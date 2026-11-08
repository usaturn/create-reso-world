# Issue #344 第1段階: レビュー系2スキルの pytest 棚卸し

## 管理・実行許可

- 状態: draft
- 対象: https://github.com/usaturn/create-reso-world/issues/344
- 実行許可: 利用者の明示 `/skill:issue-to-pr` と引数
  `#344 --implement pi_opencode-go_deepseek4-flash_max --merge --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_max,cursor_grok4_xhigh --assign implement=pi_opencode-go_deepseek4-flash_max`。
- 許可は通常判断、検証、commit、push、PR、修正ループ経由のマージまで。設計の内容承認ではない。
- 基準: usaturn/create-reso-world / origin / refs/heads/main / `c871b718f64233ce4d21cf0468d978516f0562d0`。
- 親 Issue・コメント・依存 API・既存 PR・予約 ref・branch/worktree を確認。親、コメント、先行依存、同じ Issue の既存 PR・予約は無し。既定 base main と異なる要求は無し。

## 目的と公開単位

AGENTS.md の現行 F/L/S/D 基準に照らして不要なテストだけを削除する。件数目標は置かず、S・F∩S と迷う候補を残す。

Issue は5領域を1 PRずつ進めると指定している。この文書とPRは先頭の `.agents/skills/pr-review/tests` と `.agents/skills/pr-review-fix-loop/tests` のみ。Issue 全体の「約89件」は候補名の無い概算であり、このPRで89件を棚卸し済みとしない。残る4領域は後続PRで同じ基準により判断する。PR本文は `Refs #344` とし、Issue を自動 close しない。

## 方式と決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
| --- | --- | --- | --- |
| 指定の最初の領域だけを1 PRにする | 全領域を1 PRに集約 | Issue の公開単位を守る。残りを完了扱いしない | 通常判断の委任。後続は別PR |
| 実装ガードと残す代表まで読んで候補を個別判断 | 件数目標で一律削除 | 保護の欠落を防ぐ | S/F∩S/曖昧は維持 |
| runner担当による1 TaskのSDD | controllerのinline実装 | 利用者の `--implement` を尊重 | 担当失敗時にselfへ切り替えない |
| 新規テストを作らず既存テストを削除・縮約 | 削除検査テストの追加 | 削除を目的とする固定値テストはF | 既存代表へ同じ保護のassertを移すのは可 |
| ループの inspect は指定3名、fix implement は指定1名 | 既定レビュアー | 利用者指定をそのまま適用 | 全設定検証成功 |
| max_cycles=3、fix self-review=self、fix-check=self、fallback無し | 独自の既定値追加 | 設定・helperの既定の適用。利用者指定とは区別 | 不正な設定・base移動・所有権競合は停止 |

実装担当チェック結果: agents=[pi_opencode-go_deepseek4-flash_max]、fallback=[]、self=false。
ループの inspect=[devin_swe2_max, pi_openai-codex_gpt6-sol_max, cursor_grok4_xhigh]、implement=[pi_opencode-go_deepseek4-flash_max]。
テンプレートは `.devcontainer/agent-runner.toml`、個人設定は `/home/vscode/.config/agent-runner/config.toml`。

## 棚卸し表

以下は実装前の判断。W は `.agents/skills/pr-review/tests/test_pr_review_workspace.py`、L は `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`。

| ID | 候補（W/L::テスト名） | 判断 | 分類・理由・残す代表 |
| --- | --- | --- | --- |
| 1 | W::test_save_rejects_changed_pinned_destination | 削除 | D。verify_state の同じdestination fingerprintガードは test_first_session_wins_same_destination が競合後の内容保持まで確認。正例 test_save_uses_only_pinned_paths |
| 2 | W::test_save_rejects_tampered_destination | 削除 | D。save の expected_destination 不一致は test_save_rejects_rewritten_pr_repository が副作用無しまで確認。正例 test_save_uses_only_pinned_paths |
| 3 | W::test_snapshot_existing_review_copies_regular_file | 削除 | D。test_create_pins_existing_review_snapshot が create から同じコピー・内容・fingerprintを確認。非regular/race拒否も維持 |
| 4 | W::test_load_state_rejects_non_canonical_pr_repository[missing] | ケース削除 | D/L。必須キー欠落は残る形検証か後段の参照で停止。大文字の不正repositoryを代表として残し、正例test_create_normalizes_pr_repository_caseも維持 |
| 5 | W::test_snapshot_reports_changes_excluding_reviews[staged] | ケース削除 | D。snapshot はgit statusをそのまま保存。both が両列MMを確認し、untrackedも残す。非変更の対照test_snapshot_does_not_refresh_index |
| 6 | W::test_snapshot_reports_changes_excluding_reviews[unstaged] | ケース削除 | D。同上。単独列ごとの網羅を減らす |
| 7 | W::test_resolve_codex_model_name_fails_closed[invalid-json] | ケース削除 | L。全行不正ならmodel不在で停止。先行する有効モデルを黙って誤採用する保護はtest_resolve_codex_model_name_rejects_malformed_completed_recordに残る。正例uses_latest_turn_context |
| 8 | W::test_snapshot_existing_review_rejects_non_regular[directory] | ケース削除 | L。directoryは内側fstat検査またはopenエラーでも停止する。symlink/fifoとcreateの正常コピーを残す |
| 9 | W::test_save_rejects_changed_runtime_model | 削除 | L。runtime_modelが変わると期待draft/destinationが変わり、後段のpin照合でも保存前に拒否。モデル解決と保存先pinの既存テスト・正常保存を維持 |
| 10 | W::test_sessions_keep_when_gh_fails[no-gh] | ケース削除 | L。OSError捕捉が無くてもFileNotFoundErrorで停止し削除に進まない。unknown-pr のfail-closedと正常なsessions判断を残す |
| 11 | W::test_sessions_keep_a_session_without_state[[]] | ケース削除 | L。list状態は形検証または後段のキー参照で停止し削除に進まない。state欠落とlocked/session正常判断は維持 |
| 12 | L::test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped | 削除・assert移管 | D。同じ reported=true / PR未マージガードはtest_no_fix_needed_needs_a_merged_finalize_result_at_the_same_headに残る。不一致時cycle.state=planningのassertもその代表へ移す。続く実マージ成功の対照を残す |

計12ケース（5関数の削除、7個のparametrizeケースの削除）。parametrizeを1ケースへ縮約する際は不要な引数・分岐も除去する。共有helperは他の利用がある限り残す。

### 維持に回す候補

| 候補 | 判断と理由 |
| --- | --- |
| test_loop_skill_runs_only_when_explicitly_invoked | F∩S。自動マージ開始を防ぐ権限境界 |
| test_start_succeeds_when_herdr_hangs | 迷うため維持。以前のS判断を変更しない |
| test_check_options_has_no_external_side_effects | S。GitHub・レビュー・lock・runへの副作用防止 |
| test_create_records_its_phases_in_the_journal | 中断時の所有情報・回収判断を守るSが含まれる。順序assertだけの縮約も今回は行わない |
| test_start_records_options_and_effective_assignments | 担当の保存・後段への引き渡しを守る。固定値だけの縮約も今回は行わない |
| test_save_rejects_unknown_model_source | 来歴を誤って扱う可能性があるため維持 |
| test_load_state_rejects_tampered_previous_review | 外部パスの出力・利用者保護に関係し、迷うため維持 |
| test_destination_fingerprint_distinguishes_symlink_entries | S。種類の取り違えを防止 |
| test_snapshot_preserves_existing_index_lock / test_snapshot_does_not_refresh_index | S。利用者index/lockを変更しない |
| non_regular[symlink]/[fifo] | symlink参照境界とFIFO停止の独立した保護を残す |
| gh_fails[unknown-pr] / without_state[None] | fail-closedの代表として残す |
| explicit_model_outside_codex / save_uses_pinned_explicit_model_without_codex_metadata / normalizes_pr_repository_case | 正しい入力が通る対照を維持 |

両ディレクトリの全206テスト関数（収集297ケース）を読み取り監査した結果、上表以外は削除対象にしない。残るファイルの routing/identity/refs/ownership/path escape、記録保持、secret、停止確認、sandbox境界などの保護は維持する。

## 受け入れ基準

1. Dev Container・uv/Python 3.14・ローカルの偽CLI/一時gitリポジトリで検証する。実モデル起動は実装担当と指定レビューだけであり、テスト入力には本物のCLI/課金APIを使わない。
2. 上表の候補判断を実装・PRへ対応付ける。文字列の一致だけでなく、ガードの同一性と残る正例/負例で判断する。
3. 本PRの全収集件数は1309から12減る想定（1297）。対象297ケースは285となる想定。実測で照合し、増加や別領域の欠落は認めない。
4. 保存先改変、競合、モデル取り違え、repository指定、既存レビュー内容、merge誤報告を防ぐS/F∩Sを維持する。動作コード・SKILL.md・AGENTS.md・bashテスト・ローカルワールド・CIは変更しない。
5. `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、diff checkを実施し成功を確認する。
6. 新しいテスト関数・入力ケース・削除確認用テストは追加しない。#12の既存assertの移管のみ認める。
7. 残る4領域とIssue全体の棚卸し・完了判断は対象外。高速化#345も対象外。

## 変更前の証拠

- 全収集: 1309 tests collected in 5.27s（exit 0）。
- 対象2領域: 297 passed in 443.49s（exit 0）。
- ログ: `/workspaces/reso-world/tmp/agents/issue-344.utaqtap6/baseline-collection.log`、
  `/workspaces/reso-world/tmp/agents/issue-344.utaqtap6/baseline-review-tests.log`。
- 調査担当: sp-recon。読み取り監査約14分。報告用writeが子に無いため、返却した表をcontrollerがこの文書へ記録した。

## 実装・対象検証の記録

- 棚卸し表の12件はすべて表どおり削除/縮約。#12のplanning保持assertを残す代表へ移管した。他のS/F∩S・曖昧な候補は維持した。
- 変更ファイルはテスト2つとこのSpec/Planのみ。動作コードとSKILL.mdは不変。新規テスト関数・入力は無い。
- 指定担当の観測identity: opencode-go/deepseek-v4.1-flash、effort=max。1回目3261.66秒は他worktree変更の観測でrejected（未取込、因果は断定しない）。2回目374.44秒をacceptした。両試行stop_confirmed=true、cleanup retained=[]。
- 取込commit: fb7f66db254fc259bcca9a049f9dd3270451df81。
- controller取込後:285 passed in253.52s（exit0）、全体1297 collected in0.63s（exit0）。297→285/1309→1297で差分12。
- raw nodeidは15削除/3追加。3件は単一ケース化した既存入力のsuffix除去で、Usaturn/resoloop・unknown-pr・状態欠落の同じ入力を保持している。
- Task reviewer: 仕様準拠・品質Approved、Critical/Important/Minor指摘0。対象コードの後段ガードと保持代表を静的照合した。
- 最終HEADでの全体pytest・bash・layout、ブランチ全体レビュー・公開はこの記録の後で行う。証拠は /workspaces/reso-world/tmp/agents/issue-344.utaqtap6/ とPR本文へ残す。未実施の確認を成功とはしない。
- 残る4領域は未着手。このPRのマージでIssue #344全体を完了とはしない。
