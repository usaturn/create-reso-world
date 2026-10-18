# Issue #146: pr-review の PR 識別に所属リポジトリを含める

## 管理・実行許可

- 文書管理・実装対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/146
- 状態: `draft`。内容の承認（`approved`）は無い。
- 利用者の指示: `/issue-to-pr #146`（issue-to-pr スキルの明示）。許可された範囲は、通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで続けること。マージ・リリース・他者の作業の変更は含まない。
- 調査基準: `2deb900cbc7dec46cc9ee92da0dff17076af49a8`（origin/main）。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-146-pr-review-repo-identity`、branch `fix/issue-146-pr-review-repo-identity`。
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue146-pr-review-repo-identity.md`

## 意図

共有の checkout（`external/resoloop`）を使う fork（usaturn/resoloop）と上流（orange3134/resoloop）の PR を、番号・head branch・commit・model が同じでも別の PR として扱う。守る条件は Issue のとおり。

> 共有 checkout を使っていても、PR は owner/repo と PR 番号の組で区別し、別 PR のレビュー保存先・取得 ref・片付け対象を共有させない。所属を確かめられない session は推測で削除しない。

現状の問題（Issue で確認済み）:

- `pr_review_workspace.py` の session（version 6）と journal は所属リポジトリを持たない。保存先 `reviews/#<N>-<branch>/<model>.md` も所属を含まないので、fork と上流の同じ番号・branch の PR は、同じファイルを上書きし合う。
- 取得 ref `refs/pr-review/<N>` も所属を含まない。同時に 2 つのレビューが同じ番号を fetch すると、片方の `PR_HEAD` を取り違え得る（HEAD の照合 1/3 で止まるが、正しい PR のレビューも止まる）。
- `repo-cleanup-after-merge` は `/tmp/pr-review-*` の worktree を、整理対象のリポジトリのオープン PR の一覧と branch・commit で照合する。fork の一覧だけで照合すると、上流のオープン PR のレビュー中の worktree を「オープン PR に対応しない」と見て消し得る。

## 目標・対象外

目標:

1. fork と上流の PR が、同じ番号・branch・commit・model でも、別々に保存・再レビューできる。他方の本文・snapshot は変わらない。
2. 取得 ref が PR ごとに分かれ、片方の取得がもう一方の固定した head を変えない。
3. 片付けは session に固定した所属リポジトリで PR の状態を確かめ、終了した PR の worktree だけを候補にする。所属を確かめられない session は残して報告する。
4. 所属を持たない既存の session・レビューを、別の所属へ移動・上書き・削除しない。
5. create-reso-world 自身の通常のレビュー経路を保つ。

対象外:

- `.devcontainer/cleanup-workspace.bash`（経過日数と dirty の有無で判断する安全網で、PR の識別を使わない）
- `review-fix-planning` の `FETCH_HEAD` を使う祖先確認、`PR_REPO` の決め方（`#番号` の解決だけを新しい保存先に合わせる）
- #131（ゲート A の一時ファイルの衝突）、#134（保存拒否後の再レビュー・片付け）、#116（レビュー基盤の移植）
- 既存の `refs/pr-review/<N>` と旧形式のレビュー・session の移行や削除
- cleanup の削除範囲や ignore 対象の保護を緩めること

## 設計

### helper（`.agents/skills/pr-review/scripts/pr_review_workspace.py`）

1. `create` に必須の `--pr-repo <owner/repo>` を足す。値は小文字にそろえ、owner は `[a-z0-9](?:[a-z0-9-]*[a-z0-9])?`、repo は `[a-z0-9_.-]+`（`.`・`..` を除く）だけを受け付ける。不正な値は、一時ディレクトリ・worktree を作る前に拒否する。
2. session を version 7 にし、`pr_repository` を持たせる。journal の `started` にも `pr_repository` を書く。
3. 保存先を `reviews/<owner>/<repo>/#<N>-<branch>/<model>.md` にする。`save` は state の `pr_repository` から保存先を計算し直し、state の値と一致しなければ保存しない（既存の検査に所属を足す）。
4. `load_state` は version 7 と正規形の `pr_repository` を要求する。version 6 の session には「所属が無いので session を残して、どの PR のものか確かめる」旨のエラーを返す。`verify`・`save`・`cleanup` はどれもこれを通るので、旧形式の session には保存も削除もしない。
5. `create` は、同じ番号・branch・model の旧形式の保存先（`reviews/#<N>-<branch>/<model>.md`）が存在すれば、その相対パスを `legacy_review` で返す。読まず、snapshot にせず、移動もしない。
6. `inspect`・`abandon` に必須の `--pr-repo` を足し、journal の `pr_repository` と一致する試行だけを扱う。`pr_repository` の無い journal は一致しないので、`abandon` は消さずに止まる。
7. 読み取り専用の `sessions --repo <メイン checkout>` を足す。checkout に登録された worktree のうち `<…>/pr-review-*/worktree` のものごとに次を返す: session ディレクトリ、worktree、`pr_repository`、`pr_number`、`head_branch`、`commit`、PR の状態、`removable`、理由。`removable` が `true` になるのは、`load_state` が通り、state の `main_root` と worktree が登録と一致し、登録に `locked`・`prunable` が無く、`gh pr view <N> --repo <owner/repo> --json number,state` が同じ番号の `MERGED` か `CLOSED` を返したときだけ。それ以外（session.json が無い・読めない、version 6、値の不一致、オープン、gh の失敗）は `false` と理由を返す。何も変更しない。

### 取得 ref（`.agents/skills/pr-review/SKILL.md`）

- 共通 context の確認のブロックで `PR_REPOSITORY=$(… | jq -er .repository)` を取る（`superpowers_context.py` が照合した小文字の `owner/repo`）。
- fetch を bash のブロックにし、`PR_REF="refs/pr-review/repos/$PR_REPOSITORY/$PR_NUMBER"` へ取得する。`repos/` を挟むのは、旧形式の `refs/pr-review/<N>`（ファイル）と、数字の owner のディレクトリがぶつからないようにするため。git が受け付けない名前（`.github` など、`.` で始まる repo）は fetch が失敗し、レビューは止まる。
- `create`・`inspect`・`abandon` に `--pr-repo "$PR_REPOSITORY"` を渡す。`create` の結果から `LEGACY_REVIEW` を取り、空でなければ読まずに最終応答でパスを報告する。
- 保存先の説明、他モデルのレビューを読まない規則、セルフチェックの保存先の表記を新しい形式（旧形式も対象に含める）に合わせる。

### 片付け（`.agents/skills/repo-cleanup-after-merge/SKILL.md`）

- 手順 1 の `/tmp/pr-review-*` の行と手順 5 の候補を、helper の `sessions` の結果で決める。候補は `removable: true` のものだけ。`false` のものは対象外にし、理由を手順 11 で報告する。オープン PR の一覧との照合（`headRefOid` の一致で対象外にする）は今までどおり重ねて行う。
- `allowed-tools` に `Bash(uv run --no-project python *pr_review_workspace.py sessions *)` を足す（`cleanup`・`abandon` は許可しない）。
- 手順 6（ゲート A）は、worktree が残っている session ディレクトリには適用しない。`pr_repository` の無い session（version 6 以前）の draft は保存先へコピーしない（所属を確定できないため。照合で一致したときの削除は今までどおり）。
- eval を 1 件足す（fork の MERGED と上流の OPEN が同じ branch・head を持つ場面）。

### その他の参照

- `review-fix-planning` の `#番号` の解決で、`reviews/` と `external/resoloop/reviews/` の直下に加えて、`<owner>/<repo>/` の下のディレクトリも見る。複数一致したら今までどおり止まる。eval の該当の期待値を合わせる。
- `AGENTS.md` の「コミットしないファイルの置き場所」の PR レビュー結果の行を新しい形式にする。

## 受け入れ条件・検証

- 同じ checkout で usaturn/resoloop と orange3134/resoloop の PR を、同じ番号・branch・commit・model で create → draft → save し、別々のファイルに保存されること。fork 側を再レビューしたとき、`previous_review` が fork 側の本文で、上流の本文が変わらないこと（helper の実行テスト）。
- SKILL.md の共通 context と fetch のブロックを、fork と上流の同じ番号の PR について順に実行し、ref が別々で、後の取得が先の ref を変えないこと（ブロックを抜き出して実行するテスト。既存の resolver のテストと同じ方式）。
- 同じ checkout に fork の PR と上流の PR の session を作り、偽の `gh` で fork を MERGED・上流を OPEN（とその逆）にして `sessions` を実行し、OPEN 側が `removable: false` であること。worktree の登録とファイルが変わらないこと。
- version 6 の session、不正・非正規の `pr_repository`、書き換えた `pr_repository`、journal の所属の不一致、gh の失敗で、保存・回収しないこと。拒否の前後で保存先・snapshot・worktree の登録が変わらないこと。
- 片付けの手順の判断は、変更前と変更後の SKILL.md で机上の行動比較を行う（コマンドを実行しない）。変更前は上流の OPEN の worktree を消す判断になり得ること、変更後は残すことを確かめる。
- 検証の入口（README の「テスト」のワールド以外の 3 コマンド）と `git diff --check` が成功すること。SKILL.md の文面を照合するテストは作らない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-1 所属の渡し方 | `create --pr-repo` を必須にし、`superpowers_context.py` の `repository` を渡す | helper が remote の URL を読んで所属を推定する／PR の URL を受け取る | 照合済みの値が既にあり、helper に GitHub の URL 解釈を重複させずに済む。推定は fork と上流の区別に使えない | issue-to-pr の通常設計判断の委任 |
| D-2 正規形 | 小文字の `owner/repo` にそろえる | 大文字小文字を区別する | GitHub は区別せず、context helper も小文字で返す。表記の違いで別の保存先にならない | 同上 |
| D-3 保存先 | `reviews/<owner>/<repo>/#<N>-<branch>/` | `#<N>-<branch>@<owner>+<repo>` の平らな名前／checkout の既定のリポジトリだけ旧形式のまま | 区切りの曖昧さが無く読みやすい。既定のリポジトリを helper は知らず、例外を作ると経路ごとの分岐が残る。`#番号` の解決は review-fix-planning を合わせて保つ | 同上 |
| D-4 旧形式のレビュー | 引き継がず残し、`legacy_review` でパスを返して報告する | 新しい保存先へ移す／`previous_review` として読む | 旧形式は所属を持たず、fork と上流の区別ができない。create-reso-world の open PR は再レビュー時に Initial から始まる（一度だけの影響） | 同上。誤った所属への移動・上書き・削除は Issue の禁止事項 |
| D-5 state の版 | version 7 に上げ、version 6 は保存・削除を拒否 | version 6 を読み、所属を空として扱う | 所属の無い session を推測で扱わない。拒否時の文言で、残して確かめることを伝える | 同上 |
| D-6 試行の照合 | `inspect`・`abandon` も `--pr-repo` を必須にする | 試行 ID だけで照合を続ける | 試行 ID は事実上一意だが、同じ PR 識別をすべての経路で使うと Issue が求めている | 同上 |
| D-7 取得 ref | `refs/pr-review/repos/<owner>/<repo>/<N>` | `refs/pr-review/<owner>/<repo>/<N>` | 旧形式の数字の ref と、数字の owner のディレクトリがぶつかるのを避ける | 同上。旧形式の ref は消さない |
| D-8 片付けの判断 | helper の `sessions` が session の所属で gh を呼び、`removable` を返す | SKILL.md の文面で、session ごとに gh を呼ぶよう指示する | 判断を実行テストで固定できる。所属の検査を `load_state` と共有できる | 同上。gh の失敗は残す側に倒す |
| D-9 ゲート A | worktree が残る session に適用しない。version 6 以前の draft はコピーしない | 変えない | 手順 5 で残した worktree を `rm -rf` で壊さない。所属の無い draft を共有の旧形式のディレクトリへ置かない | 同上。#131 と重ならないよう最小限にする |
| D-10 実行方式 | `superpowers:executing-plans`（inline） | `superpowers:subagent-driven-development` | helper とテストの同じファイルへの逐次変更が中心で、Task 間の文脈が強い。行動比較とブランチ全体のレビューだけを別の担当に任せる | issue-to-pr の実行方式の表 |

## 調査・実行記録

- Issue 本文を確認。コメント 0 件、親 Issue・依存（blocked_by）なし。同じ Issue の open PR・予約 ref・branch・worktree なし（open PR は #141 だけ）。
- 基準版の `uv run pytest .agents/skills/pr-review .agents/skills/repo-cleanup-after-merge .agents/skills/review-fix-planning -q`: 302 passed、終了コード 0（63 秒）。ログは `/workspaces/reso-world/tmp/agents/issue-146.zw5ywlyu/baseline-skills.log`。
