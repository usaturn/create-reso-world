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
- 実装担当は明示指定 `pi_deepinfra_deepseek4-flash_high`、fallback は個人設定により空、self は false。Spec レビューも明示指定の同 agent、fallback 空、self false。Plan の Task ごとに runner へ依頼する。
- マージループは利用者指定の inspect `devin_swe2_max` / `pi_openai-codex_gpt6-sol_max`、implement `pi_deepinfra_deepseek4-flash_high`。fallback は空。既定適用は max_cycles 3、self-review と fix-check は self。

## 受け入れと検証

雛形だけの一時設定で `implement_task.py check` が self true と空 fallback を返し、明示 `--implement claude-code_sonnet_xhigh` がその agent を選ぶこと。fix とレビュー担当の既定が不変であること。指定ファイルを検索し、issue の既定を sonnet とする現行の説明が残らないこと。`uv run pytest tools/agent_runner/tests/test_config.py` と `bash scripts/check-layout.sh` を実行する。失敗や不明を成功と扱わない。
