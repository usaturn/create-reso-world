# Issue #231: pr-review 系テストの棚卸しと削減

- 状態: draft
- 対象: `usaturn/create-reso-world` / [Issue #231](https://github.com/usaturn/create-reso-world/issues/231)
- 基準: `origin/main` `ad89c150bc9a269921088ee63c1ccbd109e93b16`（2026-10-24 の着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-24-create-reso-world-issue231-pr-review-tests.md`
- 実行許可: 利用者の `$issue-to-pr #231 --merge`。通常の設計判断、実装、検証、commit、push、PR 作成、PR 修正ループと、その結論に従う `finalize.py` のマージを許可する。これは本 Spec の内容の承認を意味しない。

## 目的と境界

親 Issue #228 の 2026-10-21 の決定と、`AGENTS.md` の「テストの採用基準」に従い、`.agents/skills/pr-review/tests/` と `.agents/skills/pr-review-fix-loop/tests/` のテストを棚卸しする。F（F∩S を除く）、L、D の余りと、使われなくなった経路のテストを消す。残すのは S、F∩S、S の代表、および証拠が足りない「迷い」である。全テストを分類した表と理由をこの Spec に残す。

対象のテストは着手時に 514 件、追跡ファイルは 8,830 行。内訳は `pr-review` 280 件、`pr-review-fix-loop` 234 件。Issue 作成時の 548 件・9,626 行は古い見積もりなので、今回の前後比較には現在の `origin/main` を使う。

変更できるのは #231 本文の「変えてよいもの」に限る。`.agents/scripts/`、`review-fix-planning`、`review-verify`、`tools/test_support/`、ルートの `conftest.py`、`pyproject.toml`、`.devcontainer/run-tests.bash`、ほかの担当のコード・テスト、`AGENTS.md` は変更しない。`SKILL.md` と説明文書を変える場合は、撤去した経路の説明だけを消す。現行の `pr_review_workspace.py`、`review_run.py`、`loop.py` のサブコマンドと JSON は、呼び出し元のない旧経路を除いて変えない。

## 依存と現行の入口

- #229 は `state_reason=completed` で close され、PR #240 は `main` にマージ済み。新基準は着手時の `AGENTS.md` にある。
- `pr-review` の現行入口は `review_run.py prepare` → レビュー → `complete`。`pr_review_workspace.py create --target` は内部で使用する。
- `repo-cleanup-after-merge` は `pr_review_workspace.py sessions --repo` を呼び、version 7 と 8 の session を扱う。version 7 の読取を撤去対象にしない。
- `pr-review-fix-loop` の `check-options` は `issue-to-pr` の事前検査で使う。`start` 以降の記録・ロック・レビュアーの照合は、誤った PR のマージや記録の混入を防ぐ。

## 採用する進め方

テスト関数と parametrize の群を単位に F / F∩S / L / S / D / 撤去 / 迷いへ分類する。L は実際にエラーとして現れる経路を示し、S は防ぐ損害と重さ（高・中・低）を示す。D は同じ守りの代表を選び、拒否の代表には通る例を残す。曖昧なものは「迷い」として残す。消したテスト専用の fixture は消す。`tools/test_support/` の未使用名は棚卸しだけに記録し、変更しない。

旧 `create --repo/--commit`、`inspect`、`abandon` は呼び出し元の検索結果を踏まえて撤去可否を決める。歴史文書の記載だけでは現行の呼び出し元とみなさず、現行スキル、スクリプト、設定、雛形、手元にある ResoLoop 系 checkout を確認する。version 7 の保存済み session の読取は、後片付けの現行手順が使うため残す。

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | #228 の決定と `AGENTS.md` の分類をそのまま適用する | 件数を先に決めて削る | S の損害を残す削減は #228 の決定 6 に反する | 利用者の `$issue-to-pr #231 --merge` と #228 の確定済み判断 |
| D2 | 現行 514 件・8,830 行を前値にする | Issue の見積もり 548 件・9,626 行を前値にする | 作業対象の `main` が進んでいる | #231 の前後計測の条件 |
| D3 | version 7 の session 読取と `sessions` を残す | 古い版を一括撤去する | `repo-cleanup-after-merge` に現行の呼び出し元がある | #231 の「呼び出し元が無いと確かめた場合を除く」 |
| D4 | 共有 fixture は使用箇所を照合してから消す | テスト数だけで一括削除する | 残す S の検査能力と現行の後片付けを守る | #228 の決定 5、#231 の受け入れ条件 |
| D5 | `--merge` の既定は最大 3 サイクル、inspect は `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` | 独自の担当・サイクル数を加える | 利用者の引数は `--merge` だけであり、`check-options` が返した設定を使う | 利用者の指定と既定値を区別する。設定の検査は成功 |
| D6 | Plan の実装担当は `self` とする | 暗黙に別担当へ切り替える | `implement_task.py check` の結果は `agents:[self]`、`self:true` | 雛形と個人設定の既定を適用。利用者は `--implement` を指定していない |
| D7 | 旧 `create --repo/--commit`、`inspect`、`abandon` と version 7 の読取を残す。`legacy_review` 返却値も今回の API 変更に含めない | 非テスト caller の検索結果だけで旧 API を撤去する | `noninteractive.md` が他 caller との互換を明記し、`repo-cleanup-after-merge` は version 7 を回収に使う。リポジトリの外の全 caller 不在は確定できない。旧配置のレビューを黙って前回結果に採用しない S も維持する | #228 の「使われていないことを確かめられたものに限る」。証拠が足りないので撤去しない |

## 棚卸しの表

関数単位で 269 件、parametrize を展開すると 514 件。着手時の `pytest --collect-only` と AST に対して、全件が表に 1 回だけ現れることを確認した。表の件数は着手時の収集数で、「縮約」は残した代表を指す。

| ファイル / テスト関数 | 収集件数 | 分類 | 理由 | 対応・残す代表 |
| --- | ---: | --- | --- | --- |
| `test_loop_check_options.py::test_check_options_accepts_the_template_and_reports_effective_assignments` | 1 | S | 高: 設定の事前検査が PR・GitHub・run・ロックへ副作用を残して後続処理や他 run を妨げる損害を防ぐ。固定の既定値照合は削除済み。 | 縮約: 既定値の完全一致は外し、正常終了と assert_untouched を残す。 最終名: test_check_options_has_no_external_side_effects。 |
| `test_loop_check_options.py::test_check_options_does_not_accept_fresh_review` | 1 | L | argparse が usage と終了コード 2 で拒否する。 | 消す |
| `test_loop_check_options.py::test_check_options_does_not_touch_herdr` | 1 | L | 誤ったペイン名は Herdr 上で見え、start の warning にも出る。 | 消す |
| `test_loop_check_options.py::test_check_options_reads_the_personal_config_when_not_given` | 1 | L | 設定の不備は start または runner が終了コードと理由を出す。 | 消す |
| `test_loop_check_options.py::test_check_options_rejects_a_codex_reviewer_in_the_personal_config` | 1 | L | 設定の不備は start または runner が終了コードと理由を出す。 | 消す |
| `test_loop_check_options.py::test_check_options_rejects_what_start_rejects_with_the_same_reason` | 10 | L | 無効な設定は start と run_roles が終了コード 2 と具体的な理由で止める。事前検査の副作用は test_check_options_has_no_external_side_effects が確認する。 | 消す: 10 ケースは同じ設定拒否経路。 |
| `test_loop_check_options.py::test_check_options_reports_the_options_start_would_record` | 1 | S | 中: 前検査と start の担当・設定が食い違うと、別の担当で気付かず実行する。 | 残す |
| `test_loop_diagnostics.py::test_all_failed_review_returns_the_diagnostics_to_the_controller` | 2 | S | 中: 全員失敗時に診断の保存先や保存失敗を司令塔へ返さず、残存資源と原因を見失う損害を防ぐ。 | 縮約: id=saved を残す。unsaved は unsaved_diagnostic_keeps_the_output_and_tells_the_controller で代表。 |
| `test_loop_diagnostics.py::test_cause_uses_only_failure_channels` | 16 | S | 中: モデル本文を実際の失敗として分類し、誤った原因を永続診断に保存する損害を防ぐ。 | 縮約: id=tool-output-is-data,error-event,traceback-line-number-is-not-a-status,bracketed-diagnostic を残す。他は同じ出所/優先順位の重複。 |
| `test_loop_diagnostics.py::test_different_failures_leave_distinct_causes_after_cleanup` | 1 | S | 中: ログ回収後に別々の失敗を同じ原因として記録する損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_final_pi_failure_survives_a_long_history` | 3 | S | 中: 長い履歴で最後の失敗を見失い、誤原因を保存する実発生 #237 の再発を防ぐ。 | 縮約: id=history-line-over-1-mib,history-line-over-the-limit を残す。final-message-without-agent-end は同じ末尾イベント。 |
| `test_loop_diagnostics.py::test_keep_diagnostic_covers_only_reviewers_with_a_failure` | 3 | S | 中: 失敗した試行の診断を保存し忘れ、ログ回収後に根拠を失う損害を防ぐ。 | 残す: id=accepted,failed-fallback,rejected を残す。成功の不保存と失敗の保存を対で確認するため。 |
| `test_loop_diagnostics.py::test_large_log_is_read_from_the_tail` | 2 | D | 長いログの末尾確認は final_pi_failure_survives_a_long_history で代表する。 | 消す |
| `test_loop_diagnostics.py::test_logs_are_read_only_when_safe` | 8 | S | 高: sensitive・symlink・出力外・生存中のログを読んで秘密や別ファイルに触れる損害を防ぐ。 | 縮約: case=readable,sensitive,outside_output,symlink,fifo,not_stopped を残す。not_recorded/missing は同じ読み取り拒否の重複。 |
| `test_loop_diagnostics.py::test_model_prose_stdout_never_decides_the_cause` | 8 | S | 中: Devin のコード例やモデル本文を実失敗として扱い、誤原因を保存する損害を防ぐ。 | 縮約: id=devin-fenced-example,devin-stderr,cursor-cli-line,unknown-runtime を残す。ほかは同じ stdout/stderr 境界の重複。 |
| `test_loop_diagnostics.py::test_recovered_failures_do_not_decide_the_cause` | 7 | S | 中: 回復した一時的エラーを最終原因として保存する損害を防ぐ。 | 縮約: id=claude-retry-overloaded,claude-retries-exhausted,pi-retry-recovered,pi-retries-exhausted-without-agent-end を残す。残りは同じ回復/失敗経路。 |
| `test_loop_diagnostics.py::test_reported_failures_are_not_response_extraction` | 4 | S | 中: pi が報告した提供元の失敗を応答抽出失敗と誤記録する損害を防ぐ。 | 縮約: id=failed-message,nothing-reported を残す。agent_end 内の類似例は重複。 |
| `test_loop_diagnostics.py::test_rerun_keeps_a_diagnostic_for_each_request` | 1 | S | 中: 再実行が最初の失敗記録を上書きして調査履歴を失う損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_response_extraction_is_decided_from_the_end_state` | 6 | S | 中: runner や adapter の終了状態と食い違う応答抽出失敗を永続診断に保存し、復旧判断を誤らせる損害を防ぐ。 | 縮約: 応答抽出の正例、adapter 成功、終了コード 1、非ログの `sensitive_paths` を持つ負例を残す。非ログの保持物は独立条件であり、サイクル 1 のレビューで復元した。 |
| `test_loop_diagnostics.py::test_review_reads_stdout_by_the_reviewer_runtime` | 1 | S | 中: レビュアーの runtime を取り違え、失敗の原因を誤記録する損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_secret_in_logs_never_reaches_the_records` | 1 | S | 高: ログ中の秘密情報が永続記録や CLI の JSON 出力へ漏れる損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_unobservable_logs_are_not_response_extraction` | 5 | S | 中: 部分取得のログだけで応答抽出失敗と誤判定し、復旧判断を誤らせる損害を防ぐ。末尾切り出しは通常の読取不能と別条件。 | 縮約: change=partial のみ残す。partial は末尾切り出しに失敗報告が隠れる固有条件。 |
| `test_loop_diagnostics.py::test_unobserved_values_are_listed` | 1 | D | 未観測の原因を unknown とする守りは unobservable_logs_are_not_response_extraction と重複。 | 消す |
| `test_loop_diagnostics.py::test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller` | 1 | S | 高: 診断の保存失敗時に唯一のログを削除し、原因調査不能にする損害を防ぐ。 | 残す |
| `test_loop_herdr_pane.py::test_run_record_without_herdr_pane_still_loads` | 1 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: 対象ケース削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_failure_does_not_call_herdr` | 1 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: 対象ケース削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_renames_the_current_pane_once` | 3 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: 対象ケース削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_skips_herdr_outside_a_pane` | 6 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: 対象ケース削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_succeeds_when_herdr_fails` | 3 | S | 高: Herdr が応答しなくても start が停止し、レビュー作業を進められる。Issue #231 が hang を S と明記。 | 縮約: hang の 1 ケースだけ残す。pane 名と通常失敗の表示は L。 最終名: test_start_succeeds_when_herdr_hangs。 |
| `test_loop_review.py::test_after_run_result_is_reloaded_before_reviewer_validation` | 2 | S | 高: after_run が却下した結果を古い成功値で受け付け、失敗したレビューで計画へ進む損害を防ぐ。 | 縮約: change=payload_failed を残す。payload_unchanged は成功の重複。 |
| `test_loop_review.py::test_cleanup_output_removes_only_its_own_prefix` | 2 | S | 高: 別の出力ディレクトリを削除する損害を防ぐ。 | 残す: own=True/False の両方を残す。拒否と正常回収を対で検査。 |
| `test_loop_review.py::test_cleanup_without_force_keeps_only_a_written_worktree` | 2 | S | 高: レビュアーが書いた worktree の変更を消す損害を防ぐ。 | 残す: write=True/False の両方を残す。 |
| `test_loop_review.py::test_cycle_end_reads_the_roles_json_that_run_roles_writes` | 1 | S | 中: 実際の担当と違う担当を判断の記録に保存する損害を防ぐ。単なる解析失敗部分は L。 | 残す |
| `test_loop_review.py::test_cycle_record_without_the_rerun_fields_loads` | 1 | L | 旧 schema の読み込みが壊れれば Pydantic/解析エラーで明示される。 | 消す |
| `test_loop_review.py::test_failed_cleanup_paths_are_reported` | 1 | S | 中: 回収できなかったパスを報告せず、残存資源を見失う損害を防ぐ。 | 残す |
| `test_loop_review.py::test_interrupted_rerun_is_not_relaunched` | 1 | D | 初回と再実行は同じ _review_batch の中断後再起動拒否を通る。test_interrupted_review_without_result_is_not_rerun が代表。 | 消す |
| `test_loop_review.py::test_interrupted_review_without_result_is_not_rerun` | 1 | S | 高: 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる損害を防ぐ。 | 残す |
| `test_loop_review.py::test_missing_output_checks_fail_closed` | 6 | S | 高: git 登録確認が失敗した状態を空とみなして資源を削除する損害を防ぐ。 | 縮約: entrypoint=audit,failure=git_unavailable を残す。他 5 組合せは同じ失敗時停止の重複。 |
| `test_loop_review.py::test_missing_output_parent_does_not_hide_registered_worktrees` | 4 | S | 高: 親ディレクトリが消えても登録済み worktree を見落としてロックを解放・誤削除する損害を防ぐ。 | 縮約: entrypoint=cleanup,locked=True を残す。audit と unlocked は同じ登録確認の重複。 |
| `test_loop_review.py::test_missing_parent_with_no_registration_is_removed` | 2 | S | 中: 拒否だけの実装で回収が永遠に進まないことを防ぐ正例。 | 縮約: entrypoint=cleanup を残す。audit は同じ正例の重複。 |
| `test_loop_review.py::test_next_commands_never_carry_placeholders_and_recover_rejects_them` | 1 | S | 高: 書きかけの停止確認を事実として受理し、生存プロセスの資源とロックを解放する損害を防ぐ。 | 残す |
| `test_loop_review.py::test_recover_keeps_files_that_may_hold_secrets` | 1 | S | 高: 回収時に秘密情報が残りうる receipt を消し、必要な調査記録を失う損害を防ぐ。 | 残す |
| `test_loop_review.py::test_request_is_kept_only_from_a_regular_file` | 1 | S | 高: 未停止の書き手や symlink をたどって別のファイルを読み取り、保存対象を誤る損害を防ぐ。 | 残す: symlink/missing/not-stopped の拒否と通常ファイルの受理を残す。 |
| `test_loop_review.py::test_rerun_is_not_started_while_another_attempt_is_unconfirmed` | 1 | S | 高: 未停止の試行と同時に再実行し、同じ成果や資源へ競合書き込みする損害を防ぐ。 | 残す |
| `test_loop_review.py::test_rerun_refuses_when_the_head_moved` | 1 | D | 初回と再実行は review の同じ HEAD 照合を通る。test_review_refuses_when_the_head_moved_after_cycle_begin が代表。 | 消す |
| `test_loop_review.py::test_rerun_that_fails_again_continues_with_the_accepted_reviewers` | 1 | D | 部分失敗を rejected として扱う守りは review_records_partial_failure_and_cleans_owned_worktrees が代表する。 | 消す |
| `test_loop_review.py::test_resume_after_review_continues_from_status` | 1 | S | 高: 再開時にレビューの保存結果を無視して段階を飛ばす損害を防ぐ。 | 残す |
| `test_loop_review.py::test_reuse_counts_only_pairs_for_the_current_head` | 1 | S | 高: 古い HEAD のレビューを現 HEAD に流用して未検証の変更をマージする損害を防ぐ。 | 残す |
| `test_loop_review.py::test_review_after_an_interrupted_after_run_holds_the_run` | 1 | S | 高: 中断した after_run を再起動し、既存の子プロセスや出力と競合する損害を防ぐ。 | 残す |
| `test_loop_review.py::test_review_executes_after_run_against_saved_result` | 1 | S | 高: 設定された後処理を省き、検査を経ない runner 成果を成功として使う損害を防ぐ。 | 残す |
| `test_loop_review.py::test_review_records_partial_failure_and_cleans_owned_worktrees` | 1 | S | 高: 失敗したレビュアーを指摘なしとして扱う、または所有 worktree を残す・誤削除する損害を防ぐ。 | 残す |
| `test_loop_review.py::test_review_refuses_when_the_head_moved_after_cycle_begin` | 1 | S | 高: 古い HEAD のレビューを現 HEAD に流用して未検証の変更をマージする損害を防ぐ。 | 残す |
| `test_loop_review.py::test_review_stops_before_creating_output_when_the_checkout_cannot_be_resolved` | 1 | L | checkout resolver が理由付きで止まり、異常な出力や再試行失敗も明示される。 | 消す |
| `test_loop_review.py::test_review_with_no_accepted_reviewer_fails_with_code_6` | 1 | S | 高: 受理したレビューが 0 件でも計画へ進む損害を防ぐ。 | 残す |
| `test_loop_review.py::test_reviewer_rejected_after_runner_success_is_rerun_once` | 1 | S | 中: 保存に失敗した担当を未実施のまま指摘なし扱いにする損害を防ぐ。 | 残す |
| `test_loop_review.py::test_reviewers_receive_the_previous_round_when_the_head_moved` | 1 | S | 中: 前回の判断履歴をレビュアーへ渡さず、同じ指摘を取り違える損害を防ぐ。 | 残す |
| `test_loop_review.py::test_runner_level_failure_is_not_rerun` | 1 | L | runner の失敗と再起動は状態・ログ・起動回数に明示される。 | 消す |
| `test_loop_review.py::test_runner_refusing_before_launch_can_be_retried` | 1 | L | 起動前の runner 拒否は code 5 と理由が表示される。 | 消す |
| `test_loop_review.py::test_status_after_every_reviewer_failed_points_to_abort` | 1 | D | 全レビュアー失敗時の停止は review_with_no_accepted_reviewer_fails_with_code_6 が代表する。 | 消す |
| `test_loop_review.py::test_two_cycles_reuse_the_pre_push_review_and_end_merged` | 1 | D | HEAD 移動は test_review_refuses_when_the_head_moved_after_cycle_begin、前回レビュー採用は test_reuse_counts_only_pairs_for_the_current_head、マージ状態は test_finalize_stopped_keeps_the_real_merge、ロック解放は test_finish_releases_only_its_own_lock に分けて確認する。 | 消す |
| `test_loop_review.py::test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms` | 4 | S | 高: 生存中かもしれない after_run の出力を消し、ロックを解放する損害を防ぐ。 | 縮約: entry=recover,case=unconfirmed を残す。interrupted は次の専用テスト、finish_abort は同じ資源ガード。 |
| `test_loop_review.py::test_unconfirmed_attempt_holds_the_run_instead_of_planning` | 3 | S | 高: レビュアーの停止を確認しないまま計画を始め、資源を消す損害を防ぐ。 | 縮約: id=first-alpha,rerun-beta を残す。first-beta は担当を替えただけの重複。 |
| `test_loop_review.py::test_unconfirmed_stop_holds_the_lock_until_operator_recovery` | 1 | S | 高: 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる損害を防ぐ。 | 残す |
| `test_loop_review.py::test_verify_reviewer_accepts_a_complete_payload_and_records_hashes` | 1 | S | 中: 正しい成果も拒否する実装や、採用した成果のハッシュ・担当を誤記録する損害を防ぐ。拒否テストの正例。 | 残す |
| `test_loop_review.py::test_verify_reviewer_rejects_artifacts_that_do_not_belong_to_this_head` | 3 | S | 高: payload は正しくても本文や候補一覧が別 PR・HEAD の場合に採用する損害を防ぐ。 | 縮約: case=other_pr_document,stale_body を残す。symlink_inside_dir は verify_reviewer_rejects_each_broken_condition の review_symlink で代表。 |
| `test_loop_review.py::test_verify_reviewer_rejects_each_broken_condition` | 12 | S | 高: runner が失敗しても正常な payload・成果だけで受理する、または別 run・担当・PR・HEAD の成果、未停止の担当、改ざんされた成果を受け付けて計画・マージへ進む損害を防ぐ。 | 縮約: case=outer_failed,stop_unconfirmed,payload_failed,request_mismatch,actual_agent_mismatch,other_pr,reviewed_head_mismatch,review_outside_dir,review_symlink,pair_mismatch,active_count_mismatch を残す。outer_failed は外側の Result.state だけが timed_out の独立条件。findings_invalid は後段の明示エラー。 |
| `test_loop_review.py::test_write_exceptions_name_the_target_checkout_git` | 1 | S | 高: runner に別 checkout の Git 書き込み権限を渡す損害を防ぐ。 | 残す |
| `test_loop_reviewer_protocol.py::test_literal_reviewer_completes_the_real_helper_within_the_declared_exceptions` | 1 | S | 高: read-only runner の書き込み範囲が広がる、または別 PR・HEAD の成果が混入する損害を実 helper 経路で検出する。 | 残す |
| `test_loop_state.py::test_a_differently_cased_pr_url_shares_the_lock` | 1 | S | 高: URL の大文字小文字違いで同じ PR に二重ロックを作り、同時書き込みする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_a_failed_lock_write_leaves_no_lock` | 1 | L | ロック書込が失敗して残留しても、次の start は lock_held と所有者を明示して止まる。成功・競合の守りは test_second_start_is_refused_while_the_first_run_holds_the_lock と test_finish_releases_only_its_own_lock が確認する。 | 消す |
| `test_loop_state.py::test_abort_after_a_finalize_merge_keeps_the_merge` | 2 | S | 高: finalize 後に cycle-end が停止しても、abort でマージ済みを false と記録する損害を防ぐ。 | 縮約: id=pr-unreadable を残す。pr-read は abort_records_the_merge_state_it_observed と重複。 |
| `test_loop_state.py::test_abort_needs_a_classified_reason` | 1 | L | 理由の書式違反は finish が引数エラーとして明示する。 | 消す |
| `test_loop_state.py::test_abort_records_the_merge_state_it_observed` | 10 | S | 高: PR の実状態、finalize の最後の観測、未確認 null を混同してマージ状態を誤報告する損害を防ぐ。 | 縮約: open・finalize 不在で false、merged・finalize false で true、PR 不可読で null、open・finalize true で null を残す。false と null の区別は独立条件としてサイクル 1 で復元した。 |
| `test_loop_state.py::test_abort_treats_a_gh_that_cannot_start_as_unreadable` | 1 | D | PR が読めないときの finalize fallback は abort_after_a_finalize_merge_keeps_the_merge の pr-unreadable で代表する。 | 消す |
| `test_loop_state.py::test_cli_finish_abort_passes_the_finalize_result` | 1 | S | 高: CLI が `--finalize-result` を実処理へ渡さないと、PR 不可読時に観測済みマージを null と記録する。API の直接呼出しでは CLI 境界を守れない。 | 残す。サイクル 1 で復元し、CLI の転送だけを壊すと失敗することを確認した。 |
| `test_loop_state.py::test_cli_start_reports_a_refused_fix_assignment` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_cycle_end_accepts_a_spec_commit_merge` | 1 | S | 高: 検証 HEAD の上に Spec commit を載せた PR のマージを、別 commit と誤照合する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_before_the_record_is_posted_keeps_the_cycle_open` | 1 | S | 高: レビューや判断記録の前にサイクルを完了し、未検証の PR を成功扱いする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_reads_the_authenticated_users_record` | 1 | S | 高: 他人のコメントを認証済み利用者の判断として採用する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_rejects_a_malformed_spec_commit` | 4 | L | 不正 SHA は finalize 結果の解析または HEAD 照合の明示エラーになる。 | 消す |
| `test_loop_state.py::test_cycle_limit_ends_with_fixes_pushed` | 1 | S | 高: サイクル上限後に追加レビューなしで次へ進み、未検証のままマージする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped` | 1 | S | 高: 未マージまたは別 HEAD のマージを検証済みとして完了報告する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result` | 1 | S | 高: 不正な finalize 結果で run を上書きし、マージ状態を誤記録する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_stopped_ends_the_run_as_stopped_and_not_merged` | 1 | S | 高: finalize の停止をマージ成功として報告する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_stopped_keeps_the_real_merge` | 4 | S | 高: finalize が停止しても、実際のマージを未マージとして誤報告する損害を防ぐ。 | 縮約: finalize の false・PR の別 HEAD の true、finalize の null・PR の true、merge parent 不一致での true を残す。false と null の優先順位は独立条件としてサイクル 1 で復元した。 |
| `test_loop_state.py::test_finish_releases_only_its_own_lock` | 1 | S | 高: 同じ PR の同時書き込み、または別 run のロック解放による競合を防ぐ。 | 残す |
| `test_loop_state.py::test_fixes_pushed_requires_the_pr_head_to_be_the_pushed_commit` | 1 | S | 高: 別 HEAD の判断や push を現サイクルのものとして採用する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_inherited_skip_changed_without_evidence_is_rejected` | 1 | S | 中: 引き継いだ判断を根拠なしに変更し、判断履歴を誤記録する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_no_fix_needed_needs_a_merged_finalize_result_at_the_same_head` | 1 | S | 高: 未マージまたは別 HEAD のマージを検証済みとして完了報告する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_out_of_order_calls_are_refused` | 1 | S | 高: レビューや判断記録の前にサイクルを完了し、未検証の PR を成功扱いする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_record_for_another_head_is_not_taken_as_this_cycle` | 1 | S | 高: 別 HEAD の判断や push を現サイクルのものとして採用する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_record_from_an_earlier_run_for_the_same_head_is_not_taken` | 1 | S | 高: 同じ HEAD の古い run の判断を新 run の判断として流用する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_recorded_stop_keeps_a_manual_merge` | 1 | D | 実際の PR のマージ状態を優先する守りは finalize_stopped_keeps_the_real_merge で代表する。 | 消す |
| `test_loop_state.py::test_records_need_the_authenticated_login` | 3 | S | 高: login を得られないまま投稿者の絞り込みを緩め、他人の判断記録を採用する損害を防ぐ。 | 縮約: id=blank を残す。gh-failed/empty は同じ認証境界の重複。 |
| `test_loop_state.py::test_second_start_is_refused_while_the_first_run_holds_the_lock` | 1 | S | 高: 同じ PR の同時書き込み、または別 run のロック解放による競合を防ぐ。 | 残す |
| `test_loop_state.py::test_start_accepts_fix_assignments_that_run_roles_accepts` | 3 | S | 中: 有効な設定を誤った担当に置き換えて起動する損害を防ぐ。 | 縮約: default と implement-codex を残す。external-review-roles は同じ割当保存の重複。 |
| `test_loop_state.py::test_start_records_options_and_effective_assignments` | 2 | S | 中: CLI が担当指定を渡さず、run.json と計画に別の担当を記録する損害を防ぐ。 | 縮約: CLI 入口の 1 件を残し、API の直接呼出しとの重複を作らない。サイクル 1 で入口を変更し、転送だけを壊すと失敗することを確認した。 |
| `test_loop_state.py::test_start_refuses_a_closed_pr` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_refuses_a_pr_whose_checkout_cannot_be_resolved` | 1 | L | checkout 不明は対象 resolver またはレビュアーが理由付きエラーで停止する。 | 消す |
| `test_loop_state.py::test_start_rejects_a_codex_reviewer` | 3 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_rejects_an_unknown_role_and_inspect_self` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_rejects_fix_assignments_that_run_roles_refuses` | 6 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_status_returns_the_next_command_after_a_restart` | 1 | S | 高: 再開時に誤った段階へ進み、レビューや判断を飛ばす損害を防ぐ。 | 残す |
| `test_loop_state.py::test_stopped_record_ends_the_run_and_finish_releases_the_lock` | 1 | D | 停止結果の保存は test_abort_records_the_merge_state_it_observed、ロック解放は test_finish_releases_only_its_own_lock が代表。 | 消す |
| `test_pr_review_fix_loop_skill_contract.py::test_loop_skill_runs_only_when_explicitly_invoked` | 1 | F∩S | 高: disable-model-invocation の権限境界が外れると、明示依頼なしに push・マージまで進む。 | 残す |
| `test_port_routing.py::test_explicit_commit_has_separate_pair_and_validates_worktree_head` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_port_routing.py::test_external_checkout_requires_explicit_source_and_matching_remote` | 1 | S | 防ぐ損害（高）: 他の Git や利用者所有ファイルを対象として操作・削除する。 | 残す |
| `test_port_routing.py::test_failed_shallow_create_can_be_inspected_then_abandoned` | 1 | S | 防ぐ損害（中）: 失敗後の所有セッションと回収手掛かりを失う。 | 残す |
| `test_port_routing.py::test_fork_and_upstream_same_number_are_independent` | 1 | D | 同番号の fork/upstream を別の保存先にする守りは test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently が保存内容と片方だけの再レビューまで検証する。version 8 の target 経由の pair 保存先・共有 ref は test_upstream_full_diff_pair_save_cleanup_preserves_shared_refs が受け持つ。repository-qualified path の生成は両入口で同じ review_artifact_paths / findings_artifact_paths を使う。 | 消す |
| `test_port_routing.py::test_moving_live_head_keeps_drafts_then_fresh_session_continues` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_port_routing.py::test_ref_delete_failure_keeps_a_retryable_session` | 1 | S | 防ぐ損害（中）: 失敗後の所有セッションと回収手掛かりを失う。 | 残す |
| `test_port_routing.py::test_shallow_recovery_refuses_unowned_git_or_user_data` | 9 | S | 防ぐ損害（高）: 他の Git や利用者所有ファイルを対象として操作・削除する。 | 縮約: replacement のみ削除。journal-owner と同じ repo inode の条件を通る D。journal-kind/worktree/parent、git-replacement は別条件なので保持。 |
| `test_port_routing.py::test_target_rejects_unvalidated_input_without_creating_session` | 7 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 縮約: remote, sha, number, url, repository。bool の PR number は識別取り違えを防ぐ独立条件なので保持。 |
| `test_port_routing.py::test_upstream_full_diff_pair_save_cleanup_preserves_shared_refs` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_pr_review_workspace.py::test_a_repeated_signal_does_not_cut_the_end_record` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_clears_records_left_by_an_interrupted_worktree_add` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: HEAD。ほかの破損形は同じ管理レコード回収の D。 |
| `test_pr_review_workspace.py::test_abandon_keeps_a_journal_without_pr_repository` | 1 | S | 防ぐ損害（高）: 所属 PR が分からない旧 journal の session を推測して削除しない。 | 残す |
| `test_pr_review_workspace.py::test_abandon_keeps_a_session_with_files_it_did_not_create` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: notes.txt と review-backup/opus-5.md。nested/ は同じ利用者所有 entry の D。 |
| `test_pr_review_workspace.py::test_abandon_keeps_a_worktree_locked_for_another_reason` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_another_repository` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_records_of_another_worktree` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_while_the_attempt_is_running` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_removes_a_worktree_left_initializing` | 1 | L | initializing lock のある正しい owned worktree を git worktree remove --force --force で回収できる正常受理。二重 --force が欠けると git が lock を理由に非 0 で失敗し、誤削除や成功の誤報告は残らない。利用者が付けた別理由の lock は test_abandon_keeps_a_worktree_locked_for_another_reason が保持し、creator 生存の拒否は test_abandon_refuses_while_the_attempt_is_running が代表する。 | 消す |
| `test_pr_review_workspace.py::test_abandon_touches_only_its_own_attempt` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_waits_for_a_checkout_that_outlives_create` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_waits_for_the_repository_review_lock` | 1 | S | abandon 自身の review_save_lock が削除競合を防ぐ。save/cleanup の lock とは別の入口。 | 残す |
| `test_pr_review_workspace.py::test_atomic_copy_replaces_internal_destination_symlink_entry` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_fails_closed_when_rerun` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_cleanup_keeps_other_worktrees_and_main_checkout` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_keeps_v7_session_when_saved_candidates_are_missing` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_parser_rejects_caller_selected_paths` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_cleanup_refuses_before_save` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_refuses_when_destination_diverges_from_draft` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_refuses_when_session_path_is_not_its_worktree` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_refuses_worktree_of_another_repository` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_removes_session_after_successful_save` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_cleanup_removes_worktree_holding_verification_artifacts` | 1 | L | 保存済み review worktree の編集・untracked build がある場合にも git worktree remove --force が通る正常受理。--force が失われると git が明示的非 0 で失敗し、後段の worktree.exists 確認も失敗を報告する。削除対象の所有権と他 worktree の保持は test_cleanup_refuses_when_session_path_is_not_its_worktree / test_cleanup_refuses_worktree_of_another_repository / test_cleanup_keeps_other_worktrees_and_main_checkout に残す。 | 消す |
| `test_pr_review_workspace.py::test_cleanup_waits_for_repository_review_lock` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_create_destination_replaces_unsafe_directory_characters` | 7 | D | 文字ごとの置換は normalize_head_branch の同じ _UNSAFE_DIRECTORY_CHARS.sub を通る組合せで、slash を含む正常 branch は test_create_pins_model_and_artifact_paths が代表。別処理である rstrip と正規化後の空名拒否は test_review_artifact_paths_reject_invalid_branch[...] が代表として残り、先頭 / の拒否も同じ関数に残す。 | 消す |
| `test_pr_review_workspace.py::test_create_destination_uses_hash_pr_number_and_sanitized_branch` | 1 | D | #<PR番号>-<slash を置換した branch> と model の保存先を test_create_pins_model_and_artifact_paths が同じ review_directory_name / review_artifact_paths 経由で検証する。explicit model の正常経路も test_create_pins_explicit_model_outside_codex に残る。 | 消す |
| `test_pr_review_workspace.py::test_create_does_not_fsync_session_files` | 1 | L | 気付ける経路: 長いロック待ち・処理時間として通常利用時に明白になる。 | 消す |
| `test_pr_review_workspace.py::test_create_normalizes_pr_repository_case` | 1 | 迷い | 旧 create API の caller はリポジトリ内で見つからないが、互換記述があり外部 caller を否定できない。削除判断を保留。 | 残す |
| `test_pr_review_workspace.py::test_create_outlives_a_reader_that_closed_its_stderr` | 1 | L | 気付ける経路: BrokenPipeError と非 0 終了で helper が停止する。 | 消す |
| `test_pr_review_workspace.py::test_create_parser_accepts_explicit_model_name` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_create_parser_requires_attempt_id` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_create_pins_existing_review_snapshot` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_explicit_model_outside_codex` | 1 | 迷い | 旧 create API の caller はリポジトリ内で見つからないが、互換記述があり外部 caller を否定できない。削除判断を保留。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_model_and_artifact_paths` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_slash_model_name_as_hyphenated_filename` | 1 | L | create が受け取る provider/model の slash 置換は受理する表記の互換性。置換が行われないと validate_model_name の _MODEL_FILENAME.fullmatch が safe filename の WorkspaceError で停止し、保存されず通常利用で分かる。ファイル名の境界とモデル上書きの拒否は test_resolve_runtime_model_name_fails_closed_outside_codex / test_resolve_runtime_model_name_rejects_codex_override に残す。 | 消す |
| `test_pr_review_workspace.py::test_create_records_its_phases_in_the_journal` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す: 固定の phase 名・順序の写しは F。残す場合は中断時の所有情報と回収判断に効く項目に絞る。 |
| `test_pr_review_workspace.py::test_create_rejects_invalid_pr_repository` | 8 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: ../resoloop と usaturn/..。owner の文法と repo 名が .. の拒否は別条件。 |
| `test_pr_review_workspace.py::test_create_rejects_reused_attempt_id` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_create_rejects_unsafe_attempt_id` | 5 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: ../escape。その他の文字列変種は同じ範囲検査の D/L。 |
| `test_pr_review_workspace.py::test_create_reports_legacy_review_without_adopting_it` | 1 | S | 防ぐ損害（中）: 旧配置のレビューを別リポジトリの前回結果として黙って採用・移動しない。互換 API は残す。 | 残す |
| `test_pr_review_workspace.py::test_create_requires_explicit_model_outside_codex` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_pr_review_workspace.py::test_create_returns_the_pinned_findings_draft` | 1 | D | findings_draft の返却パスは test_save_with_findings_saves_the_review_and_the_candidates の write_findings_pair が実際に書き、その draft と正式候補の bytes が一致するまで検証する。別の場所を返すと save は別途 findings_artifact_paths で導いた draft を発見できず、正常 pair 保存の代表が失敗する。 | 消す |
| `test_pr_review_workspace.py::test_destination_fingerprint_distinguishes_symlink_entries` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_findings_destination_must_stay_under_the_review_findings_directory` | 5 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す: 5 case 全保持。正規化・findings 名・拡張子・reviews root・別 repo の拒否はそれぞれ書込先の独立条件。 |
| `test_pr_review_workspace.py::test_findings_draft_cannot_escape_the_session_via_symlink` | 1 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す |
| `test_pr_review_workspace.py::test_findings_paths_require_repository_identity` | 2 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す: paths と destination を保持。生成側と安全な保存先判定側が repository 必須条件を別々に持つ。 |
| `test_pr_review_workspace.py::test_first_session_wins_same_destination` | 1 | S | 防ぐ損害（高）: 後から始めたセッションが先に保存したレビューを無断で上書きしない。#231 が明示する優先の守り。 | 残す |
| `test_pr_review_workspace.py::test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently` | 1 | S | fork/upstream の保存先と前回レビュー選択を分離する。port の二件保存だけのテストを D として削除し、この保存・再レビューの代表を残す。 | 残す |
| `test_pr_review_workspace.py::test_inspect_and_abandon_refuse_another_pr_repository` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_inspect_ignores_a_cut_off_journal_line` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_inspect_refuses_an_attempt_id_shared_by_two_sessions` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_inspect_reports_a_completed_attempt` | 1 | D | attempt_report の終端判定は completed 専用分岐でなく TERMINAL_PHASES への membership。終端の status/last_phase は test_terminated_create_records_the_signal、非終端・未停止と worktree の残存情報は test_killed_create_reports_its_last_phase_and_leftovers が代表。completed journal の生成は test_create_records_its_phases_in_the_journal、完成済み session の inspect entries 読取は test_legacy_inspect_reports_but_abandon_preserves_an_unowned_repo_directory が代表。返却した補助パスを破壊的な操作の許可には使わず、abandon は固定した session/worktree を別途検証する。 | 消す |
| `test_pr_review_workspace.py::test_inspect_reports_an_unknown_attempt_as_absent` | 1 | D | 未知の attempt に対する absent と session_dir=None の経路は test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock が、回収後の inspect absent と abandon 拒否で代表する。候補を取り違える危険は test_inspect_refuses_an_attempt_id_shared_by_two_sessions が拒否する。legacy ディレクトリの fixture は read-only の inspect にしか渡さず、削除経路の追加条件ではない。 | 消す |
| `test_pr_review_workspace.py::test_killed_create_reports_its_last_phase_and_leftovers` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_legacy_inspect_reports_but_abandon_preserves_an_unowned_repo_directory` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_load_state_rejects_non_canonical_pr_repository` | 5 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: 代表: Usaturn/resoloop, missing。型違いは同じ検証の D。 |
| `test_pr_review_workspace.py::test_load_state_rejects_previous_version` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_load_state_rejects_tampered_previous_review` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_fails_closed` | 6 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: 代表: unsafe-model, non-unique-rollout, invalid-json。missing-thread/rollout/context は明示エラー L。 |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_ignores_unterminated_partial_tail` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_rejects_malformed_completed_record` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_replaces_slash_with_hyphen` | 1 | L | Codex model 内の slash 置換は受理する表記の互換性。置換が行われないと validate_model_name の _MODEL_FILENAME.fullmatch が safe filename の WorkspaceError で停止し、保存されず通常利用で分かる。ファイル名の境界とモデル上書きの拒否は test_resolve_runtime_model_name_fails_closed_outside_codex / test_resolve_runtime_model_name_rejects_codex_override に残す。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_replaces_whitespace_with_hyphen` | 1 | L | Codex model 内の空白置換は受理する表記の互換性。置換が行われないと validate_model_name の _MODEL_FILENAME.fullmatch が safe filename の WorkspaceError で停止し、保存されず通常利用で分かる。ファイル名の境界とモデル上書きの拒否は test_resolve_runtime_model_name_fails_closed_outside_codex / test_resolve_runtime_model_name_rejects_codex_override に残す。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_skips_records_outside_expected_schema` | 5 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_uses_latest_turn_context` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_accepts_slash_equivalent_explicit_in_codex` | 1 | L | Codex の正規化済み runtime model と、それと同じ明示名の正常受理。等価名を誤って拒否すると explicit model does not match の WorkspaceError で通常実行が止まる。異なる runtime model を採用する危険の拒否は test_resolve_runtime_model_name_rejects_codex_override に残っている。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_fails_closed_outside_codex` | 5 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: ../evil と先頭空白 Composer を保持。先頭空白が黙って - へ変換され別保存先になることを防ぐ条件は regex とは別。 |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_rejects_codex_override` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_replaces_slash_with_hyphen` | 1 | L | 明示 model 内の slash 置換は受理する表記の互換性。置換が行われないと validate_model_name の _MODEL_FILENAME.fullmatch が safe filename の WorkspaceError で停止し、保存されず通常利用で分かる。ファイル名の境界とモデル上書きの拒否は test_resolve_runtime_model_name_fails_closed_outside_codex / test_resolve_runtime_model_name_rejects_codex_override に残す。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_replaces_whitespace_with_hyphen` | 1 | L | 明示 model 内の空白置換は受理する表記の互換性。置換が行われないと validate_model_name の _MODEL_FILENAME.fullmatch が safe filename の WorkspaceError で停止し、保存されず通常利用で分かる。ファイル名の境界とモデル上書きの拒否は test_resolve_runtime_model_name_fails_closed_outside_codex / test_resolve_runtime_model_name_rejects_codex_override に残す。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_uses_explicit_name_outside_codex` | 1 | D | resolve_runtime_model_name の正常な explicit 分岐を create 経由で通り、同じ opus-5 と model_source=explicit を返却値と state の両方で確認する test_create_pins_explicit_model_outside_codex に統合できる。 | 消す |
| `test_pr_review_workspace.py::test_review_artifact_paths_preserve_exact_model_name` | 1 | D | 同じ fix/herdr-session-cwd、PR #4、gpt-5.6-sol の draft 名と repository-qualified destination を test_create_pins_model_and_artifact_paths が create の返却値と state の整合まで検証する。 | 消す |
| `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_branch` | 5 | S | 先頭 / の拒否と、正規化後に空になる branch の拒否は別の条件。誤った branch の保存先を生成させない代表を残す。 | 縮約 |
| `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_pr_number` | 4 | S | PR number の型と正数の条件に代表が無かったため bool True と 0 を残す。誤った PR の保存先を生成しない。 | 縮約 |
| `test_pr_review_workspace.py::test_safe_destination_rejects_symlink_escape` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_save_allows_another_review_destination_to_change` | 1 | S | 防ぐ損害（中）: 自分の保存先以外の変化で作業全体を誤って拒否しない正例。 | 残す |
| `test_pr_review_workspace.py::test_save_allows_unrelated_main_changes` | 1 | L | 保存対象外の README と scratch を変えても save が通る正常受理の検査。誤って checkout 全体の差分を拒否するようになると save が WorkspaceError で止まり、通常利用で分かる。この削除テスト自体には README や scratch の内容を保持した assert がなく、利用者の変更消失を守る検査ではない。利用者の状態保持は test_cleanup_keeps_other_worktrees_and_main_checkout / test_abandon_touches_only_its_own_attempt / test_prepare_preserves_shared_refs_and_other_worktree_base_refs に残す。 | 消す |
| `test_pr_review_workspace.py::test_save_allows_untracked_reviews_directory_to_appear` | 1 | D | snapshot の reviews 除外と、保存対象だけを destination_fingerprint で追う守りの正常例。test_save_allows_another_review_destination_to_change も create 後に別 model の untracked gemini レビューを作って保存に成功し、別 model の本文を保つことを検証する。reviews ディレクトリ自体が未追跡かどうかは同じ reviews 除外の組合せ。 | 消す |
| `test_pr_review_workspace.py::test_save_parser_rejects_caller_selected_paths` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_save_parser_takes_findings_as_a_flag_without_a_path` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_save_rejects_changed_pinned_destination` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_rejects_changed_runtime_model` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_rejects_non_directory_destination_parent` | 2 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_save_rejects_rewritten_pr_repository` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_rejects_tampered_destination` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_rejects_unknown_model_source` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_uses_only_pinned_paths` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_uses_pinned_explicit_model_without_codex_metadata` | 1 | 迷い | 旧 create API の caller はリポジトリ内で見つからないが、互換記述があり外部 caller を否定できない。削除判断を保留。 | 残す |
| `test_pr_review_workspace.py::test_save_waits_for_repository_review_lock` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_save_with_findings_removes_new_candidates_when_the_review_copy_fails` | 1 | S | 候補が未作成だった場合の unlink による rollback。既存候補の write_bytes による復元とは別の分岐。 | 残す |
| `test_pr_review_workspace.py::test_save_with_findings_requires_the_draft` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_pr_review_workspace.py::test_save_with_findings_restores_the_candidates_when_the_review_copy_fails` | 1 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_with_findings_saves_the_review_and_the_candidates` | 1 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す |
| `test_pr_review_workspace.py::test_save_with_invalid_findings_saves_nothing` | 6 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 縮約: 代表: _move_head, _other_pr, _other_review_file, _extra_finding, _markdown_source。_break_property は schema 検査の明示エラー L。 |
| `test_pr_review_workspace.py::test_save_without_findings_removes_the_stale_candidates_of_the_same_head` | 1 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す |
| `test_pr_review_workspace.py::test_sessions_keep_a_locked_worktree` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_sessions_keep_a_session_without_state` | 2 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_sessions_keep_a_version6_session` | 1 | F∩S | 防ぐ損害（高）: 旧 state の repository 不明を無視すると、別 PR の worktree を削除・レビューを上書きする。 | 残す |
| `test_pr_review_workspace.py::test_sessions_keep_the_open_pr_when_fork_and_upstream_share_number_branch_and_head` | 3 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 縮約: 代表: fork=MERGED, upstream=OPEN。逆向きと CLOSED は同じ repo 別照会の D。 |
| `test_pr_review_workspace.py::test_sessions_keep_when_gh_fails` | 2 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_sessions_keep_when_gh_reports_another_number` | 1 | S | 防ぐ損害（高）: gh が別番号の PR を返してもその状態で session を削除可能と誤判定しない。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_does_not_refresh_index` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_copies_regular_file` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_rejects_non_regular` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_rejects_source_race` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_reports_missing` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_pr_review_workspace.py::test_snapshot_preserves_existing_index_lock` | 1 | S | 防ぐ損害（高）: レビューの snapshot が利用者の index.lock を変更・削除しない。#231 が明示する Git の守り。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_reports_changes_excluding_reviews` | 4 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_terminated_create_records_the_signal` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_version6_session_is_kept_by_verify_save_and_cleanup` | 1 | F∩S | 防ぐ損害（高）: 旧 state の repository 不明を無視すると、別 PR の worktree を削除・レビューを上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_marks_a_timed_out_attempt_on_the_started_record` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_rejects_an_invalid_result_file` | 1 | L | 気付ける経路: Pydantic の result 検証が失敗し、非 0 終了を返す。 | 消す |
| `test_review_run.py::test_attach_runner_rejects_conflicting_values_without_writing` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_reports_attempts_without_a_record` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_skips_files_outside_the_record_layout` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_attach_runner_writes_the_runner_block_once_and_keeps_provenance` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_cleanup_failure_records_cleanup_with_saved_outputs` | 1 | D | 同じ cleanup failure の setup を持つ test_complete_reports_saved_but_uncleaned_result_as_failure に、削除テストの record.status/failed_at/reason と保存済み review digest の assert を移している。結果の failed、保存済み pair、保持した session と実行記録を一回の setup でまとめて検査する。 | 消す: cleanup failure の代表 test_complete_reports_saved_but_uncleaned_result_as_failure へ記録の status/failed_at/reason と出力 digest の assert を統合。 |
| `test_review_run.py::test_complete_preserves_failure_as_failed_result` | 9 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 縮約: binding, reviewer, coverage, destination, head。reviewer immutable 条件は request binding と別なので保持。 |
| `test_review_run.py::test_complete_refuses_skill_changed_after_prepare` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_complete_rejects_changed_draft_before_writing_anywhere` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_complete_reports_saved_but_uncleaned_result_as_failure` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_complete_returns_actual_compare_and_delete_outcome` | 3 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す: deleted・missing・repinned の3結果を全て保持。missing は current is None の独立条件であり、既に無い ref を repinned や deleted ともっともらしく誤報告することを防ぐ。レビュー Important 1 で D 判断を訂正し、ref を事前削除する setup も復元。 |
| `test_review_run.py::test_complete_saves_zero_findings_with_provenance` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_fail_request_returns_without_blocking_and_preserves_failure_record` | 12 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 縮約: 代表: state_kind=prepared × kind=regular/fifo。ほかは同じ記録保護の D、FIFO の待ちは timeout で分かる L。 |
| `test_review_run.py::test_helper_write_exceptions_grant_git_data_only_where_the_helper_writes_it` | 4 | F∩S | 防ぐ損害（高）: 固定した書込許可範囲を広げると、writes=false の担当が利用者 Git を変更できる。 | 残す: 4 組合せを維持。親/別 checkout と shallow/通常で許可すべき Git 書込先が実際に異なる。 |
| `test_review_run.py::test_model_fail_records_review` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_ordinary_depth_one_checkout_reviews_whole_pr_without_shared_history_changes` | 3 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 縮約: 代表: head, unpushed。explicit は同じ完全差分取得の D。 |
| `test_review_run.py::test_other_runtime_request_path_acceptance_is_unchanged` | 2 | L | relative request path と同じ実体を指す symlink の受理。read_request が受理しなくなると prepare が例外または failed の非 0 で止まり、通常利用で分かる。同じファイルを複数パスで検査する組合せでもある。別 work_dir や shape の入力を誤採用する危険は test_prepare_rejects_wrong_request_workdir_and_shape、入力改変は test_complete_preserves_failure_as_failed_result[binding] に残す。 | 消す |
| `test_review_run.py::test_payloads_without_a_record_still_name_the_run_record_key` | 1 | L | 気付ける経路: 呼び出し側が欠落キーを解析すると例外になる。 | 消す |
| `test_review_run.py::test_prepare_alone_leaves_started_record_like_a_killed_run` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_base_fetch_failure_returns_correlated_retained_paths` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_binds_request_and_local_records` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_create_failure_reports_owned_session_retained_paths` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_fails_without_observed_model` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_review_run.py::test_prepare_failure_after_base_fetch_keeps_shared_refs_unchanged` | 1 | S | base fetch の後、merge-base が失敗する経路でも共有 ref を変えない。成功経路の代表と失敗後の守りは区別する。 | 残す |
| `test_review_run.py::test_prepare_failure_after_resolve_records_prepare` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_failure_before_resolve_writes_no_record` | 1 | S | model が不明で observed_model が resolve より前に失敗する際、実行記録を作らない副作用境界。失敗の WorkspaceError 自体が明白でも、ghost の started 記録が残れば損害は通常利用で分からない。test_prepare_refuses_external_pr_without_explicit_checkout の no-record は後段 resolve の失敗なので、この失敗段階の代表にはならず元関数を復元する。 | 残す: model が不明で observed_model が resolve より前に失敗する際、実行記録を作らない副作用境界。失敗の WorkspaceError 自体が明白でも、ghost の started 記録が残れば損害は通常利用で分からない。test_prepare_refuses_external_pr_without_explicit_checkout の no-record は後段 resolve の失敗なので、この失敗段階の代表にはならず元関数を復元する。 |
| `test_review_run.py::test_prepare_failure_is_kept_when_the_model_later_calls_fail` | 1 | S | prepare で記録済みの失敗原因・段階を、後続 fail が上書きすることを防ぐ。 | 残す |
| `test_review_run.py::test_prepare_nonrunner_marks_unobserved_identity_unknown` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_parallel_sessions_pin_their_own_base` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_pi_requires_both_current_environment_identifiers` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_preserves_shared_refs_and_other_worktree_base_refs` | 10 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 縮約: remote base と共有 ref が diverge した代表を、PR head と未 push commit の 2 経路で残す。ほかの relation 8 件は同じ守りの D としてサイクル 1 で削除した。 |
| `test_review_run.py::test_prepare_refuses_external_pr_without_explicit_checkout` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_rejects_wrong_request_workdir_and_shape` | 2 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_returns_skip_decisions_through_ordinary_comments` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_without_request_records_null_request` | 1 | S | request=None のときの inputs.request=None と実行記録 reviewer.provenance.run_id=unknown は独立した記録の守り。残した test_prepare_nonrunner_marks_unobserved_identity_unknown は返却 binding と candidates 側の provider/effort/cli_version を検査するが、record の no-request 分岐は検査しない。存在しない run の来歴を記録することを防ぐため元関数を復元する。 | 残す: request=None のときの inputs.request=None と実行記録 reviewer.provenance.run_id=unknown は独立した記録の守り。残した test_prepare_nonrunner_marks_unobserved_identity_unknown は返却 binding と candidates 側の provider/effort/cli_version を検査するが、record の no-request 分岐は検査しない。存在しない run の来歴を記録することを防ぐため元関数を復元する。 |
| `test_review_run.py::test_record_outputs_failure_after_save_keeps_the_review_result` | 1 | S | outputs_document 失敗時に、出力を特定できない実行記録を success と誤記録することを防ぎ、保存済み pair と cleanup の成功結果を維持する。record.update 例外とは別の分岐。 | 残す |
| `test_review_run.py::test_record_update_failure_does_not_change_the_review_result` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_refused_complete_records_complete_and_a_retry_succeeds` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_save_failure_records_save` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_second_review_records_update_mode_and_previous_digest` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_success_record_matches_saved_outputs_and_candidates` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_symlinked_review_directory_refuses_to_start` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_upstream_runner_uses_validated_upstream_remote` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |

## 受け入れと証拠

1. 棚卸しの表が現行の全テストを含み、削除・保持の理由が分かる。
2. F（F∩S を除く）・L・D の余り・撤去した経路のテストと、消したテスト専用の fixture が消えている。
3. 重さ「高」の守りで代表に絞ったものは、守る処理を一時的に壊した使い捨てのコピー（`/tmp` の `mktemp -d`）で、その代表が失敗することを 1 回ずつ確かめ、この文書に結果を記す。
4. 残したテスト、#231 の領域・全体・配置検査が通る。最後の commit で件数・行数を再計測し、前後をこの文書と #231 に記録する。
5. PR は `main` 向けの 1 件、本文に `Closes #231`。`--merge` のループで修正不要と確認した場合だけ `finalize.py` がマージする。

### 守りを壊す確認

最初の 30 件は commit `d706f3b`、追加の 2 件はレビュー後の commit `a28ad4e` の使い捨て worktree を `/tmp` の `mktemp -d` に作り、各行の実装側の判定を 1 か所だけ変更した。通常版と変異版で同じテストを実行し、追加 2 件は parametrize の関数全体を実行した。変異した実装は commit せず、使い捨て worktree は削除した。

| 壊した守り | 一時変更したファイル | 代表テスト | 観測結果 |
| --- | --- | --- | --- |
| `loop-unconfirmed-log` | `loop.py` | `test_loop_diagnostics.py::test_logs_are_read_only_when_safe[not_stopped]` | 検出（1 passed → 1 failed） |
| `loop-actual-reviewer` | `loop.py` | `test_loop_review.py::test_verify_reviewer_rejects_each_broken_condition[actual_agent_mismatch]` | 検出（1 passed → 1 failed） |
| `loop-herdr-hang` | `loop.py` | `test_loop_herdr_pane.py::test_start_succeeds_when_herdr_hangs` | 検出（1 passed → 1 failed） |
| `loop-after-run-reload` | `loop.py` | `test_loop_review.py::test_after_run_result_is_reloaded_before_reviewer_validation[payload_failed]` | 検出（1 passed → 1 failed） |
| `loop-stale-review-body` | `loop.py` | `test_loop_review.py::test_verify_reviewer_rejects_artifacts_that_do_not_belong_to_this_head[stale_body]` | 検出（1 passed → 1 failed） |
| `loop-preflight-side-effect` | `loop.py` | `test_loop_check_options.py::test_check_options_has_no_external_side_effects` | 検出（1 passed → 1 failed） |
| `loop-registered-worktree` | `loop.py` | `test_loop_review.py::test_missing_output_parent_does_not_hide_registered_worktrees[True-cleanup]` | 検出（1 passed → 1 failed） |
| `loop-unconfirmed-after-run` | `loop.py` | `test_loop_review.py::test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms[unconfirmed-recover]` | 検出（1 passed → 1 failed） |
| `loop-unconfirmed-reviewer` | `loop.py` | `test_loop_review.py::test_unconfirmed_attempt_holds_the_run_instead_of_planning[first-alpha]` | 検出（1 passed → 1 failed） |
| `loop-real-merge-state` | `loop.py` | `test_loop_state.py::test_finalize_stopped_keeps_the_real_merge[null]` | 検出（1 passed → 1 failed） |
| `loop-authenticated-login` | `loop.py` | `test_loop_state.py::test_records_need_the_authenticated_login[blank]` | 検出（1 passed → 1 failed） |
| `loop-outer-runner-state` | `loop.py` | `test_loop_review.py::test_verify_reviewer_rejects_each_broken_condition[outer_failed]` | 検出（11 passed → 1 failed、10 passed） |
| `loop-reported-success` | `loop.py` | `test_loop_diagnostics.py::test_response_extraction_is_decided_from_the_end_state[0-missing_result-success-False-True-unknown]` | 検出（3 passed → 1 failed、2 passed） |
| `review-missing-ref-outcome` | `pr_review_workspace.py` | `test_review_run.py::test_complete_returns_actual_compare_and_delete_outcome[missing]` | 検出（1 passed → 1 failed） |
| `review-ambiguous-codex-rollout` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_resolve_codex_model_name_fails_closed[non-unique-rollout-exactly one]` | 検出（1 passed → 1 failed） |
| `review-unsafe-explicit-model` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_resolve_runtime_model_name_fails_closed_outside_codex[../evil-safe filename]` | 検出（1 passed → 1 failed） |
| `review-invalid-attempt-id` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_create_rejects_unsafe_attempt_id[../escape]` | 検出（1 passed → 1 failed） |
| `review-noncanonical-state-repo` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_load_state_rejects_non_canonical_pr_repository[Usaturn/resoloop]` | 検出（1 passed → 1 failed） |
| `review-invalid-pr-number` | `review_target.py` | `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_pr_number[True]` | 検出（1 passed → 1 failed） |
| `review-empty-normalized-branch` | `review_target.py` | `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_branch[...]` | 検出（1 passed → 1 failed） |
| `review-fork-upstream-session` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_sessions_keep_the_open_pr_when_fork_and_upstream_share_number_branch_and_head[MERGED-OPEN]` | 検出（1 passed → 1 failed） |
| `review-abandon-user-file` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_abandon_keeps_a_session_with_files_it_did_not_create[notes.txt-unexpected entry]` | 検出（1 passed → 1 failed） |
| `review-target-base-remote` | `pr_review_workspace.py` | `test_port_routing.py::test_target_rejects_unvalidated_input_without_creating_session[remote]` | 検出（1 passed → 1 failed） |
| `review-invalid-repository-name` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_create_rejects_invalid_pr_repository[usaturn/..]` | 検出（1 passed → 1 failed） |
| `review-owned-history-foreign-worktree` | `pr_review_workspace.py` | `test_port_routing.py::test_shallow_recovery_refuses_unowned_git_or_user_data[foreign-worktree-owns another worktree]` | 検出（1 passed → 1 failed） |
| `review-shallow-owned-history` | `pr_review_workspace.py` | `test_review_run.py::test_ordinary_depth_one_checkout_reviews_whole_pr_without_shared_history_changes[head]` | 検出（1 passed → 1 failed） |
| `review-interrupted-worktree-record` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_abandon_clears_records_left_by_an_interrupted_worktree_add` | 検出（1 passed → 1 failed） |
| `review-first-session-wins` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_first_session_wins_same_destination` | 検出（1 passed → 1 failed） |
| `review-gh-pr-number` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_sessions_keep_when_gh_reports_another_number` | 検出（1 passed → 1 failed） |
| `review-existing-index-lock` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_snapshot_preserves_existing_index_lock` | 未検出（1 passed → 1 passed） |
| `review-no-optional-locks-index` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_snapshot_does_not_refresh_index` | 検出（1 passed → 1 failed） |
| `review-delete-index-lock` | `pr_review_workspace.py` | `test_pr_review_workspace.py::test_snapshot_preserves_existing_index_lock` | 検出（1 passed → 1 failed） |

`review-existing-index-lock` は `--no-optional-locks` を外しても、既存 lock がある fixture では Git が index を更新せず、この 1 件だけでは検出しなかった。同じ変更は `review-no-optional-locks-index` の `test_snapshot_does_not_refresh_index` で失敗し、既存 lock 自体の削除は `review-delete-index-lock` の `test_snapshot_preserves_existing_index_lock` で失敗した。二つの代表が別々の危険を検出することを確認した。

### 計測・検証の記録

指定の計測コマンドによる前後: **514 → 287 件**（227 件、44.2% 削減）、**8,830 → 7,301 行**（1,529 行、17.3% 削減）。前値は着手時の `origin/main`、後値はレビュー修正を取り込んだ `7924043` で測定した。正式な文書 commit はテスト収集対象を変えない。最終 HEAD の検証結果はセッションの記録と PR 本文に記載する。

## PR #255 レビュー修正サイクル 1

- 対象: `4b834563549aa366c6d42b4e8c54008f8da1fee7`。4 レビュアーの 7 件を、同 HEAD のコミット済み内容と隔離コピーで確認した。確認済み一覧: `reviews/usaturn/create-reso-world/#255-feat-issue-231-pr-review-tests/verified/4b834563549a.json`。7 件 confirmed、未確認 0 件。
- 分類: 解消済み 0 件、対応する 7 件、対応しない 0 件。実行許可は利用者の `$issue-to-pr #231 --merge`。`M-1`・`L-1` の欠けた S は誤った担当・診断・マージ状態をもっともらしく保存し得る。残りは Issue #231 が明示する D・専用補助・計測と Plan の成果物を満たすため対応する。
- 計画・判断担当: `gpt-6-sol`（Codex）。修正担当: `claude-opus-5-5`（`run_roles.py` の implement、担当 `claude-opus`）。自己レビューと修正確認の担当は `self`、1 回を予定する。

| レビューファイル | モデル / ランタイム | レビュー HEAD | 再実行 | 推奨 |
| --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | `gpt-6.1-sol` / pi | `4b834563549a` | はい | Approve |
| `SWE-2-Max.md` | `SWE-2 Max` / devin | `4b834563549a` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `deepseek/deepseek-v4.1-flash` / pi | `4b834563549a` | はい | Approve |
| `Grok-4.7.md` | `Grok 4.7` / cursor | `4b834563549a` | はい | Approve |

| 指摘 | 現行 HEAD での確認と採否 | 修正方針・検証 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1` | CLI の `assign` と `finalize-result` の転送をそれぞれ除くと、API 代表は通過する。誤担当・誤マージ状態を記録し得るため対応する。 | 既存の start 代表を CLI 入口へ変更し、finish の CLI 代表を 1 件復元する。各転送の変異で失敗を確認する。 |
| `gpt-6.1-sol#L-1` | 非ログの `sensitive_paths` 条件を外すと、誤った `response_extraction` を保存する。対応する。 | 読める通常ログと非ログの receipt の負例を戻し、空の `sensitive_paths` の正例を残す。 |
| `gpt-6.1-sol#L-2` | 共有 ref の 5 relation × 2 local_commit は PR 前から存在し、同じ実装経路・不変条件を重ねる。#231 の D 削減条件として対応する。 | diverged の 1 relation と、PR head・未 push commit の 2 経路を残す。共有 ref の変更と tag fetch の変異で検出力を確かめる。 |
| `gpt-6.1-sol#L-3` | `record_attempts` は唯一の呼出しテストを削除した後、定義だけ残った。#231 の専用補助の削除条件として対応する。 | 補助を削除し、参照検索と Ruff で確認する。テスト追加は不要。 |
| `deepseek-deepseek-v4.1-flash#M-1` | finalize false・PR true と、PR open・finalize 無しの false を削除していた。false と null を混同した誤報告を防ぐため対応する。 | 互いに独立した 2 ケースを復元し、各判定だけを壊して検出する。 |
| `Grok-4.7#I-1` | Spec と PR 本文には前後の数値があるが、Issue #231 に無い。受入条件として対応する。 | 修正後のコミット済み計測値を Issue にコメントする。 |
| `SWE-2-Max#I-1` | Plan Task 3 の Step 4・5 が未チェックのまま、計測・push・PR 作成は実行済み。成果物の状態を正す。 | 実行済みの段階を確認し、Plan のチェックを更新する。 |

### 守る条件と影響経路

このサイクルが初回のレビュー修正であり、同じ条件の再発・レビュー修正が生んだ回帰のきっかけには当たらない。採用条件は `AGENTS.md` の S/F∩S と D の代表の定義に従う。設計案は「旧テストをすべて戻す」「API 代表だけ残す」「独立する CLI・false・receipt の条件だけ戻す」を比べ、最後の案を選んだ。旧テスト全件では D が残り、API だけでは CLI 境界の欠落を検出できない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| CLI の意味を変える引数が実処理へ届く | `main/dispatch start` → `start` → run.json / 計画 | 修正する | 指定した担当とサイクル数を保存 | CLI 代表と `assign` 転送の変異 | `702a177` のテストで、通常版通過・転送除去で失敗。 |
| CLI の意味を変える引数が実処理へ届く | `main/dispatch finish` → `finish` → merged の記録 | 修正する | PR 不可読時に finalize の `true` を保存 | CLI 代表と `finalize-result` 転送の変異 | `702a177` のテストで、通常版通過・転送除去で失敗。 |
| マージ状態は実際に読めた PR を優先する | `cycle_end` の finalize false と PR merged true | 修正する | 停止したまま merged true を保存 | false の代表と上書き変異 | `702a177` のテストで、通常版通過・上書き変異で失敗。 |
| マージ状態は実際に読めた PR を優先する | `finish --abort` の PR open と finalize 無し | 修正する | merged false と null を区別 | open の代表と false→null 変異 | `702a177` のテストで、通常版通過・false→null 変異で失敗。 |
| 秘密の残る保持物がある試行を誤診しない | `diagnose_attempt` → `classify_cause` → 原因記録 | 修正する | 非ログ receipt があれば unknown、空なら response_extraction | 負例・正例と条件除去変異 | `702a177` のテストで、通常版通過・条件除去で負例が失敗。 |
| 共有 Git ref と別 worktree を変えない | `configure_base_fetch` → `prepare` → `complete`、失敗後の回収 | 修正する | PR head・未 push commit の両方で共有 ref が不変 | diverged の代表、tag fetch と update-ref の変異 | `702a177` で通常版 2 件通過、両変異で 2 件失敗。 |
| #231 の成果を確認できる | テスト収集・追跡行数 → Spec・Issue・Plan | 修正する | 数値・実施状態が一致 | 指定コマンド、Issue コメント、Plan 差分 | 計測は `7924043` で 287 件・7,301 行。Plan のチェック欄を更新した。Issue コメントは push 後に投稿する。 |

失敗時の状態確認は、テスト内の fake GitHub・bare remote の実状態と loop が記録した merged を対にしている。変異は隔離コピーだけに入れ、対象 PR の本体実装は変更していない。共有 ref の `--refmap=` を外す変異はこの fixture のどの relation でも検出せず、代表を縮めて失った検出力ではない。tag fetch と共有 ref 更新の変異は縮約後の 2 例がともに検出した。

修正後の領域テストは `287 passed`、全体 pytest は `1,499 passed`、bash は `23 tests`、配置と Ruff は通過した。実行ログは `tmp/agents/issue-231.qhu0z91i/` の `full-pytest-cycle1.log`、`bash-cycle1.log`、`layout-cycle1.log`、`ruff-cycle1.log`。`run_roles.py` の担当は `stop_confirmed=true`・コミット `702a177` を返したが、別タスクの worktree が並行して変更・削除された監査通知により runner 自体は終了コード 1 だった。担当のコミットは指定した 4 テストファイルだけで、専用 worktree に `7924043` として取り込んだ。別タスクの worktree は変更していない。自己レビューと Issue への計測反映は続行中。
