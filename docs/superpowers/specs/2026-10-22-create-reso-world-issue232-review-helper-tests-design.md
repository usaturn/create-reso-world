# Issue #232: .agents/scripts・review-fix-planning・review-verify のテストを新しい採用基準で減らす

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/232（親 #228、ボード `test-reduction-board`、子のキー `review-helper-tests`。先行 #229 は completed、PR #240 は `main` にマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-22-create-reso-world-issue232-review-helper-tests.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-232-review-helper-tests`（branch `feat/issue-232-review-helper-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-22（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr #232 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #232`）まで行い、`--merge` により PR 修正ループを回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」、`AGENTS.md` の「テストの採用基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options`）: `max_cycles = 3`、`assign = {}`、`template = .devcontainer/agent-runner.toml`、`config = null`（いずれも既定の適用）。割り当て: レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー・修正の確認が `self`。`fallback` なし
- 実装の担当: `implement_task.py check` は `agents = ["self"]`・`self: true`（雛形の既定の適用。利用者の指定ではない）。このセッションが、サブエージェントに領域を分けて依頼する（D-232-2）
- 予約: `refs/heads/agent-claims/issue-232` = `b50af656cc4396d6d8d727754466dcec80db8742`（セッション `64c605ef-b8eb-4b82-b400-be797a1bb277`、2026-10-22T15:52:19Z）
- 基準: `origin/main` の `481a047`

## 意図

#228 の方針に従い、この領域（`.agents/scripts`、`review-fix-planning`、`review-verify`）のテストを、`AGENTS.md` の「テストの採用基準」で F（F∩S を除く）・L・D の余りに当たるものを消して減らす。残るのは S（F∩S を含む）と D の代表だけで、棚卸しの表に全てのテストの分類と理由を残す。数を合わせるために、気付けない損害を防ぐテストは消さない（#228 の決定 6）。

## 基準値（`481a047`、コミット済みの状態）

| 指標 | 値 |
| --- | --- |
| 件数 | 1,056 |
| 行数 | 9,919 |

ファイル別の件数: `test_agent_tmp.py` 21、`test_issue_budget.py` 15、`test_review_findings.py` 231、`test_review_records.py` 205、`test_review_target.py` 59、`test_finalize.py` 169、`test_review_fix_planning_skill_contract.py` 70、`test_run_roles.py` 49、`test_upsert_pr_comment.py` 75、`test_dispatch.py` 151、`test_evaluation.py` 11（`conftest.py` は 33 行）。

## 設計

### 1. 範囲と禁止

Issue 本文の「範囲と禁止」のとおり。変えてよいのは、この領域のテストと、使われなくなった経路のコードの撤去（`git grep` などで呼び出し元が無いと確かめたものだけ）、撤去した経路を説明する行だけである。`pr-review`・`pr-review-fix-loop`・`tools/test_support/`・ルートの `conftest.py`・`pyproject.toml`・`AGENTS.md`・ほかの領域は変えない。

### 2. 進め方

1. テストのファイルごとに、全てのテスト（関数・クラス・parametrize の群）を F・F∩S・L・S・D・撤去・迷いに分類する。S は防ぐ損害と重さ（高・中・低）、L は気付ける経路、撤去は使われていない根拠を書く
2. F・L・D の余り・撤去は消す。消したテストだけが使っていた fixture・補助も消す
3. 重さが高の守りで代表に絞ったものは、守る処理を一時的に壊した使い捨てのコピー（`/tmp` に `mktemp -d`）で、残したテストが失敗することを 1 回ずつ確かめる
4. `test_review_findings.py` の factory のうち `review-verify/tests/test_dispatch.py` が読み込むものは、`test_dispatch.py` を整理するまで残す（Issue の順序の注意）
5. 層をまたぐ重複は、守りを実装している側のテストを残す。`tools/agent_runner` が実装している checkout の事前検査は、run_roles・dispatch の側を消してよい（#228 の「層をまたぐ重複」）

### 3. 棚卸しの表

この節の下の「棚卸し」に、ファイル別の表を置く。同じ理由のテストはファイル・クラス・parametrize の群で 1 行にまとめる。

### 4. 検証

- 領域: `uv run --locked pytest .agents/scripts .agents/skills/review-fix-planning .agents/skills/review-verify`
- 全体: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check`
- 計測: Issue の「検証」のコマンド（コミット済みの状態）

## 受け入れ条件

1. 棚卸しの表があり、全てのテストに分類と理由がある
2. F（F∩S を除く）・L・D の余り・撤去したもののテストと、それだけが使っていた fixture・補助が消えている
3. 重さが高の守りで代表に絞ったものについて、一時的に壊したコピーで残したテストが失敗することを確かめ、結果を「検証の記録」に書いている
4. 残したテストが通る。全体の入口で、この変更による失敗が無い
5. 前後の件数・行数を「検証の記録」と Issue に書いている

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-232-1 ファイルごとの分類と削除を行い、削除は基準の定義だけで決める**
  - 選択: 11 のテストファイルを単位に、上の設計 2 の手順で分類して消す。件数・行数の目標値は設けず、基準に当たるものだけを消す
  - 別案: 行数の目標（基準値の 1/3）に合わせて、守りの軽いものから消す
  - 理由: #228 の決定 6。1/3 に届かない分は `integration` の一覧を見て利用者が決める。この子で気付けない損害を防ぐテストを消すと、取り戻せない
  - 停止条件: 分類に迷うものは残し、表に「迷い」と書く
- **D-232-2 実装は、領域を分けたサブエージェントに同期で依頼し、このセッションが commit・統合・検証する**
  - 選択: `superpowers:subagent-driven-development` の形で、テストのファイル単位の Task をサブエージェント（general-purpose）に依頼する。担当は自分のファイルとそのコードだけを変え、commit・push しない。棚卸しの行は担当のファイルの断片（セッションディレクトリ）に書かせ、このセッションが Spec に統合する
  - 別案: (a) このセッションが全て inline で行う、(b) runner の担当に依頼する（`--implement` の指定は無い）
  - 理由: 分類は 1,056 件を読む作業で、ファイルごとに独立している。1 つのファイルの読みと分類を子の文脈に閉じると、controller の文脈が持つ。同じファイルを同時に書かせない
- **D-232-3 順序は 2 段階にし、`test_dispatch.py` は `test_review_findings.py` の後にする**
  - 選択: 第 1 段階で `test_review_findings.py`、`test_review_records.py`、`test_review_target.py`・`test_agent_tmp.py`・`test_issue_budget.py`・`test_evaluation.py`、`test_finalize.py`、`test_run_roles.py`・`test_upsert_pr_comment.py`・skill_contract を並行して行う。第 2 段階で `test_dispatch.py`
  - 別案: 全て直列、または全て並行
  - 理由: `test_dispatch.py` は `test_review_findings.py` を読み込んで factory を使う。コードの撤去が複数のファイルにまたがるので、撤去の候補は担当が `git grep` で確かめ、別の担当の領域のコードは変えない
- **D-232-4 コードの撤去は、`git grep`・文書・雛形・設定からの参照で呼び出し元が無いと確かめたものに限り、根拠を表に書く**
  - 選択: #228 の決定 5 のとおり。確かめられないものは撤去せず、S か L として扱う
  - 別案: テストの無い経路を、使われていないと推定して撤去する
  - 理由: `review_records.py`・`review_findings.py`・`finalize.py` などは pr-review・pr-review-fix-loop・issue-to-pr からも使われる
- **D-232-5 重さが高の守りの確認は、使い捨てのコピーで 1 回ずつ行う**
  - 選択: `mktemp -d` で作ったコピーに守る処理を壊す変更を入れ、残したテストが落ちることを確かめる。作業ツリーのコードは壊さない。結果を「検証の記録」に書く
  - 別案: 作業ツリーで壊して戻す
  - 理由: Issue の受け入れ条件。作業ツリーを壊すと、他の担当の並行作業に影響する
- **D-232-6 branch は `feat/issue-232-review-helper-tests`、worktree は Issue の指定の `.worktrees/issue-232-review-helper-tests`**
  - 別案: `fix/`
  - 理由: 不具合の修正ではなく、テストの整理である

## 棚卸し

凡例: F・F∩S・L・S・D・撤去・迷い。S は「損害 / 重さ」。ファイルごとの見出しの下に、群ごとの行を置く。元の全テストがいずれかの行に入る（担当が収集名と突き合わせた）。

### `.agents/scripts/tests/test_review_findings.py`（231 件 / 2415 行 → 94 件 / 1687 行）

重さの凡例: 高=秘密漏れ・データ消失・誤対象の破壊・未検証マージ、中=誤った結果の報告・記録の取り違え、低=統計・表示。コードの撤去は無し（stats は `review-verify/evals/validation.md` が呼び、statement-candidates・validate・from-markdown・check-pair は pr-review・loop・review-verify・run_roles が呼ぶため）。

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| test_planning_accepts_new_and_legacy_outcomes | 3 | L | 受理側の誤りは保存時に例外で現れる。値の一覧の写し | 消す |
| test_v2_document_accepts_observed_identity_and_real_activities | 3 | D | v2 の正しく通る例の代表（拒否テストの対） | 残す |
| test_v2_document_requires_owner_provenance | 3 | L | 欠落は例外で現れる | 消す |
| test_v2_activity_rejects_invalid_duration | 5 | L | 型の拒否のみ | 消す |
| test_v2_timing_distinguishes_unknown_zero_and_waiting_overrun | 1 | L/低 | 時間の整合の拒否 | 消す |
| test_v2_input_and_accuracy_cannot_claim_different_sessions | 1 | S 中 | 入力と accuracy の取り違えを黙って通す | 残す |
| test_v2_source_must_resolve_to_an_input_file | 1 | S 中 | 出所の参照先の取り違え | 残す |
| test_v2_cycle_sources_keep_the_detection_head_across_updates | 6 | L | 誤拒否は保存時に例外で現れる | 消す |
| test_v2_rework_links_require_a_real_implementation_actor | 1 | L | session_id 欠落の例外 | 消す |
| test_valid_documents_pass | 5 | D | v1 の正しく通る例（拒否テストの対） | 残す |
| test_statement_candidates_section_is_required_only_for_fix_check | 1 | S 中 | fix_check の条件判定の節が無くても通る | 残す |
| test_invalid_statement_judgments_name_the_problem | 5 | L | 形の拒否 | 消す |
| test_check_statement_judgments_* のうち accepts / unjudged / unknown_and_repeated / different_to / requires_inconsistent_sites | 5 | S 中 | 判定漏れ・別の head の一覧・不整合の見落とし | 残す |
| test_check_statement_judgments_reports_a_different_from | 1 | D | different_to と同じ守り | 消す |
| test_cli_validate_checks_the_fix_check_against_its_candidates | 1 | S 中 | CLI が突き合わせを呼ばないと判定漏れが通る | 残す |
| test_cli_validate_fix_check_without_candidates_file_fails | 1 | L | メッセージ付き終了 66 | 消す |
| test_invalid_documents_name_the_problem（30 件を 4 件に） | 30→4 | S 中 4 / L 26 | 残す: failure_scenario 必須、confirmed の reproduction 必須、fix_check 必須、fix_check.to=reviewed_head（取り違え）。消す: スキーマ版・kind・enum・未知キー・sha・形式 | 4 件残す |
| test_unverified_verdict_requires_missing_checks | 1 | S 中 | unverified の理由欠落 | 残す |
| test_missing_checks_only_for_unverified | 1 | D | 上と対 | 消す |
| test_failure_scenario_is_optional_for_documentation_findings | 1 | D | failure_scenario 必須の対（正しく通る例） | 残す |
| test_duplicate_ids_are_rejected | 1 | S 中 | ID 重複で記録を取り違える | 残す |
| test_markdown_source_relaxes_reviewer_only_fields | 1 | L | 誤拒否は例外 | 消す |
| test_not_a_json_object_is_rejected | 1 | L | 例外 | 消す |
| test_control_characters_are_rejected_in_text | 1 | S 中 | 制御文字の混入（偽装） | 残す |
| test_parse_review_markdown_reads_active_findings_and_unverified_candidates | 1 | S 中 | コードブロック内見出し・決定済み節を数えない | 残す |
| test_parse_review_markdown_tolerates_empty_and_missing_sections | 1 | L | 空入力の挙動 | 消す |
| test_candidates_from_markdown_is_a_valid_markdown_source_document | 1 | S 中 | 変換結果の取り違え | 残す |
| test_check_pair_accepts_a_matching_pair | 1 | D | 対 | 残す |
| test_check_pair_names_each_mismatch（5→3） | 5→3 | S 中 | 欠落・severity 差・未確認候補の欠落を残す。D: 余分な指摘、位置の移動 | 3 件残す |
| test_stats_reports_false_positives_misses_late_detections_and_severity_drift | 1 | S 低 | 精度の統計の代表 | 残す |
| test_reference_key_drops_the_markdown_suffix | 1 | D | 下の either_reference_style が通る | 消す |
| test_stats_counts_severity_drift_with_either_reference_style | 2 | S 低 | .md 付き・なしの参照 | 残す |
| test_stats_without_any_cycle_document_reports_nothing | 1 | L | 空の出力 | 消す |
| test_provenance_stats_retains_adoption_after_resolution... | 1 | S 低 | 採用の数え方 | 残す |
| test_provenance_stats_separates_same_model_with_different_observations（7→2） | 7→2 | S 低/D | effort・session_id の代表 | 2 件残す |
| test_provenance_stats_separates_skill_revisions | 1 | D | 上と同型 | 消す |
| test_provenance_stats_does_not_apply_other_pr_or_head_decisions | 1 | S 中 | 別の PR・head の採否を適用 | 残す |
| test_provenance_stats_adopts_a_finding_fixed_in_a_later_round / does_not_credit_a_later_round_from_another_session | 2 | S 低 | 採用の帰属 | 残す |
| test_provenance_stats_matches_v2_adoption_to_the_original_session | 1 | D | 上の別セッションと同じ守り | 消す |
| test_provenance_stats_leaves_adoption_unevaluated_*（4 件） | 4→1 | S 低/D | 識別子が未観測 の代表だけ残す | 3 件消す |
| test_provenance_stats_adopts_with_at_least_one_observed_identifier | 3 | D | 正しく通る例は adopts 系が持つ | 消す |
| test_provenance_stats_keeps_a_matched_seat_when_another_round_is_unobserved | 1 | D | 同上 | 消す |
| test_stats_rejects_malformed_folded_records_without_a_traceback / empty_fold_state / names_records_pr | 8 | L | 例外・メッセージ付き 65 | 消す |
| test_legacy_findings_cannot_prove_the_actor_of_a_v2_adoption | 1 | D | unevaluated 系と同じ | 消す |
| test_v2_model_identity_cannot_contain_a_line_break（3→1） | 3→1 | S 中 | model への改行で偽装。1 件に | 2 件消す(D) |
| test_v2_matching_input_and_accuracy_still_reject_unusable_runtime_identity | 1 | D | 上と同じ偽装 | 消す |
| test_v2_primary_skill_can_be_explicitly_unobserved | 1 | L | 誤拒否は例外 | 消す |
| test_provenance_stats_attributes_waiting_and_rework / uses_planning_time / marks_legacy_identity | 3 | S 低 | 時間・やり直しの帰属 | 残す |
| test_provenance_stats_keeps_stage_separate_from_generic_runner_role / ignores_skill_array_order | 2 | D | 他の統計の代表で足りる | 消す |
| test_standalone_stats_reads_v2_planning_and_rejects_its_bad_duration | 1 | L | subprocess で CLI の終了コード | 消す |
| test_cli_validate_reports_problems_on_stderr / reports_unreadable_files | 2 | L | メッセージ付き 65/66 | 消す |
| test_cli_from_markdown_and_check_pair | 1 | S 中 | check-pair の不一致が 65 になる | 残す |
| test_cli_stats_reads_cycle_documents_under_verified | 1 | S 低 | cycle 以外を数えない | 残す |
| test_cli_stats_skips_lists... / names_the_file... / stops_at_a_list_whose_kind_or_mode_is_unknown | 6 | L/D | メッセージ付き 65 | 消す |
| test_review_run_accepts_each_status | 5 | D | 実行記録の正しく通る例 | 残す |
| test_review_run_started_before_prepare... / failed_in_prepare... | 2 | L | 誤拒否は例外 | 消す |
| test_review_run_rejects_inconsistent_fields（12→4） | 12→4 | S 中/L | success に outputs 無し、started に finished_at、by_severity 合計、時刻の逆転を残す | 8 件消す |
| test_run_stats_counts_completion_failures_timeouts_and_time_per_line | 1 | S 低 | 完走率の統計 | 残す |
| test_runs_do_not_change_the_existing_stats_keys / test_stats_cli_reads_runs_and_rejects_bad_ones | 2 | L | キー構造・メッセージ付き 65 | 消す |
| test_v2_planning_example_is_accepted... / test_format_document_examples_are_valid / test_format_document_commands_are_accepted_by_the_cli | 3 | F | 文書の記入例・コマンドの写し | 消す |
| test_from_markdown_refuses_findings_it_cannot_read | 5 | S 中 | 読めない指摘を黙って落とす（最終レビュー I-1 の再発防止） | 残す |
| test_from_markdown_still_reads_coverage_subsections_and_matching_summaries | 1 | D | 上の正しく通る例 | 残す |
| test_from_markdown_reads_an_unverified_section_that_says_none（4→2） | 4→2 | D | 正しく通る例 | 2 件消す |
| test_check_pair_refuses_unverified_candidates_it_cannot_read | 1 | S 中 | 未確認候補の取りこぼし | 残す |
| test_statement_candidates_lists_documents_naming_the_enclosing_state | 1 | S 中 | 修正で変わった条件を述べる文書の見落とし | 残す |
| test_extract_terms_skips_plain_words_and_excluded_directories | 1 | S 低 | 語の抽出 | 残す |
| test_statement_candidates_reads_code_spans_removed_from_documents | 1 | S 低 | 文書から消えたコードスパン | 残す |
| test_statement_candidates_puts_frequent_terms_in_common_terms / merges_terms_on_the_same_line | 2 | S 低/D | 表示・集約 | 消す |
| test_statement_candidates_keeps_the_excerpt_around_a_term_far_into_a_long_line | 1 | S 低 | 抜粋に語が残る（代表） | 残す |
| test_statement_candidates_keeps_a_short_line / joins_excerpts_of_distant_terms / merges_overlapping_excerpts | 3 | D | 抜粋の表示 | 消す |
| test_statement_candidates_does_not_count_a_term_inside_a_longer_word | 1 | S 低/迷い | 語境界。低なので消す | 消す |
| test_statement_candidates_finds_terms_containing_regex_characters | 1 | S 低 | 記号入りの語を落とさない | 残す |
| test_statement_candidates_ignores_documents_under_excluded_directories / with_only_excluded_changes_writes_an_empty_list | 2 | S 低/D | 除外ディレクトリ | 消す |
| test_statement_candidates_handles_deleted_files / handles_non_ascii_paths / ignores_user_diff_prefix_settings | 3 | S 中 | 削除・日本語パス・利用者の git 設定で候補を黙って落とす | 残す |
| test_cli_statement_candidates_writes_the_file | 1 | S 中 | 出力ファイルを書く | 残す |
| test_cli_statement_candidates_rejects_an_unknown_revision | 1 | S 中 | 失敗時に既存の出力を上書きしない | 残す |
| test_extract_terms_does_not_mistake_removed_dash_lines_for_headers / places_removed_lines_in_the_old_file / reads_changed_lines_of_documents | 3 | S 低 | 差分の読み取り | 残す |
| test_extract_terms_places_lines_of_a_deleted_file_where_they_were | 1 | D | removed_lines_in_the_old_file と同じ位置の守り | 消す |
| test_extract_terms_rejects_headers_it_cannot_read | 1 | L | 例外 | 消す |
| test_statement_candidates_lists_documents_for_a_template_only_change / reads_kebab_case_names | 2 | S 中 | 実際の見落とし（Issue #620・#555） | 残す |
| test_invalid_statement_candidates_name_the_problem | 7 | L | 形の拒否 | 消す |
| test_fix_evidence_accepts_executed_artifact_and_deleted_file | 1 | D | 対 | 残す |
| test_fix_evidence_requires_every_claim_and_changed_file | 2 | S 中 | 主張・変更ファイルの判定漏れ | 残す |
| test_fix_evidence_rejects_duplicate_judgments（2→1） | 2→1 | S 中/D | claims のみ | 1 件消す |
| test_fix_evidence_rejects_malformed_execution（4→2） | 4→2 | S 中 | 別 head の証拠・assumed の実行を拒否。D: exit_code・command | 2 件消す |
| test_artifact_claim_requires_executed_generated_evidence（3→2） | 3→2 | S 中 | static・exit_code≠0 を拒否 | 1 件消す |
| test_unchecked_evidence_requires_remaining_coverage（2→1） | 2→1 | S 中/D | 未確認を remaining に書く | 1 件消す |
| test_failed_evidence_requires_confirmed_finding（2→1） | 2→1 | S 中/D | 違反を指摘にする | 1 件消す |
| test_evidence_inventory_cannot_omit_a_fix_or_reuse_a_claim_id | 1 | S 中 | fix の主張漏れ・claim ID 再利用 | 残す |
| test_v2_fix_check_requires_evidence_without_breaking_legacy | 1 | S 中 | v2 の fix_evidence 必須 | 残す |
| test_cli_evidence_validation_reports_missing_inventory | 1 | D | cli_validate_checks と同じ配線 | 消す |
| test_claim_inventory_lists_all_changed_paths_including_rename_and_deletion | 1 | S 中 | 改名・削除を検査対象から落とさない | 残す |

壊したコピーでの確認（高の守りは無し。中の代表を `mktemp -d` のコピーで確認）: `check_statement_judgments` の "not judged"、`fix_evidence` の "not judged"、`check_pair` の severity 差の `problems.add` を無効化すると、5 件が失敗（unjudged、cli_validate_checks、check_pair_names_each_mismatch[severity]、fix_evidence_requires_every_claim[claims/files]）。


### Task 2: `.agents/scripts/tests/test_review_records.py`（205 件 → 51 件、1552 行 → 744 行）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| v2: session を render・extract・fold で保つ | 1 | S（低） | fold が provenance を黙って落とす記録の欠落 | 残す |
| v2: identity 欠落の拒否（parametrize 9）、session_id の不正（5）、unknown/sha256、重複 skills | 16 | L・D | 検査の拒否は `RecordError` で見える。session_id の `<!-- -->` は comment-marker-in-text と同じ守り | 消す |
| 正しい 2 つの記録が検査を通る | 1 | S | 何でも拒否する実装で通らないための通る例 | 残す |
| `VALID_VARIANTS` の通る例（12 件） | 12 | L | 過剰な拒否は投稿時に `RecordError` で見える | 消す |
| `INVALID_RECORDS` 75 件の群 | 75 → 11 | S（中）・D | 代表: agent_id（マーカー一致）、rerun と head の矛盾、skip の revisit_when、changed の previous_state、skip の再開に new_evidence、d1 の reproduction、重複 decision id、複数 decision にまたがる source、no_fix_needed と未決、fixes_pushed に fix 無し、コメントマーカー混入（記録ブロックの偽造）。残り 64 件は同じ検査器の別の項目で、違反は `RecordError` か同じ守りの別の組み合わせ（L・D） | 11 残す・64 消す |
| `validation_reports_every_problem`、record は object | 2 | L | 例外メッセージの内容だけ | 消す |
| `agent_id_for` のマーカー規則 | 4 → 2 | S（中） | 計画者の同一性（1 サイクル 1 計画者）の基準。例は通常名と `/` の 2 つ。`Cursor Grok 4.6`・`a / b` は D | 2 残す・2 消す |
| `agent_id_for("..")` 拒否 | 1 | L | 例外 | 消す |
| fold が空 | 1 | L | 空の出力は普段の利用で見える | 消す |
| fold: 最新の状態・source の統合・planner 履歴 | 1 | S（中） | 状態の取り違え | 残す |
| fold: 時刻と comment id の順 | 1 | S（中） | 古い記録で新しい状態を上書きする | 残す |
| fold: split した decision を分ける | 1 | S（中） | 判断の取り違え | 残す |
| fold: 別 PR の記録を拒否 | 1 | S（中） | 別の PR の記録を混ぜる | 残す |
| fold: expected_pr で期待外を指摘 | 1 | D | 上と read_state のテスト・CLI のテストが同じ守り | 消す |
| check_against: 次のサイクルを通す | 1 | S | 通る例 | 残す |
| `INVALID_NEXT_ROUNDS` 9 件 | 9 → 6 | S（中）・D | 残す: new なのに記録済み、inherited の state 変更、サイクル番号の飛び、別の PR、前の fix の脱落（記録の消失）、skip 参照の付け替え。消す: inherited-but-unknown（D）、changed-from-the-wrong-state（D、inherited と同じ照合）、new-part-of-a-recorded-reference（D、付け替えと同じ守り） | 6 残す・3 消す |
| check_against: 1 サイクル 1 計画者 | 1 | S（中） | 記録の上書き | 残す |
| check_against: 後のサイクルが有る更新の拒否 | 1 | S（中） | 記録の上書き | 残す |
| check_against: 前の hold を残した完了 | 1 | S（中） | 未完了を完了と報告する | 残す |
| check_against: 引き継いだ fix の d1 | 1 | S（低） | 再現記録の消失（迷い。低だが気付けない） | 残す（迷い） |
| check_against: 付け替えた参照の許容 | 1 | L | 過剰な拒否は見える | 消す |
| check_against: 分割後の参照を保つ（拒否 1、許容 2） | 3 → 1 | S（中）・L | 拒否だけ残す。許容 2 件は L | 1 残す・2 消す |
| check_against: 停止サイクルは前の fix を省ける（2） | 2 | L | 過剰な拒否は見える | 消す |
| 停止サイクルのカテゴリ保持（3）、具体的なカテゴリの要求（6） | 9 | L・D | 拒否は `RecordError`。stopped-without-reason の代表も上の群に無いが、検査の例外で見える | 消す |
| `round_marker`（保持・拒否） | 3 | L・D | compose の出力は collect の marker 照合のテストでも使う | 消す |
| 描画と取り出しの往復、CRLF、unicode 行区切り | 3 → 1 | L・S（低） | 往復と CRLF の失敗は `RecordError`。unicode 行区切りは実際に起きた分割による記録の破損の再発防止 | 1 残す・2 消す |
| extract: ブロック無し、2 ブロック、終了が先、fence 無し、不正 JSON | 5 | L | `RecordError` | 消す |
| compose_comment: マーカーの位置、本文中のマーカー、空本文、上限超過 | 4 | L | `RecordError`。位置の誤りは次サイクルの照合で「round must be 1」と見える | 消す |
| comments_from_api: 平坦・slurp 両形 | 1 | S（中） | gh の形を読み違えると記録が 0 件になり、全ページ読みが落ちる | 残す |
| comments_from_api: null body、id/body 欠落、gh のエラー（slurp 内を含む） | 4 | L | `RecordError` | 消す |
| collect: 信頼できる投稿者の状況コメントだけ読む | 1 | S（高） | 記録の偽造。信頼境界 | 残す |
| collect: 明示した trusted_login（CONTRIBUTOR・NONE） | 2 → 1 | S（中） | CONTRIBUTOR の読み取りが無いと記録が消える（#169）。関連の違いは D | 1 残す・1 消す |
| collect: 他人・空の login は信頼しない（5） | 5 → 3 | S（高） | 空同士の一致で信頼する不具合。他人／author 無し／両方空 を残す | 3 残す・2 消す |
| trusted_login でも権限による信頼は保つ（3） | 3 → 1 | S（中）・D | 関連の違いは同じ守り | 1 残す・2 消す |
| read_state: trusted_login で次のサイクルへ、PR 検査を回避しない、記録検査を回避しない、除外を保つ | 4 | D・L | collect/CLI のテストと同じ守り、`RecordError` | 消す |
| collect: 壊れたコメントをすべて名指し | 1 | S（中） | 壊れた記録を黙って飛ばすと記録を失う | 残す |
| collect: マーカーと記録の不一致 | 1 | S（高） | 別の計画者の記録として読む | 残す |
| read_state: 無視したコメントの一覧と PR の検査 | 1 | S（中） | 別の PR | 残す |
| 更新時に自分のコメントを除外 | 1 | S（中） | 更新が「記録済み」と拒否される／重複 | 残す |
| 先頭に 1 行足したコメントを一覧に出す | 1 | S（低） | 人が足した行で記録が黙って外れる（迷い。ignored に出る） | 残す（迷い） |
| CLI fold: 状態を出す | 1 | S（中） | 入出力のつなぎ | 残す |
| CLI fold: コメント無し、repo と pr の片方、gh のエラー | 3 | L | argparse、`RecordError`、空の出力 | 消す |
| CLI fold: 別 PR の記録を終了コード 65 で報告 | 1 | S（中） | `--repo/--pr` の配線が切れると別 PR の記録を混ぜる | 残す |
| CLI fold: 壊れた記録で終了コード 65 | 1 | S（中） | 失敗を成功と報告する | 残す |
| CLI fold: --trusted-login（None・usaturn・someone-else） | 3 → 2 | S（中） | 配線。someone-else は None と同じ守りで D | 2 残す・1 消す |
| CLI validate: --trusted-login | 1 | S（中） | 配線 | 残す |
| CLI validate: 前のコメントとの照合と --exclude-comment | 1 | S（中） | 更新時の照合と終了コード | 残す |
| CLI render、66（読めないファイル）、65（不正 JSON）、UTF-8 でない入力、未知の除外 ID | 5 | L | メッセージ付きの非 0 の終了・出力が見える | 消す |
| 文書の記入例: from-markdown が読める、compose が記入例を作る | 2 | L（F 寄り） | 記入例が古くなると、写した利用者が `RecordError` で気付く。文書の例を写すテストで、`review_findings` の import と正規表現も一緒に撤去 | 消す |

件数: 残す 51 / 消す 154（元 205）。収集名との突き合わせは `uv run --locked pytest --collect-only -q` の元の一覧（git HEAD 版）で全群を網羅した。


# Task 3 棚卸し（106 件 → 46 件）

## .agents/scripts/tests/test_review_target.py（59 → 23 件、820 → 468 行）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| test_parse_number_url_and_reject_other | 1 | L | 指定の誤りは EXIT_USAGE で止まる。誤った解釈は後段の gh が 404 で失敗 | 消す |
| test_github_repository_reads_https_and_ssh | 1 | D | remote 名の解釈。fork/上流の振り分けは resolve のテストと superpowers_context のテストが確かめる | 消す |
| test_review_directory_uses_lowercase_owner_and_repo_levels | 1 | L | 小文字化がずれても、保存と探索が同じ関数で同じ場所を指すので損害にならない（探索が NO_REVIEW で止まる） | 消す |
| test_validate_repository_rejects_unsafe_names | 7→3 | S（高: reviews/ の外への書き込み） | `usaturn/..` などの脱出を拒否。残り 4 件（`.`、`a`、`-a/b`、`a/b c`）は D | 残す（3 件に絞る） |
| test_naming_rules_keep_the_helper_messages | 1 | F | 文言の照合。branch 名の `/` は `-` に置換されるので脱出しない | 消す |
| test_fetch_pull_request_success | 1 | D | resolve の各テストが同じ経路（gh の呼び出し・PR の値）を通る | 消す |
| test_fetch_pull_request_not_found_when_repository_exists | 1 | L | 終了コードつきの停止 | 消す |
| test_fetch_pull_request_repository_missing | 1 | L | 同上 | 消す |
| test_fetch_pull_request_auth | 2 | L | 同上 | 消す |
| test_fetch_pull_request_without_status_is_api_failure | 1 | L | 同上 | 消す |
| test_fetch_pull_request_broken_body | 1 | L | 解析の例外 | 消す |
| test_fetch_pull_request_uses_the_canonical_name_after_a_rename | 1 | L | 改名後の名前は保存と探索で同じ値になり、取り違えない | 消す |
| test_resolve_number_uses_parent_origin | 1 | S（中: 別リポジトリの選択）の正例 | 番号だけの指定で親の origin を使う | 残す |
| test_resolve_fork_and_upstream_use_separate_directories_and_remotes | 1 | S（中: fork と上流の取り違え。head が fork の上流 PR も含む） | fork/上流のディレクトリと remote の分離 | 残す |
| test_resolve_lowercases_review_directory | 1 | L | 上記の小文字化と同じ | 消す |
| test_resolve_fork_pr_uses_base_repository | 1 | D | fork と上流の振り分けのテストが head_repository が fork の上流 PR で base 側を使うことを確かめる | 消す |
| test_resolve_stops_without_checkout_and_does_not_clone | 1 | S（高: 勝手な clone） | checkout が無いとき clone せず作業ツリーを変えない | 残す |
| test_resolve_uses_explicit_code_root | 1 | S（中）の正例（迷い: tests/scripts/test_superpowers_context.py にも正例がある） | code_root から target_root・base_remote・保存先への対応 | 残す |
| test_resoloop_route_requires_fork_remotes | 2 | D | 実装側 tests/scripts/test_superpowers_context.py（test_fork_requires_both_expected_remotes） | 消す |
| test_code_root_rejections | 4 | D | 実装側 test_superpowers_context.py（test_explicit_roots_must_be_absolute_checkout_roots、test_workspace_rejects_linked_code…、"has 0 remotes"、test_known_routes_select_base_and_reject_conflicting_explicit_root） | 消す |
| test_resolve_stops_without_parent_origin | 1 | D | 実装側 test_missing_unsupported_or_foreign_parent_origin_has_actionable_error | 消す |
| test_require_parent_root_needs_ignored_reviews | 1 | F∩S（レビュー結果が git に入る範囲） | reviews/ を無視していない親を拒否 | 残す |
| test_require_parent_root_rejects_linked_worktree | 1 | S（高: worktree の削除でレビュー結果を失う） | linked worktree を親として拒否 | 残す |
| test_find_review_directory_by_number | 1 | S（中: 取り違え）の正例 | 番号で探索 | 残す |
| test_find_review_directory_reports_missing_review_and_legacy_dirs | 1 | L | NO_REVIEW で止まる。メッセージは F | 消す |
| test_find_review_directory_does_not_cross_repositories | 1 | S（中: 別リポジトリのレビューを選ぶ） | fork と上流で番号が同じでも混ざらない | 残す |
| test_find_review_directory_lists_multiple_candidates | 1 | S（中: 任意の 1 件を選ぶ） | 複数候補は AMBIGUOUS で止まる | 残す |
| test_find_review_directory_ignores_symlinks_and_other_names | 1 | S（中: symlink 先の別ディレクトリを使う） | symlink と別名を無視 | 残す |
| test_find_review_directory_accepts_legacy_path | 1 | L | 旧配置の正例。壊れると PR の解決が失敗して止まる | 消す |
| test_find_review_directory_accepts_checkout_owner_repo_layout | 1 | S（中: 上流の base_remote を origin と取り違える）。迷い | checkout 内の owner/repo 配置 | 残す |
| test_legacy_fork_checkout_directory_is_ambiguous | 1 | S（中: fork と上流を推測で選ぶ） | 旧配置の fork checkout は推測せず止まる | 残す |
| test_legacy_fork_checkout_directory_uses_findings | 1 | D | findings による識別は from_findings_json・rejects_findings_for_another_pr が代表 | 消す |
| test_legacy_fork_checkout_directory_with_pr | 1 | D | `--pr` の不一致は test_pr_option_must_match_path が代表 | 消す |
| test_pr_option_must_match_path | 1 | S（中: 別 PR のレビューを使う） | `--pr` とパスの不一致を拒否（正例つき） | 残す |
| test_checkout_layout_must_match_target_root | 1 | S（中: 別 checkout を対象にする） | 正例つき | 残す |
| test_legacy_single_remote_checkout_directory | 1 | D | 正例は test_checkout_layout_must_match_target_root が持つ | 消す |
| test_legacy_checkout_without_github_remote | 1 | L | EXIT_PATH で止まる | 消す |
| test_find_review_directory_rejects_name_mismatch | 1 | S（中: 古い branch 名のレビューを使う） | ディレクトリ名と head branch の不一致を拒否 | 残す |
| test_find_review_directory_from_findings_json | 1 | S（中）の正例 | findings から PR を識別 | 残す |
| test_find_review_directory_rejects_findings_for_another_pr | 1 | S（中: 別 PR の findings） | 拒否 | 残す |
| test_find_review_directory_rejects_unidentifiable_path | 1 | L | EXIT_PATH で止まる | 消す |
| test_fetch_pull_head_preserves_tracking_refs_tags_and_fetch_head | 2 | S（高: 利用者の ref・tag・FETCH_HEAD を壊す。head が動いたときの拒否も含む） | 正例（head_moved=False）と拒否（True） | 残す |
| test_fetch_pull_head_separates_fork_and_upstream | 1 | S（中: ref の取り違え） | 保存先 ref の分離 | 残す |
| test_fetch_pull_head_stops_when_head_moved | 1 | D | 上の parametrize の head_moved=True と同じ守り | 消す |
| test_cli_review_dir_for_planning_keeps_the_range | 1 | L | 終了コード 0 だけの確認 | 消す |
| test_cli_reports_error_code_and_message | 1 | L | 終了コードと文言 | 消す |
| test_cli_resolve_prints_json | 1 | L | 出力形式が壊れれば呼び出し側が解析で失敗 | 消す |

## .agents/scripts/tests/test_agent_tmp.py（21 → 11 件、243 → 198 行）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| test_resolve_main_root_from_main_worktree | 1 | D | test_cli_root_from_every_cwd（親・worktree・外部 checkout・ワールド）が同じ解決を通る | 消す |
| test_resolve_main_root_from_subdirectory_and_linked_worktree | 1 | D | 同上 | 消す |
| test_resolve_main_root_rejects_submodule_checkout | 1 | S（中: 親でない checkout に tmp を作る）。迷い | submodule を親として拒否 | 残す |
| test_resolve_main_root_rejects_non_git_directory | 1 | L | AgentTmpError で停止 | 消す |
| test_make_session_dir_creates_unique_dirs_under_tmp_agents | 1 | S（中: 同名の上書き）の正例 | 一意なディレクトリ・git が汚れない | 残す |
| test_make_session_dir_accepts_version_like_topic | 1 | L | 受理できなければエラー | 消す |
| test_make_session_dir_rejects_invalid_topic | 8→3 | S（高: tmp/agents の外への作成） | `a/b`・`../x`・`.x` を残す。空・`-x`・大文字・65 文字・空白は D | 残す（3 件） |
| test_make_session_dir_refuses_when_tmp_is_not_ignored | 1 | F∩S（記録が git に入る範囲） | 無視されていない tmp を拒否 | 残す |
| test_make_session_dir_refuses_symlink_escaping_main_worktree | 2 | S（高: 親の外への書き込み）。`tmp`・`tmp/agents` は別の symlink の位置で、迷い | 残す |
| test_make_session_dir_refuses_symlink_into_unignored_directory | 1 | S（高: 追跡対象ディレクトリへの書き込み） | 残す |
| test_cli_root_from_every_cwd | 1 | S（中: 別の場所に記録） | 全 cwd で同じ親 | 残す |
| test_cli_mkdir_from_worktree_copy_writes_parent_tmp | 1 | S（中）の正例 | worktree の写しからでも親の tmp に作る | 残す |
| test_cli_rejects_invalid_topic_without_creating | 1 | D | 検証は make_session_dir のテスト（実装側）に任せる。終了コードは L | 消す |

## .agents/scripts/tests/test_issue_budget.py（15 → 6 件、167 → 92 行）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| test_user_wait_is_excluded_from_active_time | 1 | S（低: 能動時間の統計の誤り） | 残す |
| test_open_user_wait_counts_until_now | 1 | S（低） | 残す |
| test_checkpoint_is_due_after_threshold_until_recorded | 1 | S（低: checkpoint の見逃し） | 残す |
| test_user_wait_delays_checkpoint_due_time | 1 | S（低） | 残す |
| test_retry_limit_counts_same_reliability_signature | 1 | S（低: 再試行の上限の誤り） | 残す |
| test_single_safety_failure_is_reported | 1 | S（低） | 残す |
| test_inconsistent_ledger_is_rejected_with_line | 6 | L | LedgerError と行番号で止まる。受け入れても統計がずれるだけ | 消す |
| test_cli_records_and_shows_budget | 1 | L | CLI の終了コード・使い方の誤り | 消す |
| test_cli_rejects_corrupted_ledger_with_line_number | 1 | L | 解析エラーの行番号 | 消す |
| test_cli_keeps_ledger_readable_with_unicode_line_separators | 1 | L | 壊れた台帳は次の show が解析エラーで止まる | 消す |

## .agents/skills/review-verify/tests/test_evaluation.py（11 → 6 件、129 → 116 行）

文書の手順を取り出して実行するテストで、F ではない。ホストの Git 状態・フック・署名・シェル起動ファイルを使わない隔離は気付けない損害（高: 別リポジトリの index 書き換え、ホストのフック実行）。

| 群（attack） | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| clean | 1 | S の正例 | 隔離なしの通常経路 | 残す |
| git-dir | 1 | S（高）代表 | `GIT_` 接頭辞の除去（index・work-tree・common-dir・config-injection も同じ除去で防ぐ） | 残す |
| index、work-tree、common-dir、config-injection | 4 | D | 上の `GIT_` 接頭辞の除去と同じ守り | 消す |
| global-hooks | 1 | D | `GIT_CONFIG_GLOBAL` は `GIT_` 接頭辞の除去と /dev/null への固定で防ぐ。home-hooks が代表 | 消す |
| home-hooks | 1 | S（高: ホストのフック実行） | HOME の差し替え | 残す |
| xdg-signing | 1 | S（高: ホストの署名の実行） | XDG_CONFIG_HOME の差し替え | 残す |
| bash-env | 1 | S（高） | BASH_ENV の除去 | 残す |
| env | 1 | S（高） | ENV の除去（集合の別の要素なので bash-env と別） | 残す |

## 撤去したコード

なし。review_target.py・agent_tmp.py・issue_budget.py のどの関数も git grep（docs/superpowers を除く全体）で他の呼び出し元があり、テストだけが使っていたものは無い。test_evaluation.py のテスト内の分岐（消した attack の設定）だけを消した。


### `.agents/skills/review-fix-planning/tests/test_finalize.py`（169 件 → 61 件、1220 行 → 約 960 行）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| no_fix_result_requires_post_merge...（REPO/PUBLIC） | 2→1 | S 高 | マージ方式・--match-head-commit・Issue close の順序。PUBLIC は CI の群と重複 | 1 件残す |
| missing_or_wrong_verification（head/missing/failed/bool/no_base/short/upper/null） | 8→3 | S 高 / D | 未検証・base 不明で最終化しない。head・failed・short_base を代表に | 3 件残す |
| invalid_pr_state（draft/moving/mergeable/state） | 4→2 | S 高 / D | head 移動・draft を代表。mergeable/state は GitHub が拒否 | 2 件残す |
| public_ci_still_running（5） | 5→1 | S 中 / D | 待機後の再実行で完了する例を 1 件 | 1 件残す |
| public_ci_failure_or_absence（7） | 7→2 | S 高 / D | 失敗・失敗+実行中を代表。型崩れは例外で気付ける（L）、空は ci テストが担当 | 2 件残す |
| unknown_mergeable_waits | 1 | L | 待つだけの停止。誤っても未マージで止まる | 消す |
| wait_after_post_reruns_by_updating_the_same_comment | 1 | S 中 | 再実行で重複コメントしない | 残す |
| create_reso_world_ci_is_not_required_but_resoloop_ci_is | 1 | S 高 | 公開 PR を CI 無しでマージしない | 残す |
| a_repository_missing_from_the_ci_table | 1 | D | マージ範囲の検査が先に止めるので到達しない | 消す |
| repository_outside_the_merge_scope（3） | 3→1 | S 高 / D | 範囲外のマージ防止。meshy（CI 表にある）を代表 | 1 件残す |
| comment_rejection / moving_head_after_post / merge_success_without_merged_state | 3 | S 高 | 記録なしマージ・別 head のマージ・失敗を成功と報告 | 残す |
| already_merged_with_this_record...resumes | 1 | S 中 | Issue 更新の再開 | 残す |
| posted_record_counts_only_from_writer（3） | 3 | S 高 | 信頼できない投稿者の記録を採用しない（採用例 2 件+拒否） | 残す |
| merged_without_this_no_fix_record（3） | 3→2 | S 中 / D | none・different を代表（stopped は同じ分岐） | 2 件残す |
| manual_merge_after_a_stop_before_posting（3） | 3→1 | S 中 / D | draft を代表 | 1 件残す |
| issue_update_failure_is_reported_after_real_merge | 1 | S 中 | 失敗を成功と報告しない | 残す |
| malformed_record_is_stopped_before_network（3） | 3 | L | 検証例外で気付ける | 消す |
| unusable_result_path（3） | 3→1 | S 高 / L | symlink は別セッションの結果の上書き防止。missing・directory は OSError で気付ける | 1 件残す |
| cli_saves_and_reports / cli_exits_one / post_operation_save_failure | 3 | S 中 | 結果ファイルと報告の一致、終了コード、保存失敗でもマージ事実を残す | 残す |
| known_manual_merge_is_not_lost_on_later_read_failure | 1 | D | login 失敗のテストが同じ守りを確かめる | 消す |
| blank_status_body | 1 | L | 入力検証で停止、明示的な環境エラー | 消す |
| conflict_with_earlier_records | 1 | S 中 | 過去の記録と衝突したまま書かない | 残す |
| duplicate_round_comments_do_not_leak_markers | 1 | D | 表示だけの問題、上の群と同じ分岐 | 消す |
| foreign_or_malformed_closing_issue | 1 | S 高 | 別リポジトリの Issue を close しない | 残す |
| login_failure（8） | 8→2 | S 中 / D | fails の OPEN・MERGED を代表。empty・spec は同じ分岐 | 2 件残す |
| spec_commit_merges_the_spec_head（2） | 2→1 | S 高 | 正しく通る例。match-head-commit が Spec commit | 1 件残す |
| spec_commit_compare（30+1） | 31→5 | S 高 / D / L | wrong_parent・two_files・other_directory・subdirectory・script を代表。形の崩れは例外・環境エラーで気付ける、要求失敗は D | 5 件残す |
| spec_commit_requires_identical_record_posted（4）+ accepts_authenticated_user | 5→3 | S 高 / D | none・different・untrusted_author。stopped は同分岐、ME 採用は拒否側と対 | 3 件残す |
| invalid_spec_commit_stops_before_network（4） | 4→1 | S 高 / L | 他リポジトリの禁止が S。SHA の形式は L | 1 件残す |
| spec_commit_waits_until_pr_head / another_head（2）/ waits_for_mergeable / already_merged / merged_without_record / cli_spec_commit | 7 | L / D | 待機・停止のみ、同じ分岐を非 spec のテストが担当、argparse | 消す |
| spec_commit_merged_with_a_changed_diff | 1 | S 高 | マージ済みでも diff を確かめる | 残す |
| base_moved_after_verification（2）/ after_posting | 3 | S 高 | 未検証の base へのマージ防止、再実行で更新 | 残す |
| rerun_after_the_merge_does_not_compare_the_moved_base（2） | 2 | D | failed_confirmation/failed_merge の再実行が同じ経路を通る | 消す |
| unreadable_base_tip（14） | 14→2 | S 高 / D | renamed（別ブランチの応答）・request_fails を代表 | 2 件残す |
| base_branch_name_with_a_slash | 1 | L | 誤ると 404 で停止 | 消す |
| retargeted_base | 1 | S 高 | 付け替え先のブランチで照合 | 残す |
| merged_with_another_head（3）/ spec_parent | 4→1 | S 中 / D | another_head を代表。spec_parent は停止理由の区別だけ | 1 件残す |
| manual_merge_with_another_head_after_posting / manual_merge_before_posting（2） | 3→2 | S 中 / D | #207 でマージ済みを失わない | 2 件残す |
| closed_before_posting / unreadable_pr_state（2） | 3 | L | 未マージ・未確認で止まるだけ | 消す |
| failed_confirmation_after_the_merge / failed_merge_request | 2 | S 中 | 未確認を未マージと言わない、再実行で完了 | 残す |
| merge_commit_parent_must_be_the_verified_base（4） | 4→2 | S 高 | #206 の再現と対照。非 spec のみ | 2 件残す |
| only_a_record_verified_on_the_merge_commit（2） | 2→1 | S 高 | 同じ記録の再実行で Issue を閉じない | 1 件残す |
| manual_merge_on_a_moved_base | 1 | S 高 | 手動マージでも Issue を閉じない | 残す |
| unreadable_merge_commit（9） | 9→3 | S 高 / D | no_merge_commit・request_fails・wrong_sha を代表 | 3 件残す |
| merge_commit_read_failure_after_the_merge_recovers | 1 | D | 上の request_fails と failed_confirmation が担当 | 消す |

- 撤去したコード: なし（finalize.py は変更せず。分岐はすべて製品経路で使われる）
- 壊したコピーでの確認（.agents のコピー、一時ディレクトリは削除済み）: check_merge_parent 呼び出しの除去（7 件失敗）、マージ直前の check_base 除去（2 件失敗）、`first != verified` 無効化（3 件失敗）、マージ後の記録照合の無効化（3 件失敗）、マージ範囲検査の無効化（1 件失敗）。サブディレクトリの Spec 検査の無効化は代表を絞った時点で通ったため subdirectory を戻した（戻した後の確認は未再実施）
- 領域の pytest: test_finalize.py 61 件（subdirectory 追加後を含む）パス。ruff は環境に無く未実行（未使用 import・名前は目視で確認）


### Task 5 の棚卸し（review-fix-planning/tests の 3 ファイル。194 件 → 66 件）

#### test_run_roles.py（47 → 15 件）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| confined_implementation_does_not_block_on_unrelated_missing_registration | 1 | D | checkout の事前検査。tools/agent_runner/tests/test_checkout_policy.py・adapters/dsh/test_runner.py が unrelated_checkout_audit を確かめる | 消す |
| external_review_roles_list_their_write_exceptions_with_the_role | 1 | S 高 | 外部担当への書き込み例外の範囲（sandbox の境界）。過大な許可は気付けない | 残す |
| only_the_externally_assigned_role_lists_exceptions | 2 | S 高 | 同上。self の役割に例外を付けない | 残す |
| self_review_roles_ask_for_no_write_exceptions | 1 | D | 上の ("self","b") の例が同じ守り | 消す |
| unresolved_parent_stops_before_reserving_the_review | 1 | 迷い（S 中） | `write_exceptions`（親の解決）を `reserve_review` より前に求める順序。ほかの残すテストは `fix_context`・担当の事前拒否の別の分岐を通るので代表にならない。順序が崩れると 1 回だけの枠が消費される（再実行は「already reserved」で止まるのでエラーにはなる）。最後のレビューの指摘で戻した | 残す |
| single_call_uses_both_review_roles_and_retains_self_instructions | 3 → 2 | S 中 | 1 回枠の予約・記録・accept の拒否。("a","self") は ("self","self")・("a","b") と同じ分岐で D | 残す（1 件消す） |
| verified_input_mismatch_never_consumes_the_only_review | 3 → 2 | S 中 | 別 PR/HEAD の verified を受けて枠を消費する。malformed は FindingsError で L | 残す（malformed を消す） |
| v2_verified_input_is_still_accepted | 1 | L | 壊れれば検証エラーで起動に失敗する | 消す |
| second_review_is_refused_even_when_all_assignments_are_self | 1 | S 中 | 1 回枠の再予約の拒否（記録の上書き） | 残す |
| existing_lock_does_not_start_or_erase_another_call | 1 | S 高 | 競合の防止。他のセッションのロックを消さない | 残す |
| cli_reports_the_cause_of_an_input_error | 4 | L/D | exit 2 とメッセージ。reserved は second_review と D | 消す |
| binding_mismatch_is_rejected_before_reservation | 3 → 1 | S 中 | planning と PR の不一致で予約しない。source_head/revision は resolve_revision の例外で L | 残す（pr のみ） |
| unusable_fix_check_destination_stops_before_reservation_or_launch | 2 → 1 | S 中 | #177。保存先の検査は review-verify 側にもあるが、予約の前に止まる順序は run_roles の守り。verified-file は同じ守りで D | 残す（missing のみ。迷い） |
| environment_preflight_does_not_launch_or_consume_review | 6 | D | checkout の事前検査。agent_runner のテストが実装側 | 消す |
| role_projection_keeps_fallback_and_rejects_lost_constraints | 1 | L/D | 制約の欠落は ConfigError。fallback の維持は下の fallback 拒否テストが通る | 消す |
| invalid_writable_review_role_never_consumes_budget | 1 | L | ConfigError | 消す |
| implement_uses_only_implement_and_does_not_consume_review_budget | 1 | L | 壊れれば implement が失敗する。implement は planning を渡さない | 消す |
| review_assignment_that_cannot_run_the_helpers_stops_before_reserving_the_review | 8 → 2 | S 中 | DSH/codex の担当は戻せない枠だけを消費する（#671・#731）。dsh×agents×self-review と codex×fallback×fix-check の 2 件で関数と枠の両方を代表 | 残す（6 件 D で消す） |
| cli_rejects_an_assigned_review_agent_that_cannot_run_the_helpers | 4 | D/L | 上の run 層が守りの実装側。CLI は exit 2（L）。TEMPLATE（42 行）はこのテストだけが使うので一緒に消す | 消す |
| review_assignment_that_cannot_run_the_helpers_does_not_stop_implement | 2 | L | 壊れれば implement が起動できずエラー。正しく通る例は single_call の ("a","b") が残る | 消す |
| review_directory_tampering_is_not_accepted_or_cleaned | 1 | S 高 | review_dir の改ざんを受け取らず、消さない（データの消失）。verifier 側（Task 6）にも同種があるが run_roles 側の roles.json の記録を守る | 残す（迷い） |
| unconfirmed_stop_blocks_fix_check_accept_and_keeps_budget | 1 | S 中 | 停止未確認を成功と報告しない | 残す |

#### test_upsert_pr_comment.py（約 89 → 33 件）

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| sanitize_replaces_slash_space_and_double_hyphen | 1 | D | shared_module のテストが records.agent_id_for と一致を確かめる | 消す |
| agent_id_comes_from_the_shared_module_whatever_the_cwd | 1 | S 低 | agent id がずれると自分のコメントを見失い重複投稿する | 残す |
| compose_body_prepends_marker・keeps_a_leading_own_marker…・rejects_empty_and_foreign_marker | 3 | L/D | 空は CommentError（L）。マーカー付与は records 系のテストが payload で確かめる | 消す |
| record_less_body_rejects_round_markers_and_records_blocks | 2 | S 中 | 記録なしの本文から round マーカー/記録ブロックを偽造しない | 残す |
| find_own_comment_ignores_other_agents_and_rejects_duplicates | 1 | S 中 | 別担当のコメントを書き換えない | 残す |
| find_own_comment_matches_the_marker_as_a_whole_first_line | 1 | S 中 | 引用した marker のコメントを書き換えない | 残す |
| find_round_comment_matches_both_marker_lines_exactly | 1 | S 中 | 別サイクルの記録を上書きしない | 残す |
| only_trusted_authors_are_matched | 13 → 6 | S 高 | 信頼しない投稿者のコメントの書き換え。OWNER・自分(CONTRIBUTOR)・他人(CONTRIBUTOR/NONE)・大文字小文字・空どうしの 6 件を代表に。MEMBER/COLLABORATOR/FIRST_TIME/空の組み合わせは D | 残す（7 件 D で消す） |
| upsert_creates_when_no_own_comment・patches_existing_own_comment | 2 | D | records_post と own_login のテストが create/patch を通る | 消す |
| upsert_passes_the_requested_repository_to_gh_pr_view | 1 | D | 次のテストの URL 照合が、別リポジトリを書き込む損害の守り | 消す |
| upsert_stops_when_gh_resolves_a_different_repository | 1 | S 高 | 別リポジトリの PR へのコメント | 残す |
| validate_repo_rejects_anything_but_owner_name | 1 | L | CommentError | 消す |
| upsert_creates_instead_of_patching_an_untrusted_marker_comment | 1 | D | trusted_authors と own_login が同じ守り | 消す |
| record_less_upsert_updates_own_login_comment_and_ignores_untrusted | 1 | S 高 | 信頼しない同マーカーを更新しない・自分のを更新する（正しく通る例） | 残す |
| record_less_upsert_updates_a_comment_by_a_writer_who_is_not_the_login | 3 | D | trusted_authors の OWNER が同じ | 消す |
| comments_are_read_from_every_slurped_page | 1 | S 中 | 全ページを読まないと既存コメントを見落として重複する | 残す |
| a_malformed_comments_payload_stops_before_any_write | 1 | S 低 | 壊れた応答を空とみなして重複投稿しない | 残す |
| authenticated_login_strips_newline_and_rejects_blank | 1 | F∩S | 信頼する投稿者を gh の認証先（api user）で決める。PR の作者などを使うと別の利用者を信頼する | 残す |
| authenticated_login_failure_reports_what_gh_said | 1 | L | メッセージ付きの失敗 | 消す |
| login_is_read_after_the_pr_is_resolved_and_before_comments_are_listed | 2 | L | 順序が違っても結果は同じ | 消す |
| login_failure_stops_before_any_comment_write | 6 → 2 | S 中 | login が不明なまま書き込まない。gh-fails の 2 モードを代表に（empty/blank は authenticated_login のテストが同じ） | 残す |
| records_post_creates_a_round_comment | 1 | S 中 | 記録付き投稿の正しい形（正しく通る例） | 残す |
| records_post_updates_the_same_round_after_the_push | 1 | S 中 | 同じサイクルを重複させない | 残す |
| records_post_updates_the_same_round_when_only_recorded_at_differs | 1 | D | round 単位で照合するので上と同じ | 消す |
| records_post_creates_a_new_comment_for_the_next_round | 1 | S 高 | 前のサイクルの記録を上書きしない（記録の消失） | 残す |
| records_post_accepts_a_review_records_v2_record | 1 | L | 検証エラーで気付く。記録の検証は review_records のテスト側 | 消す |
| records_post_ignores_untrusted_comments_that_carry_markers | 1 | D | 次の contributor のテストと trusted_authors | 消す |
| records_post_updates_own_contributor_round_comment_and_ignores_forged_ones | 1 | S 高 | 偽造コメントを更新・照合に使わない | 残す |
| records_post_reads_prior_round_written_by_own_contributor_login | 1 | S 中 | #169 の再発防止 | 残す |
| records_post_does_not_read_rounds_of_other_contributors | 1 | S 高 | 他人の記録を履歴に使わない | 残す |
| records_post_rejects_an_invalid_record_before_any_gh_call | 1 | L/D | 記録の検証は tools 側（.agents/scripts/tests/test_review_records.py）の守り | 消す |
| records_post_rejects_a_different_model_name_before_any_gh_call | 1 | S 中 | 別名義の記録を投稿しない（迷い） | 残す |
| records_post_rejects_a_record_for_another_pull_request | 1 | S 中 | 別 PR の記録 | 残す |
| records_post_requires_the_pull_request_head | 2 | S 中 | 古い HEAD の記録 | 残す |
| records_post_rejects_a_closed_pull_request | 1 | 低 | 閉じた PR への投稿は実害が小さい | 消す |
| records_post_stops_when_another_agent_recorded_the_round | 1 | S 高 | 他担当の記録を上書きしない | 残す |
| records_post_stops_when_a_later_round_exists | 1 | S 中 | 古いサイクルの上書き | 残す |
| records_post_requires_earlier_fix_decisions | 1 | D | prior_round のテストの後半と同じ守り | 消す |
| records_post_rejects_no_fix_needed_with_pending_decisions | 1 | S 中 | 保留を残して完了と記録しない | 残す |
| records_post_stops_on_a_broken_record_and_names_the_comment | 1 | 低/D | メッセージ付きの停止 | 消す |
| records_post_stops_on_duplicate_round_comments | 1 | S 中 | 重複時にどちらかを書き換えない | 残す |
| records_post_rejects_markers_in_the_body…・over_the_github_limit…・accepts_multi_line_free_text | 3 | D/L | 前者は record_less の守りと同じ、2 つ目は GitHub が 422、3 つ目は review_records の往復 | 消す |
| cli_*（posts_with_a_records_file・posts_a_record_less…・reports_every_problem…・rejects_an_unreadable…・exits_64_when_the_login…） | 6 | L | argparse・exit 64 とメッセージ。実装の守りは upsert 層に残す | 消す。CLI_ARGV も消す |

#### test_review_fix_planning_skill_contract.py（70 → 18 件）

SKILL.md の手順を取り出して実際に実行するテストなので F ではない。守りの実装は tests/scripts/test_superpowers_context.py（superpowers_context.py）側。ここは SKILL.md の手順が resolver を正しく呼ぶかを代表で確かめる。シェルの差（bash/zsh/zsh-nounset）は外部 cwd の正常系だけで確かめ、停止の各条件は bash のみ（D）。

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| status_comment_snippet_escapes_heredoc_and_pins_repository | 1 | F∩S（迷い） | 本文の文字列で判定する F。ただし --repo の固定は別リポジトリへの投稿、未エスケープのバッククォートはブランチ名のコマンド実行を防ぐ | 残す |
| fix_context_uses_real_parent_helper_from_external_cwd | 3 | S 高 | 正常系。3 シェルで word splitting・nounset の差を代表 | 残す |
| fix_context_stops_before_later_mutation | 30 → 5 | S 高 | 誤った対象への破壊操作の前に止まる。parent-omitted・duplicate-base・doc-branch・head-ambiguous・helper-missing（SKILL の手順に固有の分岐）を bash で。missing/unsupported-origin・code-subdir・head-missing・head-branch は resolver 側のテストと D、シェル違いも D | 残す（25 件消す） |
| fix_context_verifies_known_repository_worktree_membership | 9 → 3 | S 高 | 別 checkout を対象にしない（valid/same-url-clone/conflict）。bash のみ | 残す |
| status_snippet_revalidates_before_comment_mutation | 9 → 2 | S 高 | コメント変更の直前に再検証（missing-context-helper・wrong-doc-branch）。missing-origin は resolver と D | 残す |
| fix_initial_planning_does_not_confuse_pr_branch_metadata_with_head_validation | 3 → 1 | S 中 | bash のみ | 残す |
| fix_context_validates_effective_push_destinations | 15 → 3 | S 高 | 誤った push 先。split・wrong-single・fallback を bash のみ（mixed/duplicate は resolver 側と D） | 残す |

#### 件数・行数

| ファイル | 件数 前→後 | 行数 前→後 |
| --- | --- | --- |
| test_run_roles.py | 47 → 15 | 725 → 438 |
| test_upsert_pr_comment.py | 約 89 → 33 | 840 → 558 |
| test_review_fix_planning_skill_contract.py | 70 → 18 | 231 → 219 |
| 合計 | 194 → 66 | 1796 → 1215 |

#### 撤去したコード

なし。run_roles.py・upsert_pr_comment.py の関数・クラスは、すべてスクリプト内か loop.py などの呼び出し元がある（git grep で確認）。SKILL.md は変更なし。

#### 壊したコピーでの確認（`mktemp -d` のコピー、終了後に削除）

- upsert の `_trusted` を常に True にする: 6 件失敗（own_contributor・trusted_authors ほか）
- `_trusted` の `bool(trusted_login)` を外す: trusted_authors[CONTRIBUTOR---False] が失敗
- run_roles のロック競合の拒否を外す: 4 件失敗
- 再予約の拒否を外す: 4 件失敗
- self-review の書き込み例外を付けない: 2 件失敗
- planning の PR/HEAD 照合を外す: 3 件失敗
- verified の PR/HEAD 照合を外す: 5 件失敗

#### pytest

`uv run --locked pytest .agents/skills/review-fix-planning/tests --ignore=.../test_finalize.py`: 66 passed。`uvx ruff check --select F` は通過（リポジトリに ruff が無く uvx ruff 0.17.1 で実行。import 整形 I001 は既存の書式）。


## .agents/skills/review-verify/tests/test_dispatch.py（151 → 61 件）・conftest.py（変更なし、managed_state は test_evaluation.py も使用）

層をまたぐ重複の確認: checkout の事前検査・登録の監査は tools/agent_runner（test_checkout_policy.py・test_workspace.py・test_runner.py）が実装側。review_dir の使えない保存先（#177）・snapshot・改ざん検出は dispatch.py 自身が実装（run_roles は verifier.check_review_directories / snapshot_review / review_changes を呼ぶだけで、test_run_roles.py に残るのは予約・起動しない確認の 1 件）なので、dispatch 側を残し代表に絞った。

| テスト/群 | 件数 | 分類 | 理由 | 結果 |
| --- | --- | --- | --- | --- |
| test_confined_dispatch_passes_result_guard_with_unavailable_unrelated_checkout | 1 | S 中 | 無関係な checkout の欠落で結果検査が誤って止まる/通るのを防ぐ（check_batch は dispatch の実装、正しく通る例） | 残す |
| test_self_assignment_keeps_all_registrations_with_a_retained_dsh_fallback | 1 | D | agent_runner の test_checkout_policy（retained fallback / self override）が実装側 | 消す |
| test_self_returns_complete_input_without_launching_implementation | 1 | S 低 | self が担当を起動せず入力を返す（迷い: 低） | 残す |
| test_external_runs_only_fix_check_and_preserves_observed_identity [0,1] | 2 | S 中 | 失敗を成功と報告しない、観測した identity の記録 | 残す |
| test_external_fix_check_request_lists_its_write_exceptions | 1 | S 高 (F∩S) | 外部担当に与える書込み許可の範囲（サンドボックス境界） | 残す |
| test_self_fix_check_asks_for_no_write_exceptions | 1 | S 中 | self に書込み例外を与えない | 残す |
| test_invalid_fix_check_assignment_is_rejected_before_launch [multi, text] | 2 | D/L | ConfigError の例外（L）。writes と同じ検査の別入力 | 消す |
| 同 [writes]（test_writing_fix_check_role_is_rejected_before_launch に改名） | 1 | S 中 | 書込み可の役割を fix-check に使うと例外なしで書込み担当が走り得る | 残す |
| test_prefixed_named_skill_digest_is_not_recorded_as_a_fake_path | 1 | S 低 | 偽のパスを記録しない | 残す |
| test_multiple_unlocated_skills_keep_raw_observations_without_duplicate_paths | 1 | D | 上と同じ unknown 化の別入力 | 消す |
| test_unobserved_identity_is_unknown_not_requested | 1 | S 中 | 要求したモデルを観測値と偽らない（記録の取り違え） | 残す |
| test_incomplete_or_unresolvable_request_is_rejected_before_output [to-HEAD] → test_mutable_revision_is_rejected_before_output | 1 | S 中 | 動く参照(HEAD)を許すと別 commit を検証して成功と報告し得る | 残す |
| 同 [残り 15: 大文字/短い SHA、from 0*40、fix_sections 3、fix_ids 5、extra、相対パス 3] | 15 | L | ValueError / pydantic の検証で例外・メッセージ付き非 0 | 消す |
| test_every_request_field_is_required_before_output | 7 | L | pydantic の必須欠落の例外 | 消す |
| test_explicit_fallback_keeps_the_actual_agent_and_observed_identity | 1 | S 中 | fallback 時に実際の担当を記録する | 残す |
| test_time_limits_follow_the_projected_deadline [3600, 400] | 2 | S 低 | 上限 1800 の丸めと短い期限の予約（代表 2 件） | 残す |
| 同 [1800, 600] | 2 | D | 同じ計算の別入力 | 消す |
| test_self_prompt_embeds_the_same_time_limits | 1 | S 低 | self の指示と dispatch.json の時間枠の不一致（迷い） | 残す |
| test_dispatcher_skill_digest_is_the_hash_of_the_file_bytes | 1 | D | test_observed_hash_matching… が同じ digest を使い、壊れれば失敗する | 消す |
| test_observed_hash_conflicting_with_the_dispatched_skill_is_unknown / matching_is_kept | 2 | S 中 | 適用した skill と食い違う観測値を採用しない / 一致なら残す（正例） | 残す |
| test_accept_saves_the_tool_output_unchanged_with_the_observed_verifier | 1 | S 高 | 受理の正例、sidecar 無改変、verifier 差し替え | 残す |
| test_accept_rejects_a_different_pr_without_changing_outputs [new-output-repository, existing-output-number] | 2 | S 高 | 別 PR の結果で保存先を上書き（記録の上書き） | 残す（4→2） |
| 同 [new-output-number, existing-output-repository] | 2 | D | 同じ比較の別組み合わせ | 消す |
| test_accept_rejects_a_missing_or_malformed_trusted_pr_before_output [missing-pr, boolean-number] | 2 | S 中 | 凍結した PR が読めないとき payload へ fallback しない / bool を番号と誤認しない | 残す |
| 同 [残り 11] | 11 | D/L | pydantic の検証（L）と同じ守りの別入力 | 消す |
| test_accept_uses_the_frozen_pr_after_the_original_verified_file_changes | 2 | S 高 | 可変な元ファイルで対象 PR を差し替えさせない（正例を含む） | 残す |
| test_accept_rejects_a_primary_skill_not_applied_by_dispatch… [path, sha256-d] | 2 | S 中 | 適用していない skill の記録を受理しない | 残す |
| 同 [sha256-unknown] | 1 | D | 同じ比較 | 消す |
| test_accept_keeps_the_applied_skill_when_identity_was_not_observed | 1 | S 中 | 正例（未観測でも受理） | 残す |
| test_accept_rejects_a_payload_that_differs_from_the_tool_output [drop_changed_file, rewrite_tool_candidate, drop_tool_term, different_fix_ids, extra_key, unjudged_candidate] | 6 | S 高/中 | check_inventory の別分岐（key 一致、terms、candidates の先頭一致、fix_ids、payload の形、judgment）ごとに代表 | 残す |
| 同 [drop_tool_candidate, drop_claim] | 2 | D | 先頭一致 / key 一致の分岐に既に代表がある | 消す |
| 同 [missing_key] | 1 | L | payload の形の拒否は exit 1 とメッセージ | 消す |
| test_accept_allows_candidates_and_terms_the_verifier_appended | 1 | S 中 | 正例（追記は許す） | 残す |
| test_accept_does_not_attribute_a_disappeared_checkout_to_content_changes | 1 | S 中 | 監査不能を「内容変更」と取り違えない | 残す |
| test_fix_check_environment_preflight_does_not_launch [moved] | 1 | S 中 | main が environment として報告し起動しない、repair 後の正例を含む | 残す |
| 同 [missing, locked] | 2 | D | agent_runner の test_workspace（locked/prunable/missing の事前検査）が実装側 | 消す |
| test_accept_rejects_a_verifier_candidate_inserted_before_the_tool_candidates | 1 | D | rewrite_tool_candidate と同じ「先頭一致」分岐 | 消す |
| test_accept_rejects_outside_changes_and_dispatch_exits_1_for_them | 1 | S 高 | 呼び出し元 repository への外部書込みを受理しない | 残す |
| test_dispatch_main_exits_1_and_names_outside_changes | 1 | S 中 | 終了コード 0 だと汚染された結果を成功と扱う | 残す |
| test_accept_rejects_malformed_checkout_diagnostics [None] | 1 | S 中 | 改ざん・欠落した監査欄を無変更と読まない | 残す |
| 同 [unavailable, diagnostics2, diagnostics3] | 3 | D | 同じ検査 | 消す |
| test_accept_rejects_an_unconfirmed_stop / _a_failed_run | 2 | S 高/中 | 停止未確認・失敗を受理しない | 残す |
| test_accept_rejects_self | 1 | D | state != success の同じ検査（failed run） | 消す |
| test_accept_exits_2_when_the_review_directory_is_missing / _without_dispatch_json | 2 | L | メッセージ付き非 0 の終了 | 消す |
| test_main_exits_0_for_self / test_cli_self_dispatches_without_an_external_adapter | 2 | L | CLI の import・起動の失敗は明らかなエラー | 消す |
| test_main_exits_1_for_a_failed_run | 1 | S 中 | 失敗を成功と報告しない | 残す |
| test_main_names_the_invalid_request_field_without_its_value | 1 | S 中 | 入力値を stderr に漏らさない | 残す |
| test_main_names_a_config_error_category / test_main_names_an_unresolvable_revision | 2 | L | エラーメッセージの文面 | 消す |
| test_review_directory_changes_are_rejected_before_publishing [ignored-create, outside-overwrite, outside-delete, outside-chmod, outside-symlink]（valid_payload は True のみ） | 5 | S 高 | 保存先の改ざん（gitignore 内を含む）を公開前に拒否。変更の種類ごとに代表 | 残す（24→5） |
| 同 [残り 19: rename 4、他の組み合わせ、payload 無効 12] | 19 | D | 同じ snapshot 比較の別組み合わせ。無効 payload でも変更を検出する守りは test_accept_checks_changes_since_dispatch_even_with_an_invalid_payload | 消す |
| test_accept_checks_changes_since_dispatch_even_with_an_invalid_payload | 1 | S 中 | 起動後の変更を payload より先に検出 | 残す |
| test_unchanged_existing_results_and_temporary_probe_outputs_are_allowed | 1 | S 中 | 正例（何でも拒否する実装を防ぐ） | 残す |
| test_symlink_publication_directories_are_rejected_without_writing_referents [verified] → test_symlink_verified_directory_is_rejected_without_writing_referent | 1 | S 高 | verified の symlink 先へ書かない | 残す |
| 同 [review_dir] | 1 | D | 祖先 symlink（test_initial_ancestor_symlink…）が同じ守り | 消す |
| test_accept_rejects_a_late_verified_directory_symlink | 1 | S 高 | 起動後の symlink で referent に書かない | 残す |
| test_unusable_review_directory_is_rejected_before_launch… [missing-probe, verified-file-self] | 2 | S 高 | 保存できない保存先で 1800 秒の担当を起動せず、状態を変えない（#177）。実装は dispatch.py | 残す（6→2） |
| 同 [file ×2, missing-self, verified-file-probe] | 4 | D | 同じ検査の別組み合わせ | 消す |
| test_accept_lists_a_verified_file_created_after_dispatch | 1 | L | 例外にせず列挙するのは拒否の文面。拒否自体は late symlink テストが担う | 消す |
| test_dispatch_does_not_read_the_review_directory_without_stop_confirmation | 1 | S 低（迷い） | 停止未確認中に保存先を読まない | 残す |
| test_unavailable_review_audit_never_means_unchanged | 1 | S 高 | 監査不能を無変更と扱わない・内容を stderr に出さない | 残す |
| test_initial_snapshot_cannot_silently_skip_an_unreadable_subdirectory | 1 | S 中 | 読めない subdir を飛ばした不完全な snapshot | 残す |
| test_initial_ancestor_symlink_rejects_without_launch_or_any_state_change [3] | 1 | S 高 | 祖先 symlink を起動前に拒否し状態を変えない | 残す |
| 同 [1] | 1 | D | 深さ違い | 消す |
| test_ancestor_replaced_after_dispatch_is_not_unchanged_or_accepted | 1 | S 高 | 起動後の祖先差し替えを受理しない | 残す |
| test_dispatch_observes_an_ancestor_replaced_before_the_worker_stops | 1 | D | 前項と同じ snapshot の照合。review_changes の記録は変更テスト群が確認 | 消す |
| test_accept_rechecks_destination_after_validation… [inventory-ancestor, validation-root, validation-contents] | 3 | S 高 | 検証中の保存先の差し替え・既存結果の上書きを防ぐ（記録の上書き） | 残す（6→3） |
| 同 [ancestor-validation, root-inventory, contents-inventory] | 3 | D | チェックポイント違いの同じ再照合 | 消す |
| test_identical_contents_in_a_replacement_review_directory_are_not_accepted | 1 | D | rechecks の root 変異（同内容の複製）と同じ | 消す |

conftest.py: managed_state は test_dispatch.py・test_evaluation.py（Task 3）が使うので変更なし。

## 検証の記録

（実装後に追記する）
