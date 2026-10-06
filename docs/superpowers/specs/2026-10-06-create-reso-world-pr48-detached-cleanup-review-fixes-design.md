# PR #48: detached 整理手順のレビュー修正

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/48
- 関連 Issue: #47
- 検証したコード HEAD: `d02ba2fbe7d3d73120462548b6e5ff161468ef75`（第2回）
- ブランチ: `fix/issue-47-detached-cleanup`
- 状態: completed
- 実行許可: ユーザーが `review-fix-planning #48` を指定。計画のみの制限はなく、同スキルの完遂経路として修正・検証・既存 PR への push・結果投稿まで実施する。
- 結論: 1（修正して push）。マージはこの結論では行わない。
- 文書の管理: 第1回（対象 HEAD `532392efa673`）と同じ本ファイルを更新する。第1回の版は Git 履歴に残る。
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-47-detached-cleanup`（既存 worktree を clean・PR HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 第1回の記録（要約）

対象 HEAD `532392efa673` の4モデル入力を分類し、R1–R3（stale-lock 復旧案内が旧 main 操作を示唆）と R4（linked caller の古い HEAD で `-d` がマージ済み branch を拒否）を修正。R5–R9 は対応しないと判定した（R6: `set -e`/`exit` の永続シェル副作用は意図した安全停止。R8: `origin/main` 同名 ref 衝突は base でも再現する既存制約）。修正は `d02ba2fbe7d3` で PR へ反映済み。詳細はこのファイルの第1回版（Git 履歴）を参照。

## 第2回: 入力と分類

入力は `reviews/#48-fix-issue-47-detached-cleanup/` の全4ファイル（`SWE-2-High.md`、`claude-opus-5-5.md`、`deepseek-deepseek-v4.1-flash.md`、`gpt-6.1-sol.md`）。対象 HEAD は初回 `532392efa673`・更新 `d02ba2fbe7d3` で、いずれも取得した PR head（`d02ba2fbe7d3`）の祖先であることを確認した。

| ID | 入力ファイル / 元 ID | 指摘 | 分類と根拠 |
|---|---|---|---|
| S1 | `SWE-2-High.md` M-1 / `deepseek-deepseek-v4.1-flash.md` L-2 | fork 経路の `git -C external/resoloop branch -d` が古い detached HEAD を基準にし、マージ済み branch を `not fully merged` で拒否して「手順 3 の誤り」と誤診する | 対応する (a,b)。隔離リポジトリで再現: upstream 削除・prune 済み + HEAD が取り込み点より古い detached で `origin/main..merged-feature` が空なのに `-d` が exit 1。手順どおりに進めるとマージ済み branch が残り続け、誤った診断を報告する。前回 R4 で直したのと同じ守る条件の fork 経路であり、前回の表が「既に満たす」と誤判定した経路 |
| S2 | `claude-opus-5-5.md` L-2 | 手順 8・11 のブロックに `MAIN_ROOT` 空値ガードが無く、`git -C ""` が黙って cwd を対象にする | 対応する (a,b)。`git -C ""` が cwd を指すこと、MAIN_ROOT 未設定で手順 8 相当コマンドが別リポジトリに対して実行されることを隔離リポジトリで再現。linked worktree を cwd にすると前回直したはずの誤判定（`not fully merged`）が再発し、cwd が別リポジトリなら誤った対象へ操作する。前回 R4 の表で漏れた隣の経路 |
| S3 | `SWE-2-High.md` I-1 | 手順 11 の `git worktree list` / `git branch -a` に `-C` が無く呼び出し側 cwd のリポジトリを参照する | 対応する。S2 と同じ守る条件（最終報告は更新対象の root で取る）の隣の経路であり、同じブロックの修正に含める。単独では報告の取り違えに留まるが、S2 の修正で同じ行を直す |
| S4 | `SWE-2-High.md` L-3 | fork の経路で `external/resoloop` のローカル `main` が削除候補の除外対象になっていない | 対応する (b)。sync 済みのローカル `main` は `upstream/main..main` が空でマージ済み候補に並び、detached HEAD 下の `git branch -d main` が実際に削除することを隔離リポジトリで再現。`main` を保持するという本 PR の意図と非対称で、利用者所有のベース branch を消す誤対象操作 |
| S5 | `SWE-2-High.md` L-2 | 手順 7 の `set -e`/`exit 1` が永続シェルを終了させ、成功時に errexit が残る | 対応しない。前回 R6 の裁定を維持する（失敗時の停止は意図した安全性であり、データ損失・誤対象操作・誤結果は確認されていない）。PR 説明の既知の制限に独立 bash 呼び出しの注意を記載済み。提案は注意文を本文へ移す軽微な追記のみで、致命的でないため追加しない |
| S6 | `deepseek-deepseek-v4.1-flash.md` I-2 | 手順 7 の `origin/main` 短縮名が同名ローカル branch/tag に誤解決される | 対応しない。前回 R8 と同じ既存制約。base `269f3cc` の旧手順でも同じ誤参照が再現し、PR が持ち込んだ問題ではない。PR 説明の既知の制限に条件と `refs/remotes/origin/main` による回避方法を記載済み |

入力分類: **解消済み0 / 対応する4（S1・S2・S3・S4） / 対応しない2（S5・S6）**。

解消確認: 前回の L-1（stale-lock 旧案内）は現行 `stale_git_lock.sh:557-562` で両出力経路とも新案内（元の失敗操作のみ再実行、手順 7 からなら MAIN_ROOT clean 確認から再開）。旧 I-1（手順 11 status）は `SKILL.md` が `git -C "$MAIN_ROOT" status` 化済み。旧 M-1（手順 8 の `-C`）も `git -C "$MAIN_ROOT" branch -d` 化済み。

## 守る条件の設計（設計の見直し）

きっかけ: **同じ守る条件の 2 回目**。前回 R4 で直した条件（branch 削除の判定は更新済みの対象 root の HEAD を基準にし、caller や他 repo を対象にしない）が、今回 2 経路で破れている。前回の表は fork 経路を「既に満たす」と誤判定し（fork では HEAD を動かさない前提のため `-d` の暗黙の HEAD 基準が最初から成り立たない）、`MAIN_ROOT` 未設定という経路を列挙していなかった。

守る条件を、再現した 1 経路ではなく仕組み全体で成り立つ性質として定義する:

> branch 削除と最終報告は、呼び出し側の cwd・シェルの環境変数・対象 checkout の HEAD 位置のどの組み合わせでも、手順 3 で検証した対象リポジトリと基準 ref に結び付く。`-d` の暗黙の upstream/HEAD 判定をマージ済みの最終根拠にせず、`MAIN_ROOT` を使うコマンドは未設定のまま cwd へフォールバックさせず停止する。

前回までの修正が足りなかった理由:

- R4 の修正は `-C "$MAIN_ROOT"` を書き足しただけで、変数が空のときの `git -C ""` が cwd を指す挙動を止めていなかった。
- fork 経路では HEAD を動かさないことが仕様であり、`-d` の HEAD 基準は構造的に古いままなので、`-d` の拒否をそのまま未マージと読む分岐そのものが誤りだった。

仕組みからの影響経路（`MAIN_ROOT`・`git -C`・`-d` 判定・ベース branch 保護に関わる全箇所）:

| 経路 | 判定 | 確かめる方法 |
|---|---|---|
| 手順 7 ブロック（`:?` ガード + 全 `git -C "$MAIN_ROOT"`） | 既に満たす | 既存テスト 18 件。未設定時に `:171` のガードで停止 |
| 手順 8 ブロック `git -C "$MAIN_ROOT" branch -d` | 修正する（`${MAIN_ROOT:?}` をインライン化） | 新テスト: MAIN_ROOT 未設定で linked project cwd から抽出ブロックを実行し、非0・`not fully merged` が出ない・refs 不変を確認 |
| 手順 8 `not fully merged` 分岐の診断 | 修正する（`merge-base --is-ancestor` で手順 3 と同基準の再確認を指示し、取り込み済みならその branch に限り `-D` を許可） | 新テスト: stale detached HEAD + upstream 無しの fixture で `-d` 拒否を再現し、文書が指示する `merge-base` コマンドが merged=0 / unmerged=1 を弁別し、確認後の `-D` が削除することを確認 |
| 手順 8 fork 読み替え `git -C external/resoloop branch -d` | 修正する（上記分岐の再確認がこの経路をカバーする） | 同上の fixture は fork 相当構成（detached・HEAD 非移動）で再現する |
| 手順 11 `git -C "$MAIN_ROOT" status` | 修正する（`${MAIN_ROOT:?}` をインライン化） | 新テスト: 未設定で非0・ガードメッセージ・stdout 空 |
| 手順 11 `git worktree list` / `git branch -a`（`-C` 無し） | 修正する（`git -C "${MAIN_ROOT:?}"` に揃える） | 新テスト: 無関係リポジトリを cwd にして実行し、出力が MAIN_ROOT の内容と一致することを確認 |
| 手順 3・8 のローカル `main` 除外 | 修正する（fork の `external/resoloop` の `main` も除外） | 契約テスト: 除外規定の存在を固定（利用者所有のベース ref を守る固定値。理由をテストに記録）。併せて fixture で synced `main` が `-d` で消える事実を確認済み |
| 手順 9 `git branch -r` / `git push origin --delete` / `git fetch --prune`（`-C` 無し） | 対象外 | 変更前の挙動と同一（base から不変）。同一 repo のどの worktree からでも refs/remotes は共通であり、別 repo cwd は手順 1 の `git status` 等も同じ前提を共有する既存の制約。本 PR の守る条件（MAIN_ROOT を使う経路の対象固定）の外 |
| 手順 1・2・6 の非 `-C` コマンド | 対象外 | 同上（スキル全体の既存前提。本 PR 不変） |
| 変更前の挙動: upstream 残存時の `-d` は warning 付きで削除成功 | 既に満たす（変更しない） | 既存テストの削除成功ケースで維持 |

## 直し方の比較

- **採用**: (i) 手順 8・11 の `$MAIN_ROOT` 使用コマンドをすべて `git -C "${MAIN_ROOT:?...}"` のインラインガードにする（各行が自己完結し、行単位で実行されても未設定なら止まる）。(ii) `not fully merged` 分岐は「未マージと断定しない → 手順 3 と同じ基準 ref へ `merge-base --is-ancestor` で再確認 → 取り込み済みならその branch に限り `branch -D` で削除、未取り込み・確認不能なら削除せず報告」にする。`-D` は checked-out branch を拒否するので worktree 保護は残り、マージ判定は `-d` の暗黙チェックから明示的な `merge-base` へ置き換わる。(iii) 手順 3・8 に fork のローカル `main` 除外を追記する。
- **不採用**: 点の修正として fork 経路の断り書きだけ追加する方法。`MAIN_ROOT` 未設定のフォールバックと手順 11 の `-C` 漏れが残り、同じ条件の 3 回目の指摘になる。
- **不採用**: fork 経路の削除を常に `merge-base && branch -D`（verify-then-delete）にする方法。`-D` が常用化してガードレールの見通しが悪くなり、`-d` の upstream 判定・既存の警告経路を捨てる。`-d` 先行 + 拒否時の明示的再確認のほうが変更が小さい。
- **不採用**: fork での branch 削除を非対応にして報告だけにする保証の縮小。cleanup の目的を後退させ、merge-base 確認で安全性は保てるため不要。
- **不採用**: 手順 8・11 ブロック先頭の独立した `:` ガード行。手順 7 と形式は揃うが、行単位で抜き出して実行したときにガードが外れる。インライン `${MAIN_ROOT:?}` は各行が自己完結する。

## 実装・検証タスク

- [x] SKILL.md 手順 3・8・11 とガードレールを修正
- [x] `test_detached_update.py` に MAIN_ROOT 未設定の拒否・手順 11 の対象 root 固定・merge-base 再確認の弁別・fork main 除外のテストを追加（計4件、`step_text` helper を抽出）
- [x] 追加テストが旧テキストで失敗することを確認（ガード外し対照と旧 HEAD 本文の両方を隔離コピーで実施）
- [x] 関連 pytest・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run pytest tests/skills .agents/skills`
- [x] 自己レビュー 1 回（反証 / PR 全体 / 検証の検出力）と判定
- [ ] Spec を completed にしてコミット・既存 PR へ push・状況コメント投稿

## 検証結果

| 検証 | 結果 |
|---|---|
| `test_detached_update.py`（修正後） | 27 passed、exit 0（既存 23 + 新規 4） |
| 新規テストの RED 確認（旧 HEAD `d02ba2f` の SKILL.md 本文を隔離コピー） | 4 failed / 18 deselected — 未設定フォールバック・`-C` 漏れ・merge-base 再確認欠落・fork main 除外欠落の各負例が意図した理由で失敗 |
| ガード外し対照（`${MAIN_ROOT:?}` を `$MAIN_ROOT` に sed した隔離コピー） | 未設定の負例が失敗（`git -C ""` が cwd にフォールバックし `not fully merged` を出す、または foreign repo を対象にする）。ガードの検出力を確認 |
| `uv run pytest tests/skills .agents/skills -q` | 509 passed / 1 skipped（`SKILL_UNDER_TEST` 未指定の既存任意検査）、exit 0 |
| `bash .devcontainer/run-tests.bash` | 28 suites passed、exit 0 |
| `bash scripts/check-layout.sh` | PASS、exit 0。4 プロジェクトの `SKILL_SYNC_REQUIRED` 警告は前回同様の既知の未実施 |
| 失敗時の状態比較（MAIN_ROOT 未設定の負例） | 実行前後で checkout/foreign 両 repo の `refs/heads` 一覧が同一、linked worktree の HEAD・branch 不変、stdout 空・stderr にガードメッセージ。`not fully merged` に到達しないことを確認。比較した状態: refs 一覧・HEAD・worktree 属性 |

機序の事前再現（`/tmp` の隔離リポジトリ、git 2.55.0）: stale detached HEAD + upstream prune で `-d` が `not fully merged`（exit 1）、同条件で `merge-base --is-ancestor` は 0、`-D` は削除成功・checked-out branch への `-D` は拒否、synced ローカル `main` は `-d` で削除される、`git -C ""` は cwd を指す。検証用ディレクトリは削除済み。

fork 実 checkout・dotnet・LLM による eval 実行は未実施（環境になし・評価基盤の範囲外）。リポジトリ既定の全量 pytest（前回 573）は本回未実施。スキル系の pytest（`tests/skills .agents/skills`）に当該テストを含めて確認済み。

## 自己レビュー

修正後の自己レビューは 1 回。本環境はサブエージェント委譲を用いない運用のため、controller が 3 観点を自分で実施した。

| 観点 | 結果 | 判定 |
|---|---|---|
| 反証 | 守る条件の表を仕組みから再列挙。`MAIN_ROOT` の空・未設定・不存在パス、linked worktree cwd、別 repo cwd、fork stale detached HEAD、upstream prune の各入力で、停止または `merge-base` 再確認に到達し、誤対象への削除・誤報告に進まないことを確認。`-D` は再確認済み branch 限定で、checked-out branch は引き続き拒否される（隔離リポジトリで確認）。手順 9・1・2・6 の非 `-C` コマンドは base から不変の既存前提（repo 単位操作は同一 repo の worktree 間で共通）として対象外に維持 | 致命的な指摘なし。新たな経路の破れは検出されず |
| PR 全体 | 本回の差分（SKILL.md 4 箇所・テスト 4 件追加・Spec）を全文確認。evals の期待記述は `git -C $MAIN_ROOT`・`branch -d` を根拠にしており意味上変わらず成立。他ファイルへの混入なし | 致命的な指摘なし |
| 検証の検出力 | 新規 4 テストが旧 HEAD 本文で全件失敗、ガード除去コピーで未設定負例が失敗することを確認。抽出した実ブロック・実コマンド行を実行しており、文句の写しではなく挙動を見ている | 検出力を確認 |

自己レビュー後のコード修正はない。致命的でない観察: 手順 8 の `git -C <対象> branch -D` の `<対象>` はプレースホルダで、直前の再確認と同じ対象指定を読者が引き継ぐ（対応しない）。自己レビュー後の修正を再レビューしていない。

## 所要時間

第2回はセッション継続（要約復元）のため厳密な計時はない。完了時刻 2026-10-06T10:41Z 時点の内訳（概算）:

- 全入力読解・現行 HEAD 特定・隔離再現・分類: セッション前半（前スレッド要約に記録済み）
- 設計の見直し・Spec 更新・実装（SKILL.md・テスト4件）: 中盤
- 検証: cleanup pytest 27件 約4秒、ガード外し対照・旧HEAD RED 確認、`tests/skills .agents/skills` 約111秒、`run-tests.bash` 28 suites、`check-layout.sh` 約2秒
- 自己レビュー 1 回（3観点を controller が実施）
