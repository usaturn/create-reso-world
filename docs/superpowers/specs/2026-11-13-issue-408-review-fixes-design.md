# PR #424 レビュー修正の設計（Issue #408）

## 管理・実行許可

- 状態: `completed`
- 対象 PR: `usaturn/create-reso-world#424`（https://github.com/usaturn/create-reso-world/pull/424、branch `feat/issue-408-launcher-key-derivation`）
- 対象 Issue: `usaturn/create-reso-world#408`
- 実行許可: 利用者の「残作業があれば実行し、Issueを更新してください。問題がなければクローズしてください。」と、Plan に記録した `/issue-to-pr #408 --merge` の実行許可。`issue-to-pr` の `--merge` で作った PR を、`pr-review-fix-loop` から `review-fix-planning` の完遂として処理する。
- 対象 HEAD: `6d8ba3f2eda46e54495ad0003b96928e5e75a992`（レビューと判断の対象）
- 検証したツリーが含む base: `9c3ad41e99bfc91e557f900a301bc6d6884edf0d`（`origin/main` の先端）。最初の検証の後、`origin/main` が `777a67a8` から `9c3ad41e` へ前進したため、HEAD に新しい base を merge した一時ツリーで検証し直した（push しない）。

## レビューの入力

- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#424-feat-issue-408-launcher-key-derivation`
- loop run: `6cb4d7972ae04db7a00f1fa481694db2`（`pr-review-fix-loop` の 1 サイクル目）
- 判断の記録: 前のサイクルなし（`rounds: []`）。この回をサイクル 1 とする。
- レビュアーの構成:

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max | devin | `6d8ba3f2eda4` | はい | Approve |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash | pi | `6d8ba3f2eda4` | はい | Approve |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | `6d8ba3f2eda4` | はい | Approve |

- 入力から外したファイル: なし（`findings/`・`verified/`・`runs/` はレビュアーではない）。
- planner: `deepseek-v4.1-flash[1m]`（ランタイム `claude-code`）。agent_id は `self`。

## 指摘の分類

3 レビュアーのすべてが、Critical・High・Medium・Low・Info・Unverified candidates のいずれも 0 件と報告した。したがって、このサイクルの入力にある指摘は 0 件である。

| 区分 | 件数 | 内容 |
| --- | --- | --- |
| 解消済み | 0 | 対象なし |
| 対応する | 0 | 対象なし |
| 対応しない | 0 | 対象なし |

「対応する」が 0 件であり、全レビュアーが現行 HEAD `6d8ba3f2` を再実行して `Approve` している。SKILL.md の結論 2（修正不要としてマージ）に進む。

### レビューで確認された範囲

- `SWE-2-Max.md`: PR の 9 ファイルの差分を精読し、`test_with_keys.py` の実行、`claude-ollama-exec` の拒否・陽性対照、`with_keys.py` の 2 ランチャー分の e2e 導出、`-u` 46 個の一致を確認した。未実施は `test-herdr-migration.bash` 全体・`agent_runner check` / `list` の実実行（nested_invocation のため TOML 解析で代用）・実機 API。
- `deepseek-v4.1-flash.md`: 全体差分と変更コード全文を読み、`test-herdr-migration.bash`・`pytest tools/agent_runner/tests`（303 passed）・`test-readme.bash`・`test-install-beforehand.bash`・`check` / `list`・`git diff --check` を実行した。実機 API は PR 本文の記録を確認し、独立再実行はしていない。
- `claude-opus-5-5.md`: PR head を一時ディレクトリへ展開し、`pytest tools/agent_runner/tests/test_with_keys.py`・`test-herdr-migration.bash` を実行した。`fill_environment` の境界入力（空・空白だけの既存値、末尾空白・大文字の URL、未設定・空・全角数字のトークン、補う名前の外の変数）と、偽 ccdol セッションでの wrapper の e2e を確認した。

## 要件・原因・検証の対応

- PR の約束: `ANTHROPIC_BASE_URL` の完全一致と `ANTHROPIC_AUTH_TOKEN` から対応プロバイダの key 1 変数だけを導出すること、Ollama の runner agent 2 件と `claude-ollama-exec` を追加すること、README の古い記述を実装に合わせること。
- 既存 Spec・Plan: `docs/superpowers/specs/2026-11-12-issue-408-launcher-key-derivation-design.md` と `docs/superpowers/plans/2026-11-12-issue-408-launcher-key-derivation.md`。Spec の受入条件（導出の完全一致・単一変数・ASCII 英数字ガード・3 段階の解決順序、Ollama exec の key ガードと 46 個の `-u` 隔離、テスト方針、文書更新）と、PR の実装・検証・レビュー結果を照合した。
- 共有条件の統合担当: Task 4（司令塔）が、4 URL の偽 CLI 反例・`duplicate_model` 拒否・実機観測・秘密値 0 件検査・最終検証を担当した（Plan の実行記録）。
- 修正が必要な指摘は 0 件のため、「守る条件と影響経路」の表、修正方針、失敗時の検証、設計の見直しのきっかけ判定は、該当なしである。

## 検証

PR の変更の種類（`.devcontainer/`・`tools/agent_runner/`・文書）に応じた検証を実行した。当初は PR head `6d8ba3f2` の checkout（`/workspaces/reso-world/.worktrees/issue-408-launcher-key-derivation`）で全コマンドが終了コード 0 だった（記録: `tmp/agents/issue-408.kwkykzl6/reverified.json`）。その後 `origin/main` が `9c3ad41e` へ前進し、HEAD の祖先ではなくなったため、`mktemp -d` の一時 worktree で HEAD に `9c3ad41e` を merge したツリー（`83c1b4b3`）を作り、同じコマンドを実行し直した。merge は push していない。

| コマンド | 終了コード | ログ |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 0 | `tmp/agents/issue-408.kwkykzl6/merged-reverify-1.log` |
| `bash scripts/check-layout.sh` | 0 | `tmp/agents/issue-408.kwkykzl6/merged-reverify-2.log` |
| `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools` | 0 | `tmp/agents/issue-408.kwkykzl6/merged-reverify-3.log` |
| `uv run --locked python -m tools.agent_runner check` | 0 | `tmp/agents/issue-408.kwkykzl6/merged-reverify-4.log` |
| `uv run --locked python -m tools.agent_runner list` | 0 | `tmp/agents/issue-408.kwkykzl6/merged-reverify-5.log` |

- 検証したツリーは head に base `9c3ad41e` を merge したものである（head だけでは base を含まない）。base の変更は `tools/agent_runner/adapters/pi.py` とそのテスト・docs で、本 PR の変更ファイルとは重複しない。
- レビュアーが個別に実行した検証は上の「レビューで確認された範囲」のとおりで、指摘 0 件の根拠になっている。
- 実機 API の観測（マージ前）は Plan の実行記録にあり、この判断では再実行していない。Rebuild 後の `~/.local/bin/claude-ollama-exec` 配置と実ランチャーからの再確認は、PR 本文の「マージ後に残る確認」に残る。

## 結論

- **結論 2: 修正不要としてマージする。** 「対応する」が 0 件で、全レビュアーが現行 HEAD を再実行して `Approve` し、変更ファイル・関連処理・テストの確認が終わっている。
- マージしてよい範囲: `usaturn/create-reso-world` の open で draft でない PR #424。条件を満たす。
- 自己レビュー: 修正がないため未実施（`run_roles.py --phase self-review` は起動しない）。
- マージと関連 Issue の更新は `finalize.py` に `--spec-commit` を付けて行う。PR は `Refs #408` のため GitHub の自動 close はなく、関連 Issue の更新は finalize の結果で確認する。
