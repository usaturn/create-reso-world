# Issue #365: agent-runner カタログを AW 現行に揃える

- 状態: `draft`（内容の承認を示すものではない）
- 対象: https://github.com/usaturn/create-reso-world/issues/365 （親 #349、key `runner-catalog`）
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-365-runner-catalog`
- base: `usaturn/create-reso-world` / `origin` / `refs/heads/main` / `768c7c410558c1b4b705e82ac0c4687c35b51734`
- 実行許可: 利用者の `/skill:issue-to-pr #365 --merge` と担当指定。矛盾を報告した後の「止めなくていいです。自分で判断して進めてください。」は、AW 現行の Opus と Issue の旧 Sol 受け入れ条件の不一致を controller が裁定して継続する具体的な許可として扱う。一般的な安全境界の免除にはしない。
- 明示担当: Spec レビューと Task 実装 `pi_openai-codex_gpt6-terra_xhigh`、fallback は既存設定の空配列を保持。設計レビューは指定なし・起動しない。
- PR 修正ループ: 利用者指定をそのまま保持する。`--assign implement=pi_openai-codex_gpt6-terra_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`。サイクル上限 3 は既定の適用。`self-review` / `fix-check` は既定の `self`。

## 意図・現状・比較元

AW の `.devcontainer/agent-runner.toml` と比較しやすくするため、カタログの値・並び・説明を揃え、改名に付随する参照と移行説明を同時に直す。

2026-11-13 に GitHub contents API で取得した AW ファイルの blob は `93f200f1504d8214fce26dc5f83cdf12b77631b2`。この run ではこの内容を比較基準として固定し、作業中の再取得による範囲拡大はしない。内容は SESSION の `aw-agent-runner.toml` に保存する。

- AW と CRW の agent 集合の差は Opus の `_xhigh` / `_default` だけ。
- Sol は CRW でも既に `_xhigh` / `effort = "xhigh"`。README の「max を維持」は現行設定と不一致。
- roles の値は双方同じ。並びと説明だけが異なる。
- AW の現行 `review.inspect` の先頭は `claude-code_opus_xhigh`。Issue の旧表・受け入れの Sol とは異なる。
- AW と CRW の `fix.implement` / `issue.implement` はいずれも `self`。古い表の sonnet 化を持ち込まない。
- #353・#359・#408 は CLOSED/COMPLETED。必要な実装は base に含まれる。#408 の Ollama 定義は既に AW と同値。
- #365 に既存 PR・branch・planning manifest は無い。#407 は未着手で claim・branch・PR が無い。親 #349 の後着手側が待つ規則により #365 → #407 とする。

## 範囲

変更する追跡ファイルは次の 4 つと、この Spec・Plan のみ。

1. `.devcontainer/agent-runner.toml`: Opus の改名・effort、AW の agent / roles / workflow の並びと説明。
2. `.devcontainer/README.md`: 現行の命名・割当・effort・手動移行・意図的な相違の理由。
3. `.agents/skills/review-fix-planning/SKILL.md`
4. `.agents/skills/review-fix-planning/references/execution.md`: 3 とともに、古い「既定 implement は opus」を現在の `self` に訂正する。

### 除外

adapter・runner・監査・key 導出・exec・配置処理・runtime 文書・個人設定を変更しない。新しい agent、alias、自動移行、CI を追加しない。#407 の Alibaba tier の修正は含めない。過去の Spec・Plan・レビュー記録を改名しない。README の #305 の履歴表は当時の名前として残し、現行 ID と混同しない説明を付ける。Ollama の値と #408 の key / duplicate_model の説明は保持し、Opus の名前参照の追従だけ許可する。

## 設計

### カタログ

`[agents.claude-code_opus_default]` を `[agents.claude-code_opus_xhigh]` に置き換え、`effort = "xhigh"` を明示する。他の agent の値は変えない。AW の定義順を使う。roles は agent の後、workflows の前に移し、AW の順と説明を基本にする。`schema_version`、role の権限・期限・出力形式・skills は不変。

`review.inspect` は `claude-code_opus_xhigh,devin_swe2_max,pi_opencode-go_deepseek4-flash_max` とする。fix の 3 割当と issue.implement は `self` を保持する。

### 意図的に揃えない箇所

- Sol / OpenCode Go DeepSeek の env は `OPENCODE_API_KEY`。CRW のランチャーと with_keys の対応を維持する。
- review の after_run は `uv run --project .`。CRW に `tools/devenv` は無い。
- 個人設定を雛形からコピーしない install_beforehand の説明、#337 の Command Code を既定から外した経緯を残す。
- AW の Issue 参照は必要に応じて `usaturn/agent-workspace#N` と書く。
- #408 の key 解決・Ollama の duplicate_model の詳しい説明と、CRW の現在の Alibaba tier の説明を残す。AW の古い tier コメントを取り込まない。
- README の手動移行の履歴と、個人設定を保護する説明は CRW 固有のまま。

### 文書と個人設定

現在の説明・例・認証表の Opus 参照を `_xhigh` に追従させる。旧名の明示は履歴と移行説明に限る。Sol は現行の xhigh を説明し、#305 では max を選んだ履歴を残す。

個人設定の定義テーブルと workflow の `agents` / `fallback` の両方を手で変更する手順を書く。旧名が参照だけなら `invalid_reference`、完全な旧定義なら独自 agent として残ること、部分定義では `invalid_type` になり得ることを区別する。自動変更しない。max を使い続ける利用者には、完全な `[agents.pi_openai-codex_gpt6-sol_max]` の定義と `review.inspect` の上書き例を示す。同一モデルの xhigh と max を同じ役割に混在させない。

スキルの例は `_default` を `_xhigh` へ機械置換するのでなく、実効の既定 `self` を正しく説明する。手順・権限・拒否・マージ条件は変更しない。

### 実行中の雛形

Spec レビュー、Task helper、PR 修正ループは PARENT_ROOT の helper と旧雛形を使用する。親 checkout をこの run の途中で更新せず、利用者の `claude-code_opus_default` 指定を書き換えない。worktree の改名後も親の雛形ではこの指定が有効であり、`check-options` は成功済み。検証で雛形単独を調べる場合は、SESSION の空 config を明示して実個人設定を混ぜない。

## 決定記録

| ID | 選択した案 | 検討した別案 | 理由 / 委任指示・停止条件 |
|---|---|---|---|
| D1 | AW 現行 + 列挙した CRW 固有差分を保持 | ファイル全面置換、旧 snapshot の再現 | 全面置換は key・after_run・#408 説明を壊す。旧 snapshot は現在の目的と合わない |
| D2 | review 先頭は Opus xhigh | Issue の旧受け入れどおり Sol xhigh | AW 現行と既存 CRW の Opus 選択を保つ。利用者が報告済みの矛盾を自分で判断して継続するよう明示したため、この裁定を記録。旧 Sol 条件は採用しない |
| D3 | fix / issue 実装は self | 古い Issue 表の sonnet 化 | AW 現行と CRW の #377・#391 に一致するため |
| D4 | 手動移行・履歴注記 | alias / 自動書換え / 履歴一括改名 | 個人所有の定義と凍結した履歴を守る |
| D5 | 追加テスト無し、実行検査と一時比較 | カタログ固定値テスト | 今回は F / L。S の duplicate_model・env 境界は既存テストで守られる。本文文字列を写す恒久テストを追加しない |
| D6 | 1 Task を指定の runner 担当に依頼し、Task レビュー後に PR ループ | controller 実装、複数 Task 分割 | self=false の明示指定。同じ名前・割当の変更を不可分の検証単位にする |
| D7 | 実サービスを使う受け入れテストはしない | 実 CLI のモデル起動実験 | Issue の禁止。指定された Spec レビュー・実装・PR レビューの担当起動だけを行う |

## 受け入れ基準

- 動作環境: Ubuntu Dev Container、uv / Python の既存 locked 環境。実入力は日本語の複数行 TOML コメント、現行 AW の 21 agent、空の個人 config、旧名参照だけ / 完全な独自旧名定義 / 移行後の個人 config。
- Opus xhigh、Sol xhigh が有効で、review.inspect の先頭は D2 により Opus xhigh。roles と Ollama の値は base から変わらない。agent の値は上記の意図的差分以外 AW と一致する。
- agent / roles / workflow の並びとコメントを AW と対比でき、CRW の差異には理由がある。
- README の現行割当、effort、スキルの self の説明が実際の設定と一致する。履歴・移行説明以外に旧 Opus 名への現行参照が残らない。
- 雛形単独の check / list は成功し、既定に duplicate_model は無い。旧名参照だけの設定は拒否し、手動移行後は成功する。独自の旧名完全定義と max の個人設定は自動で失われない。
- 防御範囲: 実個人設定・key・ログイン・履歴・#408 の値を変更しない。alias と自動移行は対象外。check の成功を認証や実サービス起動の成功と表示しない。
- 新規の固定値テストは追加しない。スキルの説明変更は、変更前後の説明に従う一時適用シナリオと実際の設定解決・helper の self 分岐を比較する。既定割当を外部モデルと説明する変更前に不一致を観測し、変更後は self と一致することを確認する。対象手順を実行する検証であって固定文言の照合だけで代えない。個人設定は空の一時 config に隔離し、self の helper 呼出しまたは fake adapter / fake CLI のみを使う。検証のために実モデルを追加起動せず、別 context に説明させることは必須条件にしない。
- Issue 指定と README の検証入口を実行する。マージは PR 修正ループ内の finalize.py に限る。ボードの子なので PR は `Refs #365` とし、マージ後に完了状態を記録する。

## 検証入口

雛形単独 check / list（SESSION の空 config を指定）、`uv run --locked pytest tools/agent_runner/tests -q`、`bash .devcontainer/test-install-beforehand.bash`、README の `bash .devcontainer/run-tests.bash` / `bash scripts/check-layout.sh` / `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`。一時シナリオは SESSION 内だけに保存し、実 API を呼ばない。

## 準備で得た証拠

- Assignment / loop check は全て exit 0。明示された担当と fallback の保持を確認。
- baseline `768c7c41`: `uv run --locked pytest tools/agent_runner/tests -q` は 305 passed / exit 0。ログは `/workspaces/reso-world/tmp/agents/issue-365.iuvh4cpo/baseline-agent-runner.log`。
- repository の write / triage 権限あり、rulesets なし、claim branch の protected=false、Actions enabled=false を確認。claim は `42578d1a7ce39692a4c7e7664f52fc5c364c31f3`。
- 実装・PR 作成はまだ行っていない。

## Spec レビュー記録

- review_dir: `/workspaces/reso-world/tmp/agents/issue-365.iuvh4cpo/2026-11-13-issue-365-runner-catalog-design.spec-review/review-1`
- review_id: `49d56796d14e44dd88817a503ca4c237`、reviewed SHA-256: `a6b2811aace1a5a17e956cf0ad693c4a8c28da717e436b50d81dee1a2f020fa8`。
- helper `review_spec.py` の external mode。requested=actual=`pi_openai-codex_gpt6-terra_xhigh`、identity `openai-codex / gpt-6.1-terra / xhigh`、1 回目、65.97 秒、fallback 無し。stop_confirmed=true、outside_changes=[]。
- unprotected_changes: 既存の prunable な `/tmp/pr-review-376-*` 4 件と `/tmp/review-fix-planning.*` 2 件、別担当の `/workspaces/reso-world/tmp/agents/issue-431-implement.3t3ggqnv/task-1-attempt-1/03196e104041442dbb9f6da231e9606e/attempt-1/worktree`。対象 worktree の変更は無く、他者の領域には手を加えない。
- S1（important）採用: 別 context の追加モデル実行と API を呼ばない検証条件との曖昧さを解消した。受け入れ基準を、一時 config に隔離した設定解決と helper self 分岐の適用シナリオに具体化した。固定文言テストや追加の有料モデル実行は行わない。反映後の SHA は decide の出力として SESSION に保存し、Spec へ書き戻さない。
