# PR #165（Issue #162）Context7 を ctx7 CLI と find-docs に移す: レビュー指摘の選別

## 管理・実行許可

- 文書管理・対象: `usaturn/create-reso-world` PR #165（`feat/issue-162-ctx7-cli`）、Issue #162
- 状態: `completed`（結論 2: 修正不要としてマージする）
- 利用者の指示: `/review-fix-planning #162`。`#162` に一致するレビューディレクトリが無かったため利用者に確かめ、Issue #162 の PR #165 のレビューを対象にする回答を得た。review-fix-planning の既定（完遂）として、その PR の修正、または修正不要時のマージと関連 Issue の更新までの実行許可として扱う。内容の承認（`approved`）ではない
- 選別の対象 HEAD: `91313372c81f12880bf27e8979943009780f8f14`（4 件のレビューの対象 HEAD と、選別時の PR の head が一致）
- 関連文書: Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue162-ctx7-cli-design.md`、Plan `docs/superpowers/plans/2026-10-18-create-reso-world-issue162-ctx7-cli.md`（どちらも `draft`。この選別では変えない）
- 経路: 完遂（brainstorming は呼ばない）。修正する項目が無いので、設計の見直しのきっかけ（同じ守る条件の 2 回目・修正が生んだ回帰・自己レビューでの再発）にも当たらない。以前のレビュー修正の回は無い

## 入力

レビューディレクトリ `reviews/usaturn/create-reso-world/#165-feat-issue-162-ctx7-cli/` の 4 件。どれも対象 HEAD は `91313372c81f`、Mode は Initial。

| ファイル | 推奨 | 指摘 |
| --- | --- | --- |
| `SWE-2-Max.md` | Approve | 0 件（Review coverage に「補足（既出・対象外）」1 件） |
| `claude-opus-5-5.md` | Approve | 0 件 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Low 1 件（L-1） |
| `gpt-6.1-sol.md` | Approve | 0 件 |

## 分類

解消済み 0 / 対応する 0 / 対応しない 2。

| ID | 出どころ | 内容 | 区分 | 理由 |
| --- | --- | --- | --- | --- |
| L-1 | commandcode-deepseek-deepseek-v4.1-flash | `install_ctx7.bash:13` の `ctx7 --version` の失敗で止まる分岐を `test-install-ctx7.bash` が通らず、`\|\| fail` を外してもテストが通る | 対応しない | 現行 HEAD で再現した（下記）が、テストの追加だけの提案で、致命的な欠陥ではない。現行のスクリプトは `--version` の失敗で `[install_ctx7] ERROR:` を出して終了コード 1 で止まる。ガードが外れても `set -e` で終了コード 1 になり、呼び出し元の `install_beforehand.bash` が `fail "Context7 CLI installation failed."` でセットアップを止める。違いは `install_ctx7.bash` の ERROR 行が出ないことだけである |
| S-1 | SWE-2-Max（Review coverage の補足。指摘としては報告していない） | `docs/maatlog-poc-porting.md` の `.codex/.gitkeep` の行（#17）が「移植先は `.codex/config.toml` を持つ」のまま残る | 対応しない | 文書の記述の整合だけで、手順・ツールの結果に影響しない。#17 の行は過去の判断の記録で、文書の冒頭が「#125 の行が現在の判断」「過去の Spec と観測結果は履歴として残す」としている。PR のブランチ全体のレビューでも Minor として見送り済み（PR 本文の「検証」） |

### L-1 の確認

- 隔離した worktree（`mktemp -d` の下、`9131337` の detached）で、偽の `npm` が置く偽の `ctx7` を `--version` のときだけ終了コード 1 にして `install_ctx7.bash` を実行した。終了コード 1、出力は `[install_ctx7] ERROR: .../ctx7 --version failed.` だった
- 対照として 13 行目の `|| fail ...` だけを外した版を同じ条件で実行した。終了コード 1（`set -e`）で、ERROR 行は出なかった。その版に対して `test-install-ctx7.bash` を実行すると PASS した（レビューの指摘のとおり、テストはこのガードを確かめていない）
- 呼び出し元: `install_beforehand.bash` の手順は `if ! bash .devcontainer/install_ctx7.bash; then fail "Context7 CLI installation failed."; fi` で、終了コードだけで止まる。壊れた `ctx7` でセットアップが止まることは、ガードの有無にかかわらず成り立つ
- PR 本文の保証との関係: 本文は「導入の失敗・PATH に無い・版の不一致で `[install_ctx7] ERROR:` を出して止まります」とし、`--version` の失敗の扱いやテストの範囲を保証していない。食い違いが無いので、PR 本文の既知の制限は変えない
- 確認後に worktree を外して消した

## 自己確認

- 読んだ範囲: PR の変更 17 ファイル（`install_ctx7.bash`・`test-install-ctx7.bash`・`find-docs/SKILL.md` は全文、ほかは差分と前後、Spec の全文）。関連処理として、`install_beforehand.bash` の Pi の拡張の節と撤去の処理（`remove_pi_*` に context7-pi が無いこと）、`run-tests.bash`（`.devcontainer/test-*.bash` を自動で拾う）、`zshrc.txt` の `cod` の `CONTEXT7_API_KEY`
- 削除したファイルと Context7 の残存参照: `git grep` で、`.codex/config.toml`・`.cursor/mcp.json`・`context7` を参照するのは、PR が意図して残した箇所（`install_beforehand.bash` のコメント、`.pi/settings.json` の停止の項目、`test_pi_shared_packages.py` の `KEPT_PACKAGE`、文書と移植の記録）だけだった。雛形・スクリプト・テストに削除したファイルを読むものは無い
- PR が持ち込んだ致命的な欠陥は見つからなかった。共有の `~/.pi` の登録を消さない、`ctx7 setup` を実行しない、導入の失敗で postCreate を止める、の 3 つの安全条件は、テストとレビューの実機確認（Pi の RPC の `get_commands`）で確かめられている。ユーザー設定に context7-pi が無いときの `.pi/npm` への導入は、PR 本文・Spec・`.devcontainer/README.md` に既知の制約として書かれ、今の共有の `~/.pi` では起きない
- base の進み: 選別時の `origin/main`（`6ca0ec8`）は PR の分岐点（`3e3c1a3`）より先に進んでいる（#163）。重なるファイルは `AGENTS.md` と `.devcontainer/install_beforehand.bash` で、head に base を merge した一時的なツリーは競合しなかった。base 側の `install_beforehand.bash` の追加（`place_agent_runner_config`）は `step` を呼ばないので、merge 後も `STEP_TOTAL=31` と `step` の呼び出し 31 件が一致する

## 守る条件と影響経路

「対応する」項目が無いので作らない。

## 検証

環境の変更（`.devcontainer/`・`.pi/`・`.agents/skills/find-docs`・`AGENTS.md`・テスト）なので、PR が変えたテストと、README の「テスト」のワールド以外のコマンドを、次の 2 つのツリーで順に実行した。

| ツリー | `test-install-ctx7.bash` | `test_pi_shared_packages.py` | `bash .devcontainer/run-tests.bash` | `bash scripts/check-layout.sh` | `uv run pytest tests/skills .agents/skills` |
| --- | --- | --- | --- | --- | --- |
| PR の head `9131337`（専用の worktree `.worktrees/issue-162-ctx7-cli`） | PASS、終了コード 0 | 2 passed、終了コード 0 | 33 PASS、終了コード 0 | PASS、終了コード 0 | 620 passed（167.09 秒）、終了コード 0 |
| head に `origin/main`（`6ca0ec8`）を merge した一時的なツリー（`mktemp -d` の隔離 worktree。push しない。検証後に削除） | PASS、終了コード 0 | 2 passed、終了コード 0 | 33 PASS、終了コード 0 | PASS、終了コード 0 | 620 passed（189.16 秒）、終了コード 0 |

- `test_pi_shared_packages.py` は `uv run --no-project --with pytest python -m pytest -q -p no:cacheprovider` で実行した（PR の検証と同じ形）
- 実行後、どちらのツリーも `git status --porcelain` は空だった
- CI: usaturn/create-reso-world は private で、`AGENTS.md` の「GitHub Actions」のとおり確認の対象外

## 結論

結論 2（修正不要としてマージする）。

- 「対応する」が 0 件で、全指摘・変更ファイル・関連処理とテストの確認が終わった
- マージしてよい範囲: usaturn/create-reso-world の open で draft でない PR
- PR 本文は変えない（「対応しない」の指摘に、本文の保証と食い違う実在の制約は無い）
- 自己レビュー: 修正したとき（結論 1）だけの段なので、行っていない
- 仕様の論点: なし
