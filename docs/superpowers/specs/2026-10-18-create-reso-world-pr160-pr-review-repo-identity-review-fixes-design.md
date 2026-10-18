# PR #160（Issue #146）pr-review の所属リポジトリ識別: レビュー指摘の選別

## 管理・実行許可

- 文書管理・対象: `usaturn/create-reso-world` PR #160（`fix/issue-146-pr-review-repo-identity`）、Issue #146
- 状態: `completed`（結論 2: 修正不要としてマージする）
- 利用者の指示: `/review-fix-planning #160`。review-fix-planning の既定（完遂）として、その PR の修正、または修正不要時のマージと関連 Issue の更新までの実行許可として扱う。内容の承認（`approved`）ではない
- 選別の対象 HEAD: `3f56097cbd507e1c90833b1a4d1e3c4043376043`（3 件のレビューの対象 HEAD と、選別時の PR の head が一致）
- 関連文書: Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue146-pr-review-repo-identity-design.md`、Plan `docs/superpowers/plans/2026-10-18-create-reso-world-issue146-pr-review-repo-identity.md`（どちらも `draft`。この選別では変えない）
- 経路: 完遂（brainstorming は呼ばない）。修正する項目が無いので、設計の見直しのきっかけ（同じ守る条件の 2 回目・修正が生んだ回帰・自己レビューでの再発）にも当たらない。以前のレビュー修正の回は無い

## 入力

レビューディレクトリ `reviews/#160-fix-issue-146-pr-review-repo-identity/`（旧形式。PR のマージ前の helper が保存した）の 3 件。どれも対象 HEAD は `3f56097cbd50`、Mode は Initial。

| ファイル | 推奨 | 指摘 |
| --- | --- | --- |
| `Claude-Opus-5.5-XHigh.md` | Approve | 0 件（Test suggestions に任意の提案 1 件） |
| `SWE-2-Max.md` | Approve | 0 件 |
| `gpt-6.1-sol.md` | Approve | Medium 1 件（M-1） |

## 分類

解消済み 0 / 対応する 0 / 対応しない 2。

| ID | 出どころ | 内容 | 区分 | 理由 |
| --- | --- | --- | --- | --- |
| M-1 | gpt-6.1-sol | `session.json` の `pr_repository` だけを別の所属に書き換えると、`sessions` が保存先との食い違いを検出せず、書き換え後の所属の PR が MERGED なら `removable: true` を返す | 対応しない | 現行 HEAD で再現した（下記）が、発生条件に通常の経路で到達しない。`session.json` を書くのは helper の `create_session` の 1 か所（`pr_review_workspace.py:574-597`）だけで、所属と保存先は同じ値から作られる。pr-review の編集許可も `review-backup/` に限られ（SKILL.md の `allowed-tools`）、他のスクリプト・スキルは `session.json` を書かない。手で書き換えた state はサポートしている使い方ではない |
| T-1 | Claude-Opus-5.5-XHigh（Test suggestions） | `session_report` の `state_repo != repo` の分岐を通るテストが無い | 対応しない | テストの追加だけの提案で、致命的な欠陥の修正・検証に要るものではない。分岐は残す側（`removable: false`）に倒れる |

参考: Claude-Opus-5.5-XHigh と SWE-2-Max が「検討して報告しなかった候補」とした項目（`.` で始まる repo 名の取得 ref、version 6 の session を手で扱う必要、旧形式のレビューを引き継がない、壊れた `session.json` で `sessions` 全体が非 0、片付けの SKILL.md の旧い例示、`inspect`・`abandon` の所属不一致がエラーになる、gh の timeout が無い、レビュー途中のマージとの競合）は指摘ではない。どれも PR 本文の「既知の影響と見送り」か Spec に記載済みで、止まる側・残す側に倒れることをレビュアーが確かめている。

### M-1 の確認

- 隔離した worktree（`mktemp -d` の下、`3f56097` の detached）で、PR のテストの helper（`make_repo`・`identity_create_args`・`fake_gh_path`）を使って再現した。上流 `orange3134/resoloop#11` の session を作り、`pr_repository` だけを `usaturn/resoloop` に書き換え、偽の gh に `usaturn/resoloop#11=MERGED`・`orange3134/resoloop#11=OPEN` を返させると、`sessions` は `pr_repository=usaturn/resoloop`・`pr_state=MERGED`・`removable=true` を返した（保存先は `reviews/orange3134/resoloop/#11-fix-shared/opus-5.md` のまま）。確認後に worktree を外して消した
- 発生条件の確認: `write_json` の呼び出しは `create_session` だけ。`.agents/`・`scripts/`・`.devcontainer/` で `session.json` を扱うのは、pr-review の helper、repo-cleanup-after-merge の手順 6（`main_root`・`destination` を読むだけ）、`.devcontainer/cleanup-workspace.bash`（session ディレクトリごと消すだけ）で、中身を書き換える経路は無い
- PR 本文の保証との関係: 本文の「書き換えた `pr_repository` … で保存・回収しないこと」は、`save` の拒否（`test_save_rejects_rewritten_pr_repository`）を指す。`sessions` が `session.json` を信頼することは実在する制約なので、次のレビューで同じ論点が挙がらないよう、PR 本文の「既知の影響と見送り」に条件と扱い方を書き足す

## 自己確認

- 読んだ範囲: PR の変更 11 ファイル（`pr_review_workspace.py` の全文、3 つの SKILL.md・2 つの evals.json・`AGENTS.md` の差分と前後、テスト 2 ファイルの差分、Spec・Plan）。関連処理として、`scripts/superpowers_context.py` の `repository`、`.devcontainer/cleanup-workspace.bash` の `/tmp/pr-review-*` の扱い（経過日数と dirty の有無で判断し、PR の識別を使わない。PR では変えていない）、`session.json` の他の読み手
- PR が持ち込んだ致命的な欠陥は見つからなかった。取得 ref の `repos/` は旧形式の `refs/pr-review/<N>` とぶつからない。`sessions` は gh の失敗・version 6・state の欠落・locked・prunable を残す側に倒す。片付けの候補は従来より狭まる方向の変更である
- base の進み: 選別時の `origin/main`（`8659aa9`）は PR の分岐点（`2deb900`）より 8 コミット先に進んでいる（#147・#148）。重なるファイルは `AGENTS.md` と `.agents/skills/review-fix-planning/SKILL.md` で、head に base を merge した一時的なツリーは競合しなかった

## 守る条件と影響経路

「対応する」項目が無いので作らない。

## 検証

環境の変更（スキル・helper・`AGENTS.md`）なので、README の「テスト」のワールド以外の 3 コマンドを、次の 2 つのツリーで実行した。

| ツリー | `bash .devcontainer/run-tests.bash` | `bash scripts/check-layout.sh` | `uv run pytest tests/skills .agents/skills .agents/scripts` |
| --- | --- | --- | --- |
| PR の head `3f56097`（専用の worktree `.worktrees/issue-146-pr-review-repo-identity`） | 32 PASS、終了コード 0 | PASS、終了コード 0 | 656 passed（148.68 秒）、終了コード 0 |
| head に `origin/main`（`8659aa9`）を merge した一時的なツリー（`mktemp -d` の隔離 worktree。push しない。検証後に削除） | 32 PASS、終了コード 0 | PASS、終了コード 0 | 656 passed（162.88 秒）、終了コード 0 |

- 実行後、どちらのツリーも `git status --porcelain` は空だった
- CI: usaturn/create-reso-world は private で、`AGENTS.md` の「GitHub Actions」のとおり確認の対象外（`gh pr checks` も check 無し）

## 結論

結論 2（修正不要としてマージする）。

- 「対応する」が 0 件で、全指摘・変更ファイル・関連処理とテストの確認が終わった
- マージしてよい範囲: usaturn/create-reso-world の open で draft でない PR
- PR 本文の「既知の影響と見送り」に、M-1 の制約（`sessions` は `session.json` の `pr_repository` を信頼する）と扱い方を書き足す
- 自己レビュー: 修正したとき（結論 1）だけの段なので、行っていない
