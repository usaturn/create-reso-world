# Issue #434: Pi の sp-review 依頼に必要な scope の案内

## 管理・実行許可

- 状態: `draft`
- 対象: `usaturn/create-reso-world#434`
- Issue: https://github.com/usaturn/create-reso-world/issues/434
- 利用者の指示: `#434 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_opencode-go_deepseek4-flash_max --implement pi_opencode-go_deepseek4-flash_max --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max`（元の改行を空白で表示）
- issue-to-pr による通常の設計判断、指定担当による設計・Spec レビューと実装、検証、commit・push・PR 作成、PR 修正ループ内の finalize.py によるマージが実行許可の範囲。内容の承認を受けた記録ではない。
- コード・文書の保存先は同じ worktree。同一 PR に含める。対象 origin/main の捕捉 SHA は `eb9e378bd803a77c75fa01a30d92ccf0b3682f48`。親 Issue・依存・要求統合 branch はなく、base は既定の main。

## 意図と原因

Pi の通常の issue-to-pr → SDD で初回の Task レビューが scope 不足のため未実施になる無駄を減らす。導入済み pi-superagents の `/sp-*` 用 root prompt は scope を案内するが、`/skill:issue-to-pr` からの経路には届かず、リポジトリの常設指示も補っていない。

導入済み `@teelicht/pi-superagents` は 1.14.4。`agents/sp-review.md` は依頼本文に `Review scope: task`・`Review scope: re-review`・`Review scope: branch` のいずれかを求め、選択した upstream テンプレートに入力・境界・出力形式を委ねる。必要な文脈が無ければ `NEEDS_CONTEXT` となり、レビューを実施しない。

## 変更内容

`.pi/APPEND_SYSTEM.md` の「サブエージェントの起動」にだけ、次を加える。

1. sp-review への依頼本文に、対応する `Review scope: <種別>` を単独行として必ず 1 つ入れる。通常の API 引数を増やすのではない。
2. 初回 Task レビューは `task`、修正後の限定再レビューは `re-review`、統合後の最終ブランチ全体レビューは `branch`。文脈不足を補った再送は元の scope のままであり、修正後の限定再レビューとは区別する。
3. マーカーだけでなく、選択した upstream のレビュー用テンプレートに必要事項を埋め、その本文と証拠を渡す。Task は Task brief・実装報告・Task の開始前 BASE..HEAD の review package・受け入れ基準と共通制約。限定再レビューは前回指摘の原文・修正報告・修正範囲の diff。ブランチ全体は要求・全体の BASE..HEAD の diff・deferred/parked の指摘を扱う。詳細は選択したテンプレートに従う。
4. `NEEDS_CONTEXT` を成功・指摘なしとして扱わない。不足した文脈を補って再依頼するか、解消できなければ停止する。
5. レビュー子の読み取り専用・テスト実行禁止は維持する。上流テンプレートに focused test 実行を許す記述があっても、このリポジトリの禁止を優先し、テストや最小再現は実装担当か調整役に依頼する。依頼例にもこの制限を含める。

短い表で 3 種類の違いと upstream のテンプレートを対応させる。テンプレート本文そのものを常設指示に複製せず、選択したスキルのテンプレートに委ねる。`## Response Persona` 以降は利用者所有のため、1 バイトも変更しない。

## 受け入れ基準

- **動作環境:** Ubuntu 26.04 LTS の Dev Container、信頼済みプロジェクト内の Pi、導入済み `@teelicht/pi-superagents` 1.14.4。非 Pi や信頼前の挙動を保証しない。
- **実入力:** 日本語の Task と受け入れ条件を含む複数行の依頼。初回は `Review scope: task` と task-reviewer-prompt.md の入力、限定再レビューは `Review scope: re-review` と前回指摘・修正 diff、ブランチ全体は `Review scope: branch` と全体 diff を渡せる。
- **防御範囲:** 対象は sp-review の依頼文を作る常設指示。パッケージや upstream を変更せず、NEEDS_CONTEXT の拒否・レビュー子の読み取り専用・テスト実行禁止・利用者所有の Persona 節を維持する。マーカーだけ、証拠なし、scope の取り違えを十分な依頼として案内しない。

## 検証と完了の区別

恒久テストは追加しない。現在の文言だけを写す検査は F/L に当たるためである。既存の安全保護検査 `tests/scripts/test-instructions.bash`、配置検査 `scripts/check-layout.sh`、README の既存検証入口を実行する。

実行前後の常設指示に基づく 3 種類の依頼例をセッション領域に保存し、導入済みロールと upstream テンプレートに照合する。変更前は常設指示にマーカーの案内が無く、変更後は各 scope・テンプレート・証拠・未実施時の扱いを選べることを構造と意味から確認する。これは静的なシナリオ確認であり、実起動で成功したという主張にはしない。本 Issue の検証用の追加 runner/CLI・実サービス疎通は行わない。利用者が明示した workflow の設計・Spec・Task・PR レビューと実装は行うが、これを 3 種類の動作試験の代用にしない。

変更後の SDD 実行 3 回の記録で、初回依頼に scope があり、scope 不足の NEEDS_CONTEXT 再依頼が 0 件かを評価する。現時点では未確認。PR は `Refs #434` とし、マージ後もこの評価を残して Issue を自動 close しない。

## 対象外

- 導入済みパッケージ・ロール定義の直接編集、版更新、常設 sp-review ロールの追加
- 上流の拒否条件の緩和、レビュー子の書き込み・テスト実行、マーカーを付けるだけでのレビュー成功扱い
- #307・#400・#417 の変更や再開、#365 の整理、親ボードの所有権変更
- 新しい機構・強制バリデーター・固定文言の恒久テスト・追加の実サービス再現

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 編集範囲 | `.pi/APPEND_SYSTEM.md` の既存節のみ | issue-to-pr にも同じ文を複製 | 共通スキルは選択した実装スキルへ委ねており依頼を直接生成しない。Pi 固有の不足を常設指示で補うのが最小 | 通常判断の委任。共通案内に別の生成箇所が見つかれば範囲内で再検討 |
| テンプレート | 選択した upstream の task/re-review/branch テンプレートを使用 | 常設指示にテンプレート全文を複製 | 上流の入力・境界・出力形式を保ち、二重管理を避ける | 拒否条件・意味の変更が必要なら停止 |
| 検証 | 静的照合・依頼例・既存検査 | マーカー欠落を実起動で再現、文言固定テスト追加 | Issue の追加実起動禁止・F/L 基準に従う | 実入力での効果は未確認として残す |
| 実装方式 | runner に 1 Task ずつ依頼する SDD | controller が inline 実装 | 利用者の `--implement` 明示指定を保持する | 担当の失敗を理由に self へ切り替えない |
| 設計レビュー | 明示 `pi_openai-codex_gpt6-sol_xhigh`、fallback なし | 無指定の既定省略 | 利用者の明示値、check 成功 | 失敗は成功扱いせず停止 |
| Spec レビュー | 明示 `pi_opencode-go_deepseek4-flash_max`、fallback なし | builder check | 明示の Spec レビューが builder check に代わる | 重要な採用後の再レビューは最大 1 回 |
| Task 実装 | 明示 `pi_opencode-go_deepseek4-flash_max`、fallback なし、self=false | 雛形の既定 self | check で明示割当を確認した | runtime の拒否・監査不能で停止 |
| PR 修正ループ | 明示 inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max、implement=pi_opencode-go_deepseek4-flash_max。fallback はすべて空 | 最終全体レビューを別途実行 | `--merge` でループの 1 サイクル目が最終全体レビューに代わる | merge は finalize.py のみ |
| ループ既定 | max_cycles=3、self-review=self、fix-check=self、雛形は `.devcontainer/agent-runner.toml`、ループ config=null | 個別の回数・担当を補完 | helper が適用した既定であり利用者の明示指定ではない | サイクル上限で止める |

## レビュー記録

- 設計レビュー 1 回目: 外部 helper、明示担当 `pi_openai-codex_gpt6-sol_xhigh`、actual_agent は同名、identity は `openai-codex/gpt-6.1-sol`（xhigh）、fallback 未使用。所要 107.96 秒。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-434.pe2kx9ad/2026-11-15-issue-434-review-scope-design.design-review/review-1`
- review_id: `23916ae614fa401baf452d7c4d9cc16e`、reviewed Spec SHA-256: `ef57b4e115e2688cb312b3384ed0752895635e1a0645550150fcc21c9e3f5b86`。
- 結果: `completed` / `sound`、concerns・questions_for_user・incomplete は空。採否対象なし。設計の小ささと安全境界、静的検証と後続評価の分離を妥当と評価。
- attempts の終了コード 0、stop_confirmed=true。outside_changes は空。unprotected_changes は既存の `/tmp/pr-review-376-{2f0d17b0,79fe98e5,7f95b4e6,c9a6d3e9}/worktree` と `/tmp/review-fix-planning.{9AkFc2,a6ogtH}/worktree` の6登録で、いずれも開始前から不在の非保護 checkout（unavailable_before）。本作業の checkout の変化ではなく、他作業の領域なので変更・削除しない。

- Spec レビュー 1 回目: 外部 helper、明示担当・actual_agent は `pi_opencode-go_deepseek4-flash_max`、identity は `opencode-go/deepseek-v4.1-flash`（max）、fallback 未使用。所要 768.69 秒。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-434.pe2kx9ad/2026-11-15-issue-434-review-scope-design.spec-review/review-1`
- review_id: `dd589fcd1e8044aeae7713383b8e6d4d`、reviewed Spec SHA-256: `3c58702b51876f6a22b762f28bb7ebb144d1fa5f7caf6c39eb1301abcb7ea20a`。
- 結果: `completed`、S1（minor）を採用。上流テンプレートの focused test 許可よりもレビュー子のテスト実行禁止を優先する旨を変更内容5と依頼例の条件に反映した。既存の防御範囲の明確化であり、作るものは変えない。incomplete は空。minor の採用のため再レビューは行わない。
- attempts の終了コード 0、stop_confirmed=true。outside_changes は空。unprotected_changes は設計レビューに記した既存6登録と、他作業の `/workspaces/reso-world/.worktrees/issue-425-json-example-boundary`、`/workspaces/reso-world/tmp/agents/issue-425.55cedqeq/review-runner/design-1/e0c56dd8a4a74415b0fface3b59eab26/attempt-1/worktree`。保護対象の本 worktree に変化はなく、他作業の領域を変更しない。

## 調査根拠

- `.pi/APPEND_SYSTEM.md` の「サブエージェントの起動」、`tests/scripts/test-instructions.bash` の Persona 保護
- `/home/vscode/.pi/agent/npm/node_modules/@teelicht/pi-superagents/agents/sp-review.md`
- 同パッケージ `src/superpowers/root-prompt.ts` の SDD adapter と `src/superpowers/skill-entry.ts`
- `/home/vscode/.pi/agent/git/github.com/obra/superpowers/skills/subagent-driven-development/task-reviewer-prompt.md` と `re-review-prompt.md`
- 同 checkout の `skills/subagent-driven-development/references/final-review.md` と `skills/requesting-code-review/code-reviewer.md`
- 調査担当 sp-recon の読み取り専用調査。所要約18分。パッケージ 1.14.4、upstream 7.0.2 を確認。Issue 本文・全コメント（0件）・先行依存（0件）・親不在を確認した。
