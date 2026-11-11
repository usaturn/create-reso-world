# Issue #391: issue 実装担当の既定を self にする

状態: draft

## 管理・実行許可

対象: https://github.com/usaturn/create-reso-world/issues/391。利用者の指示は `$issue-to-pr #391 --merge --spec-review pi_deepinfra_deepseek4-flash_high --implement pi_deepinfra_deepseek4-flash_high --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_max --assign implement=pi_deepinfra_deepseek4-flash_high`。Issue の範囲で Spec・Plan・実装・検証・PR・指定ループによるマージを行う指示であり、内容の承認を意味しない。

## 目的と範囲

雛形の `workflows.issue.assignments.implement` を `agents = ["self"]`、`fallback = []` にして、既定では司令塔が実装する。`.devcontainer/agent-runner.toml` のコメント、`.agents/skills/issue-to-pr/SKILL.md`、`.devcontainer/README.md`、`README.md`、`tools/agent_runner/interfaces.rst` の現在の説明を揃える。#353 の Spec・Plan は履歴として維持する。

## 変更しない範囲

`fix.implement`、`fix.self-review`、`fix.fix-check`、agent 定義、明示指定と個人設定の優先順位、個人設定、runner・adapter・レビュー機構は変更しない。個人設定の移行案内で歴史的な agent 名が必要な記述は残せる。

## 決定記録

- 選択: 雛形の assignment と現行の説明を一緒に更新する。別案: runner に特例を追加する。理由: 既存の self と設定の優先順位を使え、変更範囲が Issue に一致する。委任: Issue と issue-to-pr の推奨案で進める指示。
- 選択: 固定値のテストを追加せず実際の helper と既存テストで検証する。別案: 設定と文言を写すテストを追加する。理由: AGENTS.md の F に該当する。停止条件: 受け入れを検証できない場合は停止する。
- 実装担当は明示指定 `pi_deepinfra_deepseek4-flash_high`、fallback は雛形の既定で空、self は false（明示指定は agents のみを置き換え fallback を維持）。Spec レビューも明示指定の同 agent、fallback 空、self false。Plan の Task ごとに runner へ依頼する。
- マージループは利用者指定の inspect `devin_swe2_max` / `pi_openai-codex_gpt6-sol_max`、implement `pi_deepinfra_deepseek4-flash_high`。fallback は空。既定適用は max_cycles 3、self-review と fix-check は self。

## 受け入れと検証

雛形だけの一時設定で `implement_task.py check` が self true と空 fallback を返し、明示 `--implement claude-code_sonnet_xhigh` がその agent を選ぶこと。fix とレビュー担当の既定が不変であること。5 ファイルのそれぞれで issue の既定が self と説明され、sonnet とする現行の説明が残らないことを検索と目視で確認する。空の一時 TOML を `--config`、作業 worktree の雛形を `--template` に指定し、既定と明示指定の両方を検証する。`uv run pytest`、`uv run pytest tools/agent_runner/tests/test_config.py .agents/skills/issue-to-pr/tests` 、`bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash` を実行する。pytest の既定対象には含まれない scripts や Dev Container のテストも後者で確認する。失敗や不明を成功と扱わない。

## Spec レビュー

1 回目: helper による外部レビュー、review ID `c200bb5884894a2694257f5fabc8a6ab`、reviewed SHA-256 `2043b96e68b62db0844be8d51095a5b459105f489e9c3b40516dbf2d2acdb004`。指定・実担当 `pi_deepinfra_deepseek4-flash_high`、deepinfra / deepseek-ai/DeepSeek-V4.1-Flash-1017 / high、fallback なし、所要 321.09 秒。outside_changes は空。unprotected_changes は事前から prunable の 6 worktree（`/tmp/pr-review-376-2f0d17b0/worktree`、`/tmp/pr-review-376-79fe98e5/worktree`、`/tmp/pr-review-376-7f95b4e6/worktree`、`/tmp/pr-review-376-c9a6d3e9/worktree`、`/tmp/review-fix-planning.9AkFc2/worktree`、`/tmp/review-fix-planning.a6ogtH/worktree`）。S1–S4 を採用し、説明の正の確認、既存テスト、一時設定の隔離、fallback の由来を明確化した。

2 回目: helper による外部レビュー、review ID `57b02a25d39a465c926b4db4b69044a4`、reviewed SHA-256 `4f6b20a0b8592daa80b4aec28879f41b8b9d0d7bae93723501b716f77359227a`。指定・実担当 `pi_deepinfra_deepseek4-flash_high`、deepinfra / deepseek-ai/DeepSeek-V4.1-Flash-1017 / high、fallback なし、所要 299.80 秒。outside_changes は空。unprotected_changes は 1 回目と同じ 6 worktree。S1 を採用し Dev Container の既存テストを追加した。
