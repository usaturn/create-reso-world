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

関数単位で 269 件、parametrize を展開すると 514 件。着手時の `pytest --collect-only` と AST に対して、全件が表に 1 回だけ現れることを確認した。表の「縮約」は削除する case と残す代表を実装時に照合する。

| ファイル / テスト関数 | 展開前の件数 | 分類 | 理由 | 対応・残す代表 |
| --- | ---: | --- | --- | --- |
| `test_loop_check_options.py::test_check_options_accepts_the_template_and_reports_effective_assignments` | 1 | 迷い | 固定された既定値・担当一覧は F。PR・GitHub・run・ロックに触れない部分は、高: 前検査で副作用を残すことを防ぐ S。 | 縮約: 既定値の完全一致は外し、正常終了と assert_untouched を残す。 |
| `test_loop_check_options.py::test_check_options_does_not_accept_fresh_review` | 1 | L | argparse が usage と終了コード 2 で拒否する。 | 消す |
| `test_loop_check_options.py::test_check_options_does_not_touch_herdr` | 1 | L | 誤ったペイン名は Herdr 上で見え、start の warning にも出る。 | 消す |
| `test_loop_check_options.py::test_check_options_reads_the_personal_config_when_not_given` | 1 | L | 設定の不備は start または runner が終了コードと理由を出す。 | 消す |
| `test_loop_check_options.py::test_check_options_rejects_a_codex_reviewer_in_the_personal_config` | 1 | L | 設定の不備は start または runner が終了コードと理由を出す。 | 消す |
| `test_loop_check_options.py::test_check_options_rejects_what_start_rejects_with_the_same_reason` | 10 | D | 無効設定の検出は start・run_roles の終了コード 2 と明示理由で気付く。前検査の副作用は正常例の assert_untouched で代表して確認する。 | 消す: 10 ケースは同じ設定拒否経路。 |
| `test_loop_check_options.py::test_check_options_reports_the_options_start_would_record` | 1 | S | 中: 前検査と start の担当・設定が食い違うと、別の担当で気付かず実行する。 | 残す |
| `test_loop_diagnostics.py::test_all_failed_review_returns_the_diagnostics_to_the_controller` | 2 | S | 中: 全員失敗時に診断の保存先や保存失敗を司令塔へ返さず、残存資源と原因を見失う損害を防ぐ。 | 縮約: id=saved を残す。unsaved は unsaved_diagnostic_keeps_the_output_and_tells_the_controller で代表。 |
| `test_loop_diagnostics.py::test_cause_uses_only_failure_channels` | 16 | S | 中: モデル本文を実際の失敗として分類し、誤った原因を永続診断に保存する損害を防ぐ。 | 縮約: id=tool-output-is-data,error-event,traceback-line-number-is-not-a-status,bracketed-diagnostic を残す。他は同じ出所/優先順位の重複。 |
| `test_loop_diagnostics.py::test_different_failures_leave_distinct_causes_after_cleanup` | 1 | S | 中: ログ回収後に別々の失敗を同じ原因として記録する損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_final_pi_failure_survives_a_long_history` | 3 | S | 中: 長い履歴で最後の失敗を見失い、誤原因を保存する実発生 #237 の再発を防ぐ。 | 縮約: id=history-line-over-1-mib,history-line-over-the-limit を残す。final-message-without-agent-end は同じ末尾イベント。 |
| `test_loop_diagnostics.py::test_keep_diagnostic_covers_only_reviewers_with_a_failure` | 3 | S | 中: 失敗した試行の診断を保存し忘れ、ログ回収後に根拠を失う損害を防ぐ。 | 残す: id=accepted,failed-fallback,rejected を残す。成功の不保存と失敗の保存を対で確認するため。 |
| `test_loop_diagnostics.py::test_large_log_is_read_from_the_tail` | 2 | D | 長いログの末尾確認は final_pi_failure_survives_a_long_history で代表する。 | 消す |
| `test_loop_diagnostics.py::test_logs_are_read_only_when_safe` | 8 | S | 高: sensitive・symlink・出力外・生存中のログを読んで秘密や別ファイルに触れる損害を防ぐ。 | 縮約: case=readable,sensitive,outside_output,symlink,fifo を残す。not_recorded/not_stopped/missing は同じ読み取り拒否の重複。 |
| `test_loop_diagnostics.py::test_model_prose_stdout_never_decides_the_cause` | 8 | S | 中: Devin のコード例やモデル本文を実失敗として扱い、誤原因を保存する損害を防ぐ。 | 縮約: id=devin-fenced-example,devin-stderr,cursor-cli-line,unknown-runtime を残す。ほかは同じ stdout/stderr 境界の重複。 |
| `test_loop_diagnostics.py::test_recovered_failures_do_not_decide_the_cause` | 7 | S | 中: 回復した一時的エラーを最終原因として保存する損害を防ぐ。 | 縮約: id=claude-retry-overloaded,claude-retries-exhausted,pi-retry-recovered,pi-retries-exhausted-without-agent-end を残す。残りは同じ回復/失敗経路。 |
| `test_loop_diagnostics.py::test_reported_failures_are_not_response_extraction` | 4 | S | 中: pi が報告した提供元の失敗を応答抽出失敗と誤記録する損害を防ぐ。 | 縮約: id=failed-message,nothing-reported を残す。agent_end 内の類似例は重複。 |
| `test_loop_diagnostics.py::test_rerun_keeps_a_diagnostic_for_each_request` | 1 | S | 中: 再実行が最初の失敗記録を上書きして調査履歴を失う損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_response_extraction_is_decided_from_the_end_state` | 6 | S | 中: CLI の失敗を応答抽出失敗と誤分類し、復旧判断を誤らせる損害を防ぐ。 | 縮約: 値 (exit_code=0,state=response_failed,reported=None,sensitive=False,stopped=True,cause=response_extraction) と (exit_code=1,state=response_failed,reported=None,sensitive=False,stopped=True,cause=unknown) を残す。 |
| `test_loop_diagnostics.py::test_review_reads_stdout_by_the_reviewer_runtime` | 1 | S | 中: レビュアーの runtime を取り違え、失敗の原因を誤記録する損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_secret_in_logs_never_reaches_the_records` | 1 | S | 高: ログ中の秘密情報が永続記録や CLI の JSON 出力へ漏れる損害を防ぐ。 | 残す |
| `test_loop_diagnostics.py::test_unobservable_logs_are_not_response_extraction` | 5 | D | 読めないログの分類は logs_are_read_only_when_safe と response_extraction_is_decided_from_the_end_state で代表する。 | 縮約: change=partial のみ残す。partial は末尾切り出しに失敗報告が隠れる固有条件。 |
| `test_loop_diagnostics.py::test_unobserved_values_are_listed` | 1 | D | 未観測の原因を unknown とする守りは unobservable_logs_are_not_response_extraction と重複。 | 消す |
| `test_loop_diagnostics.py::test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller` | 1 | S | 高: 診断の保存失敗時に唯一のログを削除し、原因調査不能にする損害を防ぐ。 | 残す |
| `test_loop_herdr_pane.py::test_run_record_without_herdr_pane_still_loads` | 1 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: ファイル削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_failure_does_not_call_herdr` | 1 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: ファイル削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_renames_the_current_pane_once` | 3 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: ファイル削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_skips_herdr_outside_a_pane` | 6 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: ファイル削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_herdr_pane.py::test_start_succeeds_when_herdr_fails` | 3 | L | ペイン名の異常は UI または warning、古い記録の読込失敗は解析エラーとして直ちに分かる。 | 消す: ファイル削除後も conftest.py の autouse no_herdr は維持。 |
| `test_loop_review.py::test_after_run_result_is_reloaded_before_reviewer_validation` | 2 | S | 高: after_run が却下した結果を古い成功値で受け付け、失敗したレビューで計画へ進む損害を防ぐ。 | 縮約: change=payload_failed を残す。payload_unchanged は成功の重複。 |
| `test_loop_review.py::test_cleanup_output_removes_only_its_own_prefix` | 2 | S | 高: 別の出力ディレクトリを削除する損害を防ぐ。 | 残す: own=True/False の両方を残す。拒否と正常回収を対で検査。 |
| `test_loop_review.py::test_cleanup_without_force_keeps_only_a_written_worktree` | 2 | S | 高: レビュアーが書いた worktree の変更を消す損害を防ぐ。 | 残す: write=True/False の両方を残す。 |
| `test_loop_review.py::test_cycle_end_reads_the_roles_json_that_run_roles_writes` | 1 | S | 中: 実際の担当と違う担当を判断の記録に保存する損害を防ぐ。単なる解析失敗部分は L。 | 残す |
| `test_loop_review.py::test_cycle_record_without_the_rerun_fields_loads` | 1 | L | 旧 schema の読み込みが壊れれば Pydantic/解析エラーで明示される。 | 消す |
| `test_loop_review.py::test_failed_cleanup_paths_are_reported` | 1 | S | 中: 回収できなかったパスを報告せず、残存資源を見失う損害を防ぐ。 | 残す |
| `test_loop_review.py::test_interrupted_rerun_is_not_relaunched` | 1 | D | HEAD 移動と中断後の再起動拒否は初回 review の同じガードの代表テストで確認する。 | 消す |
| `test_loop_review.py::test_interrupted_review_without_result_is_not_rerun` | 1 | S | 高: 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる損害を防ぐ。 | 残す |
| `test_loop_review.py::test_missing_output_checks_fail_closed` | 6 | S | 高: git 登録確認が失敗した状態を空とみなして資源を削除する損害を防ぐ。 | 縮約: entrypoint=audit,failure=git_unavailable を残す。他 5 組合せは同じ失敗時停止の重複。 |
| `test_loop_review.py::test_missing_output_parent_does_not_hide_registered_worktrees` | 4 | S | 高: 親ディレクトリが消えても登録済み worktree を見落としてロックを解放・誤削除する損害を防ぐ。 | 縮約: entrypoint=cleanup,locked=True を残す。audit と unlocked は同じ登録確認の重複。 |
| `test_loop_review.py::test_missing_parent_with_no_registration_is_removed` | 2 | S | 中: 拒否だけの実装で回収が永遠に進まないことを防ぐ正例。 | 縮約: entrypoint=cleanup を残す。audit は同じ正例の重複。 |
| `test_loop_review.py::test_next_commands_never_carry_placeholders_and_recover_rejects_them` | 1 | S | 高: 書きかけの停止確認を事実として受理し、生存プロセスの資源とロックを解放する損害を防ぐ。 | 残す |
| `test_loop_review.py::test_recover_keeps_files_that_may_hold_secrets` | 1 | S | 高: 回収時に秘密情報が残りうる receipt を消し、必要な調査記録を失う損害を防ぐ。 | 残す |
| `test_loop_review.py::test_request_is_kept_only_from_a_regular_file` | 1 | S | 高: 未停止の書き手や symlink をたどって別のファイルを読み取り、保存対象を誤る損害を防ぐ。 | 残す: symlink/missing/not-stopped の拒否と通常ファイルの受理を残す。 |
| `test_loop_review.py::test_rerun_is_not_started_while_another_attempt_is_unconfirmed` | 1 | S | 高: 未停止の試行と同時に再実行し、同じ成果や資源へ競合書き込みする損害を防ぐ。 | 残す |
| `test_loop_review.py::test_rerun_refuses_when_the_head_moved` | 1 | D | HEAD 移動と中断後の再起動拒否は初回 review の同じガードの代表テストで確認する。 | 消す |
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
| `test_loop_review.py::test_two_cycles_reuse_the_pre_push_review_and_end_merged` | 1 | D | HEAD 別の再利用、判断、マージ、ロック解放は各守りの代表テストに分解済み。大きな統合シナリオの重複。 | 消す |
| `test_loop_review.py::test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms` | 4 | S | 高: 生存中かもしれない after_run の出力を消し、ロックを解放する損害を防ぐ。 | 縮約: entry=recover,case=unconfirmed を残す。interrupted は次の専用テスト、finish_abort は同じ資源ガード。 |
| `test_loop_review.py::test_unconfirmed_attempt_holds_the_run_instead_of_planning` | 3 | S | 高: レビュアーの停止を確認しないまま計画を始め、資源を消す損害を防ぐ。 | 縮約: id=first-alpha,rerun-beta を残す。first-beta は担当を替えただけの重複。 |
| `test_loop_review.py::test_unconfirmed_stop_holds_the_lock_until_operator_recovery` | 1 | S | 高: 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる損害を防ぐ。 | 残す |
| `test_loop_review.py::test_verify_reviewer_accepts_a_complete_payload_and_records_hashes` | 1 | S | 中: 正しい成果も拒否する実装や、採用した成果のハッシュ・担当を誤記録する損害を防ぐ。拒否テストの正例。 | 残す |
| `test_loop_review.py::test_verify_reviewer_rejects_artifacts_that_do_not_belong_to_this_head` | 3 | S | 高: payload は正しくても本文や候補一覧が別 PR・HEAD の場合に採用する損害を防ぐ。 | 縮約: case=other_pr_document,stale_body を残す。symlink_inside_dir は verify_reviewer_rejects_each_broken_condition の review_symlink で代表。 |
| `test_loop_review.py::test_verify_reviewer_rejects_each_broken_condition` | 12 | S | 高: 別 run・担当・PR・HEAD の成果、未停止の担当、改ざんされた成果を受け付けて計画・マージへ進む損害を防ぐ。 | 縮約: case=stop_unconfirmed,payload_failed,request_mismatch,other_pr,reviewed_head_mismatch,review_outside_dir,review_symlink,pair_mismatch,active_count_mismatch を残す。outer_failed/actual_agent_mismatch/findings_invalid は代表の重複または後段で明示エラー。 |
| `test_loop_review.py::test_write_exceptions_name_the_target_checkout_git` | 1 | S | 高: runner に別 checkout の Git 書き込み権限を渡す損害を防ぐ。 | 残す |
| `test_loop_reviewer_protocol.py::test_literal_reviewer_completes_the_real_helper_within_the_declared_exceptions` | 1 | S | 高: read-only runner の書き込み範囲が広がる、または別 PR・HEAD の成果が混入する損害を実 helper 経路で検出する。 | 残す |
| `test_loop_state.py::test_a_differently_cased_pr_url_shares_the_lock` | 1 | S | 高: URL の大文字小文字違いで同じ PR に二重ロックを作り、同時書き込みする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_a_failed_lock_write_leaves_no_lock` | 1 | D | 失敗したロック書込後の競合・解放はロック所有者の代表テストで確認する。残留した場合も lock_held として明示される。 | 消す |
| `test_loop_state.py::test_abort_after_a_finalize_merge_keeps_the_merge` | 2 | S | 高: finalize 後に cycle-end が停止しても、abort でマージ済みを false と記録する損害を防ぐ。 | 縮約: id=pr-unreadable を残す。pr-read は abort_records_the_merge_state_it_observed と重複。 |
| `test_loop_state.py::test_abort_needs_a_classified_reason` | 1 | L | 理由の書式違反は finish が引数エラーとして明示する。 | 消す |
| `test_loop_state.py::test_abort_records_the_merge_state_it_observed` | 10 | S | 高: PR の実状態、finalize の最後の観測、未確認 null を混同してマージ状態を誤報告する損害を防ぐ。 | 縮約: id=merged-finalize-false、unreadable、open-finalize-true を残す。他 7 件は同じ優先順位の重複。 |
| `test_loop_state.py::test_abort_treats_a_gh_that_cannot_start_as_unreadable` | 1 | D | PR が読めないときの finalize fallback は abort_after_a_finalize_merge_keeps_the_merge の pr-unreadable で代表する。 | 消す |
| `test_loop_state.py::test_cli_finish_abort_passes_the_finalize_result` | 1 | D | finalize 結果を abort へ渡す守りは abort_after_a_finalize_merge_keeps_the_merge で代表する。 | 消す |
| `test_loop_state.py::test_cli_start_reports_a_refused_fix_assignment` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_cycle_end_accepts_a_spec_commit_merge` | 1 | S | 高: 検証 HEAD の上に Spec commit を載せた PR のマージを、別 commit と誤照合する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_before_the_record_is_posted_keeps_the_cycle_open` | 1 | S | 高: レビューや判断記録の前にサイクルを完了し、未検証の PR を成功扱いする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_reads_the_authenticated_users_record` | 1 | S | 高: 他人のコメントを認証済み利用者の判断として採用する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_cycle_end_rejects_a_malformed_spec_commit` | 4 | L | 不正 SHA は finalize 結果の解析または HEAD 照合の明示エラーになる。 | 消す |
| `test_loop_state.py::test_cycle_limit_ends_with_fixes_pushed` | 1 | S | 高: サイクル上限後に追加レビューなしで次へ進み、未検証のままマージする損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped` | 1 | S | 高: 未マージまたは別 HEAD のマージを検証済みとして完了報告する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result` | 1 | S | 高: 不正な finalize 結果で run を上書きし、マージ状態を誤記録する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_stopped_ends_the_run_as_stopped_and_not_merged` | 1 | S | 高: finalize の停止をマージ成功として報告する損害を防ぐ。 | 残す |
| `test_loop_state.py::test_finalize_stopped_keeps_the_real_merge` | 4 | S | 高: finalize が停止しても、実際のマージを未マージとして誤報告する損害を防ぐ。 | 縮約: id=null と true_merge_parent を残す。false/true_another_head は同じ状態優先の重複。 |
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
| `test_loop_state.py::test_start_records_options_and_effective_assignments` | 2 | S | 中: run.json と計画への引き渡しで別の担当・設定を記録する損害を防ぐ。 | 縮約: entrypoint=api を残す。cli は同じ保存経路。 |
| `test_loop_state.py::test_start_refuses_a_closed_pr` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_refuses_a_pr_whose_checkout_cannot_be_resolved` | 1 | L | checkout 不明は対象 resolver またはレビュアーが理由付きエラーで停止する。 | 消す |
| `test_loop_state.py::test_start_rejects_a_codex_reviewer` | 3 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_rejects_an_unknown_role_and_inspect_self` | 1 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_start_rejects_fix_assignments_that_run_roles_refuses` | 6 | L | closed PR・無効な担当は start、run_roles、runner が理由付き非 0 終了で検出する。 | 消す |
| `test_loop_state.py::test_status_returns_the_next_command_after_a_restart` | 1 | S | 高: 再開時に誤った段階へ進み、レビューや判断を飛ばす損害を防ぐ。 | 残す |
| `test_loop_state.py::test_stopped_record_ends_the_run_and_finish_releases_the_lock` | 1 | D | 停止結果の保存とロック解放は別の finalize/abort/所有者テストで代表する。 | 消す |
| `test_pr_review_fix_loop_skill_contract.py::test_loop_skill_runs_only_when_explicitly_invoked` | 1 | F∩S | 高: disable-model-invocation の権限境界が外れると、明示依頼なしに push・マージまで進む。 | 残す |
| `test_port_routing.py::test_explicit_commit_has_separate_pair_and_validates_worktree_head` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_port_routing.py::test_external_checkout_requires_explicit_source_and_matching_remote` | 1 | S | 防ぐ損害（高）: 他の Git や利用者所有ファイルを対象として操作・削除する。 | 残す |
| `test_port_routing.py::test_failed_shallow_create_can_be_inspected_then_abandoned` | 1 | S | 防ぐ損害（中）: 失敗後の所有セッションと回収手掛かりを失う。 | 残す |
| `test_port_routing.py::test_fork_and_upstream_same_number_are_independent` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_port_routing.py::test_moving_live_head_keeps_drafts_then_fresh_session_continues` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_port_routing.py::test_ref_delete_failure_keeps_a_retryable_session` | 1 | S | 防ぐ損害（中）: 失敗後の所有セッションと回収手掛かりを失う。 | 残す |
| `test_port_routing.py::test_shallow_recovery_refuses_unowned_git_or_user_data` | 9 | S | 防ぐ損害（高）: 他の Git や利用者所有ファイルを対象として操作・削除する。 | 縮約: 代表: journal-owner, git-symlink, foreign-worktree, repo-notes。journal-kind/worktree/parent と replacement/git-replacement は同じ所有権検査の D。 |
| `test_port_routing.py::test_target_rejects_unvalidated_input_without_creating_session` | 7 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 縮約: 代表: remote, sha, url, repository。missing/null は明示エラー L、number は PR 識別検査と D。 |
| `test_port_routing.py::test_upstream_full_diff_pair_save_cleanup_preserves_shared_refs` | 1 | S | 防ぐ損害（高）: PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 残す |
| `test_pr_review_workspace.py::test_a_repeated_signal_does_not_cut_the_end_record` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_clears_records_left_by_an_interrupted_worktree_add` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: HEAD。ほかの破損形は同じ管理レコード回収の D。 |
| `test_pr_review_workspace.py::test_abandon_keeps_a_journal_without_pr_repository` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_abandon_keeps_a_session_with_files_it_did_not_create` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: notes.txt と review-backup/opus-5.md。nested/ は同じ利用者所有 entry の D。 |
| `test_pr_review_workspace.py::test_abandon_keeps_a_worktree_locked_for_another_reason` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_another_repository` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_records_of_another_worktree` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_refuses_while_the_attempt_is_running` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_removes_a_worktree_left_initializing` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_abandon_touches_only_its_own_attempt` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_waits_for_a_checkout_that_outlives_create` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_abandon_waits_for_the_repository_review_lock` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
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
| `test_pr_review_workspace.py::test_cleanup_removes_worktree_holding_verification_artifacts` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_cleanup_waits_for_repository_review_lock` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_create_destination_replaces_unsafe_directory_characters` | 7 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_create_destination_uses_hash_pr_number_and_sanitized_branch` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_create_does_not_fsync_session_files` | 1 | L | 気付ける経路: 長いロック待ち・処理時間として通常利用時に明白になる。 | 消す |
| `test_pr_review_workspace.py::test_create_normalizes_pr_repository_case` | 1 | 迷い | 旧 create API の caller はリポジトリ内で見つからないが、互換記述があり外部 caller を否定できない。削除判断を保留。 | 残す |
| `test_pr_review_workspace.py::test_create_outlives_a_reader_that_closed_its_stderr` | 1 | L | 気付ける経路: BrokenPipeError と非 0 終了で helper が停止する。 | 消す |
| `test_pr_review_workspace.py::test_create_parser_accepts_explicit_model_name` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_create_parser_requires_attempt_id` | 1 | L | 気付ける経路: argparse が非 0 終了とエラーメッセージを返す。 | 消す |
| `test_pr_review_workspace.py::test_create_pins_existing_review_snapshot` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_explicit_model_outside_codex` | 1 | 迷い | 旧 create API の caller はリポジトリ内で見つからないが、互換記述があり外部 caller を否定できない。削除判断を保留。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_model_and_artifact_paths` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_create_pins_slash_model_name_as_hyphenated_filename` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_create_records_its_phases_in_the_journal` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す: 固定の phase 名・順序の写しは F。残す場合は中断時の所有情報と回収判断に効く項目に絞る。 |
| `test_pr_review_workspace.py::test_create_rejects_invalid_pr_repository` | 8 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: 代表: ../resoloop。残りの文法変種は同じ検証の D/L。 |
| `test_pr_review_workspace.py::test_create_rejects_reused_attempt_id` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_create_rejects_unsafe_attempt_id` | 5 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: ../escape。その他の文字列変種は同じ範囲検査の D/L。 |
| `test_pr_review_workspace.py::test_create_reports_legacy_review_without_adopting_it` | 1 | S | 防ぐ損害（中）: 旧配置のレビューを別リポジトリの前回レビューとして黙って採用・移動しない。互換 API は残す。 | 残す: 旧 create は非テスト caller を確認できないが、現行文書が他 caller 向け互換と記す。返却値だけの撤去は行わない。 |
| `test_pr_review_workspace.py::test_create_requires_explicit_model_outside_codex` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_pr_review_workspace.py::test_create_returns_the_pinned_findings_draft` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_destination_fingerprint_distinguishes_symlink_entries` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_findings_destination_must_stay_under_the_review_findings_directory` | 5 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 縮約: 代表: ../ 正規化脱出、別 repository。ほかの場所/拡張子は同じ境界または明示エラー。 |
| `test_pr_review_workspace.py::test_findings_draft_cannot_escape_the_session_via_symlink` | 1 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 残す |
| `test_pr_review_workspace.py::test_findings_paths_require_repository_identity` | 2 | S | 防ぐ損害（中）: 別 PR・HEAD の候補一覧、古い候補一覧、または不完全なレビュー成果を正式保存する。 | 縮約: 代表: paths。destination は同じ repository 必須条件の D。 |
| `test_pr_review_workspace.py::test_first_session_wins_same_destination` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_inspect_and_abandon_refuse_another_pr_repository` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_inspect_ignores_a_cut_off_journal_line` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_inspect_refuses_an_attempt_id_shared_by_two_sessions` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_inspect_reports_a_completed_attempt` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_inspect_reports_an_unknown_attempt_as_absent` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_killed_create_reports_its_last_phase_and_leftovers` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_legacy_inspect_reports_but_abandon_preserves_an_unowned_repo_directory` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_load_state_rejects_non_canonical_pr_repository` | 5 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: 代表: Usaturn/resoloop, missing。型違いは同じ検証の D。 |
| `test_pr_review_workspace.py::test_load_state_rejects_previous_version` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_load_state_rejects_tampered_previous_review` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_fails_closed` | 6 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 縮約: 代表: unsafe-model, non-unique-rollout, invalid-json。missing-thread/rollout/context は明示エラー L。 |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_ignores_unterminated_partial_tail` | 1 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_rejects_malformed_completed_record` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_replaces_slash_with_hyphen` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_replaces_whitespace_with_hyphen` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_skips_records_outside_expected_schema` | 5 | L | 気付ける経路: WorkspaceError、OS エラー、または明示的な非 0 終了として通常実行時に現れる。 | 消す |
| `test_pr_review_workspace.py::test_resolve_codex_model_name_uses_latest_turn_context` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_accepts_slash_equivalent_explicit_in_codex` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_fails_closed_outside_codex` | 5 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 縮約: 代表: ../evil。None は明示エラー L、ほかの不正モデル名は D。 |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_rejects_codex_override` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_replaces_slash_with_hyphen` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_replaces_whitespace_with_hyphen` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_resolve_runtime_model_name_uses_explicit_name_outside_codex` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_review_artifact_paths_preserve_exact_model_name` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_branch` | 5 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_review_artifact_paths_reject_invalid_pr_number` | 4 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_safe_destination_rejects_symlink_escape` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_save_allows_another_review_destination_to_change` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_save_allows_unrelated_main_changes` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_save_allows_untracked_reviews_directory_to_appear` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
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
| `test_pr_review_workspace.py::test_save_with_findings_removes_new_candidates_when_the_review_copy_fails` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
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
| `test_pr_review_workspace.py::test_sessions_keep_when_gh_reports_another_number` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_snapshot_does_not_refresh_index` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_copies_regular_file` | 1 | S | 防ぐ損害（高）: モデル・PR・HEAD・保存先の識別を取り違え、もっともらしい誤レビューを保存する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_rejects_non_regular` | 3 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_rejects_source_race` | 1 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_snapshot_existing_review_reports_missing` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_pr_review_workspace.py::test_snapshot_preserves_existing_index_lock` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_pr_review_workspace.py::test_snapshot_reports_changes_excluding_reviews` | 4 | S | 防ぐ損害（高）: 利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 残す |
| `test_pr_review_workspace.py::test_terminated_create_records_the_signal` | 1 | S | 防ぐ損害（高）: 未終了 PR や実行中の試行を回収可能と誤判定して worktree を削除する。 | 残す |
| `test_pr_review_workspace.py::test_version6_session_is_kept_by_verify_save_and_cleanup` | 1 | F∩S | 防ぐ損害（高）: 旧 state の repository 不明を無視すると、別 PR の worktree を削除・レビューを上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_marks_a_timed_out_attempt_on_the_started_record` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_rejects_an_invalid_result_file` | 1 | L | 気付ける経路: Pydantic の result 検証が失敗し、非 0 終了を返す。 | 消す |
| `test_review_run.py::test_attach_runner_rejects_conflicting_values_without_writing` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_reports_attempts_without_a_record` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_attach_runner_skips_files_outside_the_record_layout` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_attach_runner_writes_the_runner_block_once_and_keeps_provenance` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_cleanup_failure_records_cleanup_with_saved_outputs` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_complete_preserves_failure_as_failed_result` | 9 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 縮約: 代表: binding, destination, head, coverage。missing/invalid/api はエラーが明白、reviewer/coverage_kind は別の入力形の D。 |
| `test_review_run.py::test_complete_refuses_skill_changed_after_prepare` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_complete_rejects_changed_draft_before_writing_anywhere` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_complete_reports_saved_but_uncleaned_result_as_failure` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_complete_returns_actual_compare_and_delete_outcome` | 3 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 縮約: 代表: deleted, repinned。missing は同じ compare-and-delete の D。 |
| `test_review_run.py::test_complete_saves_zero_findings_with_provenance` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_fail_request_returns_without_blocking_and_preserves_failure_record` | 12 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 縮約: 代表: state_kind=prepared × kind=regular/fifo。ほかは同じ記録保護の D、FIFO の待ちは timeout で分かる L。 |
| `test_review_run.py::test_helper_write_exceptions_grant_git_data_only_where_the_helper_writes_it` | 4 | F∩S | 防ぐ損害（高）: 固定した書込許可範囲を広げると、writes=false の担当が利用者 Git を変更できる。 | 残す: 4 組合せを維持。親/別 checkout と shallow/通常で許可すべき Git 書込先が実際に異なる。 |
| `test_review_run.py::test_model_fail_records_review` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_ordinary_depth_one_checkout_reviews_whole_pr_without_shared_history_changes` | 3 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 縮約: 代表: head, unpushed。explicit は同じ完全差分取得の D。 |
| `test_review_run.py::test_other_runtime_request_path_acceptance_is_unchanged` | 2 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_payloads_without_a_record_still_name_the_run_record_key` | 1 | L | 気付ける経路: 呼び出し側が欠落キーを解析すると例外になる。 | 消す |
| `test_review_run.py::test_prepare_alone_leaves_started_record_like_a_killed_run` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_base_fetch_failure_returns_correlated_retained_paths` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_binds_request_and_local_records` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_create_failure_reports_owned_session_retained_paths` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_fails_without_observed_model` | 1 | L | 気付ける経路: 必須入力・ファイルの欠落を WorkspaceError で報告して停止する。 | 消す |
| `test_review_run.py::test_prepare_failure_after_base_fetch_keeps_shared_refs_unchanged` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_prepare_failure_after_resolve_records_prepare` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_failure_before_resolve_writes_no_record` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_prepare_failure_is_kept_when_the_model_later_calls_fail` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_prepare_nonrunner_marks_unobserved_identity_unknown` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_parallel_sessions_pin_their_own_base` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_pi_requires_both_current_environment_identifiers` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_preserves_shared_refs_and_other_worktree_base_refs` | 10 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_refuses_external_pr_without_explicit_checkout` | 1 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_rejects_wrong_request_workdir_and_shape` | 2 | S | 防ぐ損害（高）: 誤った対象をレビュー・保存する、保護範囲外へ書く、または利用者の Git ref・ファイルを変える。 | 残す |
| `test_review_run.py::test_prepare_returns_skip_decisions_through_ordinary_comments` | 1 | S | 防ぐ損害（中）: 実行記録やレビュー結果の識別・状態・失敗を誤って報告または上書きする。 | 残す |
| `test_review_run.py::test_prepare_without_request_records_null_request` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
| `test_review_run.py::test_record_outputs_failure_after_save_keeps_the_review_result` | 1 | D | 同じ守りの代表テストが別にあるため重複。 | 消す |
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

未実施。代表と変更点、実行したテスト、失敗した観測結果を、実施後に記録する。

### 計測・検証の記録

前値: 514 件（`uv run --locked pytest --collect-only -q .agents/skills/pr-review .agents/skills/pr-review-fix-loop`）、8,830 行（`git ls-files -z -- .agents/skills/pr-review/tests .agents/skills/pr-review-fix-loop/tests | xargs -0 cat | wc -l`）。後値と検証ログは、実施後に記録する。
