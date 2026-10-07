# PR #53: テストの整理（Issue #51）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/53（`chore/issue-51-test-cleanup` → `main`）
- 関連 Issue: #51（Closes）。本文で参照: #36、#12
- 検証したコード HEAD: `20b6008bb3fdee880b59dc1ce9015d209caa5de7`（base `main` = `a94f04eea41fce3fb344dd4a7f10a7a0692512c2` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning #53` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-51-test-cleanup`（既存 worktree を clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#53-chore-issue-51-test-cleanup/` の 4 ファイル。対象 HEAD はすべて `20b6008bb3fd` で、取得した PR head と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `SWE-2-High.md` | Approve | Low 2・Info 2 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Info 2 |
| `grok-4.7.md` | Approve | 0 |
| `openai-codex-gpt-6.1-sol.md` | Needs manual verification（全文精読が未完了の限定レビュー） | 0 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | SWE L-1 | MCP 設定の鍵の直書きガードが `.pi/mcp.json`・`.mcp.json` の `headers` だけで、`env` と `.cursor/mcp.json` を見ない | 対応しない。base でも `env`・`.cursor/mcp.json` の値は検査されておらず、PR が弱めたものではない。現行の設定に直書きの鍵は無く、将来の保険 |
| R2 | SWE L-2 | postCreate の順序・呼出しの grep 検査を削除し、`STEP_TOTAL` の一致だけが残る | 対応しない。削除したのは本文の文字列一致だけで判定する検査（採用基準の作らない型 4）。現行の `install_beforehand.bash` の順序（uv → pi → cleanup → 拡張の導入）は正しく、cleanup を拡張の導入より後ろへ移す変異は `test_pi_mcp_cleanup.py` が検出した |
| R3 | SWE I-1 | 撤去済みツール名の再混入を防ぐ grep 検査を削除 | 対応しない。採用基準の作らない型 2。移行元の名前（`MAATLOG_*` など）は `tests/skills/test_legacy_references.py` が引き続き検出する |
| R4 | SWE I-2 | file-modes の件数下限、unittest discover の無言スキップ、frontmatter の空 glob | 対応しない。`tests/scripts/test_*.py` の 3 ファイルはすべて `unittest.TestCase` で、discover と pytest の収集件数はどちらも 61 件。`.agents`↔`.claude` の対応は check-layout が検査する。致命的な弱化ではない |
| R5 | DeepSeek I-1 | 採用基準の「書く」に参照先の実在・定義元との比較・schema が明記されていない | 対応しない。仕様の是非。PR 本文の判断事項 1 として利用者に示されている |
| R6 | DeepSeek I-2 | 凍結した 2 文書（2026-09-26 の再設計 Spec・フェーズ 0・1 の Plan）の 7 文字列の検査を削除し、変更を検知しなくなった | 対応しない。分類表に削除理由が記録された設計判断（PR 本文の判断事項 2）。文書は Git の履歴に残り、データの消失は起きない |
| R7 | 自己確認（akichi） | akichi で BoxCollider（地面 1・塔 10）を検査するテストが無くなった。削除した `test_manifest_component_type_counts` が副次的に見ていた | 対応しない。発生条件は「akichi の pipeline・layout を将来変えて manifest を作り直す」ことで、PR は現在の生成結果を変えていない（akichi は 2026-09-25 に納品済み）。削除理由（コミット済みの生成物の件数の写し、型 3）は分類表に記録済み。PR 本文の「残したもの: ワールドの生成結果（… collider …）」と食い違うため、既知の制限に条件と回避方法を書き足す |
| R8 | 自己確認（.devcontainer） | `.pi/mcp.json` の送り先 URL を固定する検査が無くなった。削除した `test_project_builtin_mcp_settings_are_shared_with_worlds` が設定全体の完全一致で副次的に見ていた | 対応しない。発生条件は「URL を誤ったホストへ書き換える将来の変更」で、現行の URL は正しい。旧テストの目的は設定の欠落と link 切れで、`.mcp.json` の URL は base でも固定されていない。PR 本文が戻したと書く保証（header が環境変数の参照であること）は保たれているが、秘密情報の検査を残したという説明と範囲が紛らわしいため、既知の制限に書き足す |

分類: **解消済み 0 / 対応する 0 / 対応しない 8**。

openai-codex のレビューの「Needs manual verification」は指摘ではなく、確認範囲の制限である。下の「確認の範囲」で、変更ファイルの全文と代わりの保証を確かめた。

## 確認の範囲

変更ファイル 104 件を 4 領域に分け、読み取り専用の確認を並行して行った。各担当は `20b6008` の全文と差分、分類表の該当節を読み、変異は使い捨ての隔離 worktree でだけ行って消した。

| 領域 | 結果 | 主な変異と結果 |
| --- | --- | --- |
| `.agents`・`tests`・`pyproject.toml` | 致命的な欠陥なし | handoff schema・review-copy のガード（`require_ignored`・`require_clean_against_commit`・origin 検査）を外す、MCP header を直書きにする、Codex の `env_vars` を増やす、ci.yml の `fetch-depth` を変える、取り込み済み文書を変える → すべて検出 |
| `.devcontainer` | 致命的な欠陥なし（R8 を報告） | provisioning が pi-distill などを再び導入する、cleanup の失敗を警告にする、cleanup を拡張の導入より後ろへ移す、ランチャーを 0644 で配置する、ccdd の BASE_URL を変える → すべて検出。`.pi/mcp.json` の URL の変更は未検出（R8） |
| MyResoniteProject・akichi・slum02 | R7 を報告 | slum02 の決定性（`_assemble()` の比較）、階高の定義元の比較、akichi の看板、存在テストの対象 → すべて検出。akichi の collider を外して manifest を作り直す → 未検出（R7） |
| slum03 | 致命的な欠陥なし | collider の回転を外す、`box()` の回転を固定する → 検出。Yarol だけの回転の除去は未検出だが、現行コードに Yarol だけの分岐は無く、向きは `test_layout.py` が固定している |

テストの収集と実行経路: ルート pytest の収集 474 件、`tests/scripts` の unittest discover 61 件（pytest での収集件数と一致）、slum03 の収集 520 件。消した helper・fixture の参照残りと import 切れは ruff（F）で無いことを確かめた。

## 検証

専用の worktree（`20b6008`）で実行し、すべて exit 0。実行後も作業ツリーは clean で HEAD は変わらなかった。

| コマンド | 結果 | 所要 |
| --- | --- | --- |
| `uv run pytest` | 474 passed | 113 秒 |
| `bash .devcontainer/run-tests.bash` | 27 PASS | 259 秒 |
| `bash scripts/check-layout.sh` | PASS | 2 秒 |
| `(cd MyResoniteProject && uv run pytest)` | 51 passed | 6 秒 |
| `(cd akichi && uv run pytest)` | 62 passed | 2 秒 |
| `(cd slum02 && uv run pytest)` | 202 passed | 63 秒 |
| `(cd slum03 && uv run pytest)` | 520 passed | 115 秒 |
| `git diff --check origin/main...HEAD` | 差分なし | — |

base `main`（`a94f04e`）は head の祖先なので、base を merge した一時ツリーでの再検証は不要。private リポジトリの CI は停止中のため確認しない（ルート `AGENTS.md`「GitHub Actions」）。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## 既知の制限として PR 本文に書き足すこと

- akichi には BoxCollider の数・位置を検査するテストが無い。akichi の pipeline・layout を変えて manifest を作り直すときは、`akichi/artifacts/akichi/delivery-report.json` の BoxCollider 件数（地面 1・塔 10）と比べる
- `.pi/mcp.json` の送り先 URL はテストで固定していない（検査するのは header の値が `${NAME}` の参照であることだけ）。MCP 設定の URL の変更はレビューで確かめる
