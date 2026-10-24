# Issue #233: スキルと tests/skills のテスト削減設計

> 状態: draft。管理先: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/233 。対象ブランチ: `feat/issue-233-skill-tests`。
>
> 実行許可: 利用者の「`$issue-to-pr #233 --merge`」（2026-10-24）。これは実装、検証、commit、push、PR 作成、および指定されたレビュー修正ループで条件を満たした場合のマージの許可であり、本書の内容承認を意味しない。

## 目的と入力

親 #228 の「利用者の決定」と「削除と採用の基準」、`main` の `AGENTS.md`「テストの採用基準」を使い、#233 担当範囲のテストを F・F∩S・L・S・D・撤去・迷いに棚卸しする。F（F∩S を除く）、L、D の余り、使われなくなった経路のテストだけを削除し、S と F∩S の守りを維持する。件数を合わせるために S を消さない。

先行 #229 は `state_reason=completed` で close、PR #240 は `main` にマージ済み。作業開始時の `origin/main` は `ad89c150bc9a269921088ee63c1ccbd109e93b16`。対象の基準値は 471 件、5,906 行（本 worktree の `pytest --collect-only` と `git ls-files` で計測）。実行テストは 470 passed、1 skipped、終了コード 0。

## 範囲と制約

- 編集可能: #233 に列挙された 10 スキルの `tests/` 全体と `tests/skills/` 全体。使われなくなった経路の撤去を根拠付きで行う場合に限り、同じ 10 スキルのコード・`SKILL.md`・`references/` と、撤去した経路を説明する `README.md`・`.devcontainer/README.md`・`docs/` の行。
- 編集禁止: `pr-review`、`pr-review-fix-loop`、`review-fix-planning`、`review-verify` のコードとテスト、スキルの `evals/`、`.claude/skills/` の symlink、`tools/test_support/`、ルート `conftest.py`、`pyproject.toml`、`.devcontainer/run-tests.bash`、`README.md` の「テスト」、`AGENTS.md`、ほかの子 Issue の担当領域。
- `resolve_issue.py`、`implement_task.py`、`task_watch.py` などの入出力と終了コードを保つ。コードの変更は呼び出し元が無い経路を実証できた場合の撤去に限定する。
- テスト関数または同一理由の parametrize 群を棚卸し表の単位とする。S の理由には防ぐ損害と重さを記し、D には代表を記す。迷いは残す。
- 複数の担当で同じ構文・操作範囲の意味が変わらないか統合時に点検する。高い守りを代表へ絞った箇所は、`/tmp` の `mktemp -d` に置いた使い捨てコピーの処理を一時的に壊し、残したテストが失敗することを確かめる。

## 推奨案と決定記録

| 決定 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-1 | テスト関数と理由が共通の parametrize 群を単位に分類し、S の代表のみ残す | ファイルごとの一括削除、件数目標からの逆算 | 守りを失わず、#228 の棚卸し条件を満たせる | #228 の利用者決定。S か L か決められないものは残して「迷い」と記す |
| D-2 | 既存のコード経路は、使用終了の証拠がそろうまで維持する | ワールド保護の旧経路を同時に撤去 | `README.md` と現行 cleanup 手順が、古い checkout から更新する際の保全を説明している。旧 checkout が全て無いとは確認できない | #228 の決定 5 は、未使用を確かめたときだけ撤去を許す |
| D-3 | テストの共通 fixture は、残る S が使うものを維持し、削除したテスト専用のものを消す | 全 fixture を先に整理する | テストの安全な削減と担当領域の境界を守る。`tools/test_support/` は #236 の担当 | #233 の範囲と禁止 |
| D-4 | 実装は既定の `self` を適用する。独立したファイル群を Task に分け、統合担当が条件単位で確認する | 一括で同時変更する | `implement_task.py check` が `self: true`、`agents: [self]` を返した。別ファイルの独立作業は Task ごとにレビューできる | 雛形・個人設定の既定の適用であり、利用者の担当指定ではない |
| D-5 | PR 後は `--merge` でレビュー修正ループを開始する。サイクル上限 3、レビュアーと修正担当は `loop.py check-options` の既定を適用する | PR 作成で終了 | 利用者が `--merge` を明示した。既定の `max_cycles: 3`、inspect は `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、fix の implement は `claude-opus`、self-review と fix-check は `self` | 利用者の明示指示。これらの値は利用者指定ではない。ループの停止条件は同スキルに従う |
| D-6 | 非 S のテストを新規作成しない。削除後は領域・全体の検証と構造確認を行う | 現在値を写す固定値テストで削減量を監視する | 固定値の検査自体が F となり、採用基準に反する | #228 と `AGENTS.md` の採用基準 |

## 受け入れ条件と検証

1. 棚卸し表が対象のすべてのテスト関数・同一理由の parametrize 群を網羅し、分類と理由、S の重さ、D の代表を示す。
2. F（F∩S を除く）・L・D の余りと、それだけが使う fixture・補助が消えている。残した S は、拒否例と正しく通る例が対になる。
3. 10 スキルと `tests/skills/` の既存 S/F∩S が通る。高い守りを代表に絞った箇所は、使い捨てコピーを一時的に壊したときに失敗する。
4. コミット済みの状態で、#233 に記された領域の収集件数・テスト行数を前後で測り、結果を本書と #233 に記録する。
5. `README.md` の「テスト」にあるリポジトリ全体の 3 入口を通す。実装対象外のファイルが変わっていないことを `git diff` で確かめる。

## 棚卸しの表

以下の 3 表群は、対象 18 ファイルの全 254 テスト関数を列挙した。parametrize は同じ理由のケースを 1 行とし、異なる分類が混在する関数はケース群を分けて記す。撤去は、現時点で呼び出し元が無いと実証できた経路が無いため該当なし。表中の「残す」「維持」は実装時に必要なケースへ絞る判断を含み、最終結果は実装後に更新する。


### Issue #233: issue-to-pr の対象 3 ファイルのテスト棚卸し

対象は `.agents/skills/issue-to-pr/tests/` の `test_implement_task.py`、`test_implement_task_run.py`、`test_resolve_issue.py`。`AGENTS.md` と #228 の採用基準を使用した。`parametrize` に異なる守りが混ざる関数は行を分けた。表の「残す」は必要なケースだけを残す提案を含む。S の重さは高・中・低で記した。D の行には残す代表を記した。撤去に該当する経路は、この 3 ファイルでは確認できなかった。

#### test_implement_task.py

| テスト関数・ケース | 分類 | 判断 | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_check_accepts_template_default_self` | D | 消す | 既定 `self` を `check` で読む守りは `test_check_reads_the_real_template` が実際の雛形で代表する。 |
| `test_check_implement_replaces_primary_and_keeps_fallback`：別担当への上書き | S・中 | 残す | `--implement` が別の担当を選ぶと、もっともらしい結果で誤担当の作業を採用する。`claude-opus` 指定を代表にする。 |
| `test_check_implement_replaces_primary_and_keeps_fallback`：fallback・明示 `self` | D・L | 消す | fallback の優先順は `tools/agent_runner/tests/test_config.py` の `test_assignment_override_is_last_and_keeps_explicit_fallback` が代表。明示 `self` を拒否しても設定エラーとして気付け、既定 `self` は `test_check_reads_the_real_template` が守る。 |
| `test_check_personal_config_overrides_template` | D | 消す | 設定の優先順は `tools/agent_runner` の `test_config.py` が実装側で守る。代表は同ファイルの個人設定優先テスト。 |
| `test_check_rejects_invalid_assignment`：`two-primaries` | S・中 | 残す | 複数の一次担当を受け入れると、意図しない担当を起動・採用し得る。単一担当制約の拒否例。 |
| `test_check_rejects_invalid_assignment`：その他 5 ケース | L | 消す | 未知の担当、役割欠落、書き込み・結果形式の不整合は設定読み込みまたは runner 起動で明示的に失敗する。 |
| `test_check_reads_the_real_template` | F∩S・中 | 残す | 実際の雛形の既定値 `self` が変わると、`--implement` 無しで有料 runner を黙って起動し得る。#157 の安全な既定値を守る固定値。 |
| `test_task_result_accepts_each_status_and_null_commit` | L | 消す | 12 組の受理は Pydantic の型・列挙値検証で、破損時は結果解析のエラーになる。 |
| `test_task_result_rejects_commit_that_is_not_a_full_lowercase_sha` | L | 消す | 短縮 SHA 等は Pydantic または後段の HEAD 照合で拒否される。 |
| `test_task_request_accepts_multiline_prompt_and_non_ascii_paths` | L | 消す | JSON/Pydantic の通常の受理確認で、形式の不整合は解析時か担当の初回利用で現れる。実際の prompt 伝達は run 側で扱う。 |
| `test_task_request_rejects_invalid_fields`：`allowed_files` の `/abs/a.py`・`../a.py`・改行 | S・高 | 残す | 監査対象のパスを脱出・偽装できると、担当外ファイルを取り込み得る。絶対、親参照、改行を各 1 件の代表に絞る。 |
| `test_task_request_rejects_invalid_fields`：`allowed_files` の `src/../a.py`・`./a.py`・`src//a.py`・先頭空白・`/` | D | 消す | 正規化されないパスの拒否は上行の代表と `test_directory_entry_matches_by_path_segment` が守る。 |
| `test_task_request_rejects_invalid_fields`：repository・revision・task・prompt・message | L | 消す | 不正な値は Pydantic 検証か後段の checkout・git 操作で明示的に失敗する。 |
| `test_directory_entry_matches_by_path_segment` | S・高 | 残す | `tests/` が `tests_other/` や `tests` に誤一致すると、担当外の変更が許可済みと判定される。正常一致も含む。 |
| `test_exit_code_for_verdicts` | S・中 | 残す | `rejected`・`failed`・`retry` を 0 で返すと、呼び出し元が失敗を成功として進める。成功の 0 も同じテストで守る。 |

#### test_implement_task_run.py

| テスト関数・ケース | 分類 | 判断 | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_agent_commit_is_importable` | D | 消す | 正常な担当 commit の監査・feature への取り込みは `test_accept_fast_forwards_agent_commit` が代表。run が accept 前に feature を動かさない検査は代表へ移す。 |
| `test_uncommitted_changes_matching_report_are_importable_by_helper` | D | 消す | 報告と一致する未 commit 変更を helper が取り込む正常例は `test_accept_commits_uncommitted_changes_with_message` が代表。 |
| `test_uncommitted_report_mismatch_is_rejected`：`unreported-change` | S・高 | 残す | 報告に無いファイルを helper が commit すると、未監査の変更を取り込む。 |
| `test_uncommitted_report_mismatch_is_rejected`：`reported-but-missing` | D | 消す | 実際の変更と報告を集合で照合する同じ守り。代表は同関数の `unreported-change`。 |
| `test_commit_with_leftover_changes_is_rejected` | S・高 | 残す | commit 後に残る未報告変更を成功と扱うと、取り込みや削除でデータを失い得る。 |
| `test_change_outside_allowed_files_is_rejected` | S・高 | 残す | 最終差分にある担当外ファイルを取り込む事故を防ぐ。 |
| `test_intermediate_commit_outside_allowed_files_is_rejected`：`new-file` | S・高 | 残す | 途中の commit にだけ残る担当外ファイルも ff 取り込みで履歴に入る。最終 tree だけの監査への退行を検出する。 |
| `test_intermediate_commit_outside_allowed_files_is_rejected`：`existing-file` | D | 消す | 戻した途中変更の検出は同関数の `new-file` が代表。 |
| `test_intermediate_commit_inside_allowed_files_is_importable` | L | 消す | 許可範囲内の途中 commit を誤拒否すれば明示的な rejected となる。`test_accept_fast_forwards_agent_commit` が取り込みの正常例を担う。 |
| `test_merge_commit_in_range_is_rejected` | S・高 | 残す | merge commit の親の取り方で未監査変更が紛れるのを防ぐ。 |
| `test_commit_not_descending_from_revision_is_rejected` | S・高 | 残す | 別の履歴の commit を feature に取り込む誤操作を防ぐ。 |
| `test_reported_commit_other_than_head_is_rejected` | S・高 | 残す | 報告 SHA と監査した worktree の HEAD が違うまま取り込む事故を防ぐ。 |
| `test_outside_change_is_rejected` | S・高 | 残す | runner worktree の外側に生じた変更を見落として成功報告するのを防ぐ。 |
| `test_blocked_and_needs_context_ask_for_retry`：`BLOCKED` | S・中 | 残す | 作業不能の報告を成功・無変更と誤判定して先へ進むのを防ぐ。 |
| `test_blocked_and_needs_context_ask_for_retry`：`NEEDS_CONTEXT` | D | 消す | 再試行状態の同じ分岐を `BLOCKED` が代表する。 |
| `test_invalid_result_falls_back_to_the_next_candidate` | L | 消す | fallback が働かなくても `assess` の `TaskResult` 再検証で不正 payload の取り込みは拒否され、明示的な失敗になる。payload 検査と fallback は `tools/agent_runner/tests/test_runner.py` の `test_payload_check_refusal_is_invalid_result_and_tries_fallback` が担当する。 |
| `test_invalid_result_fails_when_no_candidate_is_left` | L | 消す | 候補が尽きた場合は runner が明示的な failed を返す。候補数の 2 通りは同じ終了経路。 |
| `test_recorded_invalid_payload_is_rejected_on_reassessment` | S・高 | 残す | 保存済み記録が壊れた後でも、accept 前の再評価で未検証の payload を取り込ませない。 |
| `test_fallback_success_is_assessed_on_its_own_attempt` | S・高 | 残す | 失敗した一次担当の作業領域を成功した代替担当のものと取り違えると、別の変更を採用し得る。 |
| `test_exhausted_fallback_fails` | L | 消す | 全候補失敗は runner の明示的な失敗として現れ、取り込み不可になる。 |
| `test_unconfirmed_stop_fails` | S・高 | 残す | 停止未確認の担当がまだ書き込み中でも成功として取り込む危険を防ぐ。 |
| `test_no_changes` | L | 消す | 無変更を誤って importable としても、helper commit または ff の後段で明示的に失敗する。 |
| `test_self_assignment_is_refused_without_launch` | L | 消す | runner は `self` を外部担当として起動せず、結果 state を `self` にする。ここで拒否を忘れても `assess` が明示的に failed とし、取り込みは進まない。既定 `self` の安全性は `test_check_reads_the_real_template` が守る。 |
| `test_run_refuses_dirty_or_moved_feature_worktree` | L | 消す | run が誤って始まっても `accept` が同じ `check_feature` で dirty・moved を再検査して取り込みを拒否する。破壊的な取り込みの代表は `test_accept_refuses_moved_or_dirty_feature`。 |
| `test_run_refuses_main_checkout` | S・高 | 残す | feature 用の処理を親の main checkout に適用し、main を動かす事故を防ぐ。 |
| `test_non_ascii_paths_and_prompt_round_trip` | S・中 | 残す | prompt の内容が静かに欠落・変形すると担当が別の作業をしても、許可範囲内なら気付けない。 |
| `test_rename_counts_both_paths` | S・高 | 残す | rename の移動元・先の双方を監査し、担当外への移動を拒否する。内側への移動の正常例も含む。 |
| `test_ignored_files_do_not_count` | L | 消す | ignored ファイルを差分と誤認すれば明示的な拒否になる。未監査の変更を取り込む方向には進まない。 |
| `test_cli_run_rejects_invalid_request_before_launch` | L | 消す | 不正 JSON の要求は Pydantic の解析エラーとして明示的に停止する。 |
| `test_cli_run_stops_on_unauditable_checkout_without_pruning` | D | 消す | runner 自身も全登録を起動前に監査し、別 worktree を prune しない。代表は `tools/agent_runner/tests/test_checkout_policy.py` の `test_unavailable_registration_blocks_work_without_launch_or_repair`。CLI の理由表示は明示エラー。 |
| `test_accept_fast_forwards_agent_commit` | S・高 | 残す | 監査した SHA だけを feature に ff 取り込みする正常例。拒否だけで通る実装を防ぐ。 |
| `test_accept_commits_uncommitted_changes_with_message` | S・高 | 残す | helper commit が未監査ファイルや別の親を含む、または記録と異なる commit を取り込む事故を防ぐ。 |
| `test_accept_reassesses_current_state` | S・高 | 残す | run 後に worktree が変化しても、古い監査結果のまま取り込む事故を防ぐ。 |
| `test_accept_refuses_moved_or_dirty_feature` | S・高 | 残す | run と accept の間に feature が変わった場合の上書き・別履歴への取り込みを防ぐ。両ケースを残す。 |
| `test_accept_refuses_non_importable` | D | 消す | accept が `assess` をやり直して拒否する守りは、run 後の変更を加える `test_accept_reassesses_current_state` が代表。担当外の判定は `test_change_outside_allowed_files_is_rejected` が担当する。 |
| `test_accept_refuses_range_with_reverted_outside_change` | D | 消す | accept の再評価は `test_accept_reassesses_current_state`、途中履歴の検出は `test_intermediate_commit_outside_allowed_files_is_rejected` がそれぞれ代表。 |
| `test_cleanup_removes_worktree_and_run_dir` | S・高 | 残す | 正常な担当領域だけを外し、取り込んだ feature commit を残す正常例。保持テストが「何も消さない実装」で通るのを防ぐ。 |
| `test_cleanup_retains_dirty_worktree` | S・高 | 残す | 未 commit・未追跡の作業物を cleanup が消すデータ損失を防ぐ。 |
| `test_cleanup_retains_unstopped_or_sensitive_attempt` | S・高 | 残す | 停止未確認の担当領域や秘匿情報のある領域を消すと、実行中の作業・調査用データを失う。両ケースは異なる条件なので残す。 |
| `test_cleanup_removes_worktree_with_ignored_files` | L | 消す | ignored ファイルで cleanup が止まれば保持が結果に出て、後片付けの失敗に気付ける。 |
| `test_cleanup_after_fallback_removes_every_attempt_worktree` | L | 消す | 消し残した worktree は登録と出力ディレクトリに残り、後片付けの失敗として見える。 |
| `test_cli_accept_and_cleanup_exit_codes`：accept 拒否の終了コード | S・中 | 残す | accept が拒否しても CLI が 0 を返すと、呼び出し元が取り込み成功として続ける。成功 cleanup の正常例も同じテストに残す。 |
| `test_cli_accept_and_cleanup_exit_codes`：missing run-dir と cleanup の細部 | L | 消す | 無い記録の読み込みと cleanup の終了・表示は明示的なエラーまたは結果で分かる。上行に必要な正常例以外は削る。 |

#### test_resolve_issue.py

| テスト関数・ケース | 分類 | 判断 | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_resolves_supported_forms_without_changing_git`：3 リポジトリの代表 | F∩S・高 | 残す | 許可する owner/repo の固定値と、`#N` の origin による選択が誤ると別リポジトリで branch/PR を作る。正常な URL・短縮形・origin を各 1 件残す。 |
| `test_resolves_supported_forms_without_changing_git`：表記・空白の追加 6 ケース | D | 消す | 同じリポジトリ解決と read-only の守り。代表は上行の 3 リポジトリ例。 |
| `test_accepts_repo_casing_only_in_response_url` | L | 消す | 大文字小文字だけの違いを誤拒否した場合、Issue 取得が明示的に止まる。 |
| `test_rejects_input_before_looking_up_issue`：対象外 repo・上流 repo・偽 GitHub host | F∩S・高 | 残す | 許可外のリポジトリやホストを先に拒否しないと、別対象の Issue を使って作業を進め得る。上流 `orange3134/resoloop` と偽 host を代表にする。 |
| `test_rejects_input_before_looking_up_issue`：複数 Issue・追加語 | D | 消す | 複数の参照を黙って選ぶ守りは `test_rejects_malformed_arguments_before_looking_up_issue` の `#41 #42 --merge` が代表。 |
| `test_rejects_input_before_looking_up_issue`：残りの不正表記 | L | 消す | 形が合わなければパースまたは `gh issue view` が明示的に失敗する。シェルは介さないので `;` は実行されない。 |
| `test_merge_arguments_are_passed_in_the_written_order`：複数 `--max-cycles`・`--assign` | S・中 | 残す | 値の順序や担当指定を入れ替えると、利用者と違う回数・担当でレビュー修正が進む。 |
| `test_merge_arguments_are_passed_in_the_written_order`：`--merge` の位置・単純な値の追加例 | D | 消す | 同じ引数の受け渡しを上行が守る。 |
| `test_template_and_config_become_absolute_from_the_starting_directory` | S・中 | 残す | 後段の cwd で相対パスを解決すると別設定を読んで、違う担当を起動し得る。 |
| `test_unresolvable_home_is_rejected` | L | 消す | `~user` を展開できなければ例外・設定ファイル未発見で明示的に止まる。 |
| `test_rejects_malformed_arguments_before_looking_up_issue`：`#41 #42 --merge` | S・高 | 残す | 複数 Issue の入力から一方を黙って選ぶと、別 Issue の作業・PR を作る。 |
| `test_rejects_malformed_arguments_before_looking_up_issue`：残りのオプション形式 | L | 消す | 重複・欠値・無効な値はパーサー、`loop.py check-options`、または start が明示的に拒否する。 |
| `test_refused_options_name_the_option` | L | 消す | 理由文の表示と未知オプションとの差は診断文面であり、誤指定は後段でも明示的に拒否される。 |
| `test_implement_is_returned_without_changing_git` | S・中 | 残す | 明示した `--implement` を別担当・`self` に取り違えると、誤った担当を起動・採用する。通常形と `self` の正常例を残す。 |
| `test_rejects_malformed_implement_before_looking_up_issue`：二重指定 | S・中 | 残す | 二重の `--implement` から一方を黙って採ると、意図しない担当を起動する。スペース区切り 1 件を代表にする。 |
| `test_rejects_malformed_implement_before_looking_up_issue`：その他の値・二重指定の別表記 | L・D | 消す | 欠値・不正名はパースまたは `implement_task.py check` が明示的に拒否し、`=` 形式の二重指定は上行の同じ守り。 |
| `test_rejects_unknown_options` | L | 消す | 未知オプションはパーサーの明示エラーになる。 |
| `test_number_with_unusable_origin_stops`：GitLab | F∩S・高 | 残す | `#N` の origin が別ホストでも GitHub と誤認すると、別リポジトリの Issue を選び得る。ホストの境界を代表する。 |
| `test_number_with_unusable_origin_stops`：別 owner/repo・query 付き・origin 無し | L・D | 消す | owner/repo の許可判定は `test_rejects_input_before_looking_up_issue` の上流 repo が代表。query 付き・origin 不在はパース・git の明示エラーになる。 |
| `test_origin_with_credentials_stops_without_printing_them`：GitHub URL | S・高 | 残す | origin に入った資格情報をエラーメッセージへ出す漏えいを防ぐ。 |
| `test_origin_with_credentials_stops_without_printing_them`：GitLab URL | D | 消す | 同じ URL 認証情報の伏せ字処理。代表は上行の GitHub URL。 |
| `test_number_outside_a_checkout_stops` | L | 消す | checkout 外では `git remote get-url` が明示的に失敗する。 |
| `test_rejects_mismatched_or_closed_response`：closed・別番号・別 repo・別 host | S・高 | 残す | GitHub 応答の状態や対象を信用すると、閉じた Issue・別 Issue・別リポジトリで作業を始め得る。各違う判定条件を 1 件残す。 |
| `test_rejects_mismatched_or_closed_response`：URL の他の表記違い | D | 消す | URL が指定先と一致するかの同じ守り。代表は上行の番号・repo・host 不一致。 |
| `test_rejects_malformed_response` | L | 消す | JSON 形式・型・状態名の異常は解析エラーとして明示的に止まる。 |
| `test_reports_gh_failure_without_trying_another_repository` | S・高 | 残す | 404 後に別 repo を推測して再検索すると、もっともらしい別 Issue を選んでしまう。 |
| `test_resolve_then_implement_check` | D | 消す | `--implement` の受け渡しは `test_implement_is_returned_without_changing_git`、担当の検査と既定 `self` は `test_check_implement_replaces_primary_and_keeps_fallback` と `test_check_reads_the_real_template` が代表。 |
| `test_implement_is_returned_separately_from_loop_args` | S・中 | 残す | `--assign implement=` を Plan Task の担当へ混ぜると、別担当が実装する。`--merge --assign implement=self` を代表にする。 |
| `test_resolve_then_check_options` | D | 消す | `loop.py check-options` の許可・拒否は実装側の `.agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py` が代表。こちらは上位層の再検査。 |

#### 残す S・F∩S の守り

- **担当と既定値**: 実雛形の既定 `self`、明示した担当の上書き、複数一次担当の拒否。設定優先順や fallback の一般処理は runner 側のテストを代表にする。
- **担当ファイルと commit 履歴**: パスの脱出と境界、未報告変更、commit 後の残存変更、最終差分と途中 commit、merge commit、別履歴、報告 SHA と HEAD、rename の両端。これらは異なる取得・検査経路で、どれか 1 件だけでは他を守れない。
- **runner 結果**: 別 checkout の変更、BLOCKED の誤成功、保存済み payload の再検証、fallback の作業領域選択、停止未確認、prompt の欠落をそれぞれ守る。runner 内部の payload 検査・監査不能 checkout の拒否は runner 側のテストに任せる。
- **取り込みと後片付け**: 正常 commit と helper commit の取り込み、accept 直前の再評価と feature の dirty・moved、main checkout の拒否、cleanup の正常削除と dirty・停止未確認・秘匿領域の保持、CLI の拒否終了コードを守る。run の dirty・moved 拒否は accept の再検査が代表となる。
- **Issue とオプション**: 許可するリポジトリ、対象外 repo・ホスト、GitHub 応答の Issue 同一性・OPEN、404 後の別 repo 推測禁止、origin 認証情報の伏せ字、複数 Issue・二重 `--implement` の拒否、担当・レビュー修正用オプション・設定パスの受け渡しを守る。

全 70 関数を掲載し、残す提案は 41 関数（一部は `parametrize` の代表ケースだけ）。関数を削る前に移す必要がある検査は `test_agent_commit_is_importable` の「run は accept 前に feature を動かさない」で、`test_accept_fast_forwards_agent_commit` に加える。

#### 注意点

- `allowed_files` は最終 tree、途中の commit、未 commit 差分、rename の両端で守る必要がある。単一の最終差分テストだけにまとめない。
- `run` の判定と `accept` 時の再判定は、間に状態変更が入るので別の守りとして残す。
- `stop_confirmed=False` は成功判定だけでなく cleanup の保持条件にも使う。両方残す。
- テストの一部ケースだけを削る行では、既存の関数を分割・parametrize 縮小してから件数を計測する。`test_check_reads_the_real_template` と `SUPPORTED_REPOSITORIES` の境界は固定値でも削除対象にしない。

### #233 テスト棚卸し: Git ロック復旧とマージ後の片付け

対象: `.agents/skills/stale-git-lock-recovery/tests/` と `.agents/skills/repo-cleanup-after-merge/tests/` の **102 関数**。`AGENTS.md` と #228 の F / F∩S / L / S / D / 撤去を適用した。`S` の理由には守る損害を記し、`D` は代表を明記した。parametrize は関数単位で数えた。`維持` は関数を残す提案、`削除` はテストを消す提案である。2 回目の照合後の内訳は S 54、S（迷い）3、F∩S 4、D 14、L 26、F 1。追跡ファイルと実装は変更していない。

#### stale-git-lock-recovery: `test_stale_git_lock_recovery_contract.py`（50 関数）

| テスト関数 | 分類 | 扱い | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_bash_snippets_do_not_run_destructive_git_commands` | F∩S | 維持 | 実行例の `clean` / `reset --hard` / 強制 checkout を禁止し、利用者の未保存データ消失を防ぐ固定値。 |
| `test_skill_never_removes_the_lock_by_hand` | F∩S | 維持 | 手作業の `rm` が保持者検査を迂回して生きたロックを消す損害を防ぐ。 |
| `test_bash_snippets_do_not_clobber_zsh_special_variables` | L | 削除 | zsh の `path` / `status` 代入は直後に異常やエラーとして現れる。 |
| `test_check_reports_no_lock` | L | 削除 | ロック無しの誤判定は通常の Git 再実行や表示で分かる。 |
| `test_json_object_has_a_fixed_key_set` | F | 削除 | 現在の JSON キー集合を写した固定値で、欠落は利用側の解析エラーになる。 |
| `test_stale_lock_is_detected_then_cleared` | S | 維持 | 保持者がいない場合だけ対象ロックを消せる正常例。保持者拒否を「常に拒否」で満たす退行を防ぐ。 |
| `test_unheld_lock_is_stale_on_the_real_proc` | D | 削除 | 実 `/proc` での正常解放は `test_stale_lock_is_detected_then_cleared` の同じ守りと重なる。 |
| `test_nonzero_byte_lock_is_still_stale_when_unheld` | L | 削除 | 内容量で余計に停止しても、元の Git 操作がロックで失敗して明らかになる。 |
| `test_clear_without_lock_is_a_noop` | L | 削除 | ロック無しの clear の誤動作は通常の再実行で分かり、ここでは別ファイルの保全を検査していない。 |
| `test_non_git_repo_is_a_usage_error` | L | 削除 | Git 管理外の入力は git / helper の明示エラーとなる。 |
| `test_rm_failure_reports_error_without_json` | S | 維持 | 削除に失敗したのに JSON で成功を返すと、残るロックを解消済みと誤報する。 |
| `test_live_holder_blocks_check_and_clear` | S | 維持 | lsof で見える生きた保持者のロックを消して、進行中の Git 操作を壊すことを防ぐ。 |
| `test_proc_scan_finds_holder_when_lsof_is_unavailable` | S | 維持 | lsof 不在時も `/proc` の fd 保持者を見つけ、使用中ロックの削除を防ぐ。 |
| `test_unlistable_git_process_is_an_unknown_holder` | S | 維持 | Git プロセスの fd を読めない場合に stale と誤認して消すことを防ぐ。 |
| `test_unlistable_non_git_process_is_not_a_holder` | L | 削除 | 非 Git プロセスを過大に疑うと clear が止まるだけで明白。 |
| `test_unknown_holder_blocks_clear` | D | 削除 | `/proc` から不在を証明できない場合の拒否は `test_without_proc_lsof_alone_cannot_prove_a_lock_stale` が代表。空の `/proc` fixture は同じ拒否を再確認する。 |
| `test_clear_removes_only_the_symlink_lock_not_its_target` | S | 維持 | symlink の参照先にある利用者ファイルの削除・上書きを防ぐ。 |
| `test_dangling_symlink_lock_is_detected_and_cleared` | L | 削除 | 壊れたリンクの見落としはロックが残り、元の Git 操作が失敗する。 |
| `test_linked_worktree_lock_is_detected_at_its_own_path` | S | 維持 | linked worktree のロックを main 側と取り違えて別のロックを操作する危険を防ぐ。 |
| `test_json_escapes_special_characters_in_path` | L | 削除 | エスケープ不備は JSON パースエラーで分かる。 |
| `test_clear_refuses_force_and_unknown_options` | F∩S | 維持 | `--force` 受け付け禁止は保持者検査を迂回する危険な操作範囲を固定する。未知オプションの部分だけなら L。 |
| `test_git_commit_holding_the_lock_without_an_fd_is_not_stale` | S | 維持 | hook / editor 待ちで fd を閉じた commit の生きたロックを消すと、コミットを壊す。 |
| `test_git_process_inside_the_repository_makes_the_holder_unknown` | S | 維持（縮約） | 同一 worktree 内の fd を閉じた Git を守る。worktree 直下は実 commit の `test_git_commit_holding_the_lock_without_an_fd_is_not_stale` が代表なので、ここは `.git` 内 cwd の 1 値に縮める。 |
| `test_git_process_pointing_at_the_repository_through_its_environment_is_unknown` | S | 維持（縮約） | cwd が外でも `GIT_*` で対象 index に結び付く Git を守る。`GIT_INDEX_FILE` の絶対 / 相対は相対を代表にし、他は異なる変数分岐を維持する。 |
| `test_git_process_pointing_at_the_repository_through_its_options_is_unknown` | S | 維持 | argv の `--git-dir` と `--work-tree` は別の解析分岐。外部 cwd から対象を指す Git を見落としてロックを消す危険があるため、両値を残す。 |
| `test_git_process_with_a_relative_repository_reference_cannot_be_ruled_out` | S | 維持（縮約） | 起動後の cwd から相対 `--git-dir` を確定できず、保持中ロックを消す危険がある。3 値から argv の代表 1 値へ縮める。 |
| `test_git_process_with_an_unreadable_cwd_is_unknown` | S | 維持 | cwd を読めない Git を対象外と断定してロックを消す危険を防ぐ。 |
| `test_unrelated_processes_do_not_block_a_stale_lock` | L | 削除 | 無関係なプロセスで過剰停止しても Git の再実行が失敗して分かる。 |
| `test_git_process_in_a_nested_worktree_or_repository_does_not_block_the_outer_lock` | D | 削除 | 内側ではない `vendor` の Git を unknown とする S 部分は `test_git_process_inside_the_repository_makes_the_holder_unknown` が代表。内側の過剰停止は L。 |
| `test_repo_inside_the_git_dir_is_refused` | S | 維持 | `.git` 内からの指定では worktree の保持者を見落とし得るため、ロック削除前に拒否する。 |
| `test_git_process_in_the_main_worktree_does_not_block_a_linked_worktree_lock` | D | 削除 | linked 側の cwd から保持者を検出する守りは `test_git_process_inside_the_repository_makes_the_holder_unknown` と実 commit が代表。main 側の過剰停止は L。 |
| `test_holder_found_after_an_unknown_process_is_still_present` | L | 削除 | unknown と present はどちらも clear を止めるため、差は表示の精度だけ。 |
| `test_union_keeps_unknown_when_lsof_finds_nothing` | S | 維持 | lsof が空でも `/proc` が不明なら stale と断定せず、ロック削除を止める。 |
| `test_lsof_holder_wins_over_an_unusable_proc` | L | 削除 | present / unknown の優先は表示差で、どちらも削除を止める。 |
| `test_without_proc_lsof_alone_cannot_prove_a_lock_stale` | S | 維持 | `/proc` が使えず lsof が空でも保持者不在とは言えず、clear を拒否する。 |
| `test_inherited_git_environment_does_not_redirect_the_target` | S | 維持 | 呼び出し元の `GIT_*` で別 repository の `index.lock` を削除する事故を防ぐ。 |
| `test_stale_suggestion_is_a_runnable_command_for_paths_with_spaces` | L | 削除 | この fixture の空白パスで引用が壊れると提案コマンドが明示エラーになる。別対象の削除を検査していない。 |
| `test_concurrent_clear_waits_for_the_lock_directory` | S | 維持 | 並列 clear の競合で検査済みとは別のロックを消す危険を防ぐ。 |
| `test_clear_without_flock_removes_nothing` | S | 維持 | 排他ロック取得に失敗した clear が、競合する Git / clear のロックを消すことを防ぐ。 |
| `test_clear_keeps_a_lock_replaced_during_the_check` | S | 維持 | 検査後に差し替えられた新しいロックを消す TOCTOU のデータ損失を防ぐ。 |
| `test_paused_commit_in_a_core_worktree_repository_is_not_stale` | S | 維持 | `core.worktree` が外を指す配置でも一時停止した commit のロックを守る。希少だが別のパス判定。 |
| `test_git_child_of_a_linked_worktree_does_not_block_the_main_lock` | D | 削除 | 絶対 `GIT_DIR` の対象選択は `test_git_process_pointing_at_the_repository_through_its_environment_is_unknown` が代表。linked cwd 自体も unknown とするので、このテスト固有の main 側の過剰停止は L。 |
| `test_submodule_git_dir_is_refused` | D | 削除 | submodule の Git 管理ディレクトリを拒否する守りは `test_repo_inside_the_git_dir_is_refused` が代表。 |
| `test_paused_commit_with_an_external_work_tree_is_not_stale` | D | 削除 | 実 commit の fd 無しロックは `test_git_commit_holding_the_lock_without_an_fd_is_not_stale` が代表。外部 `core.worktree` により cwd と top が異なる場合は `test_paused_commit_in_a_core_worktree_repository_is_not_stale` が代表。 |
| `test_git_started_through_a_symlink_with_another_name_is_detected` | S | 維持 | 別名 symlink で起動した Git の commit 中ロックを非 Git と誤認して消す危険を防ぐ。 |
| `test_git_dir_given_as_a_dot_git_file_is_resolved` | S | 維持 | linked worktree の `.git` ファイルを解決し、その worktree の生きたロックを守る。 |
| `test_zombie_git_process_does_not_block` | D | 削除 | 後半の生存 Git の拒否は `test_git_process_with_an_unreadable_cwd_is_unknown` が代表。zombie による過剰停止は L。 |
| `test_git_process_that_exits_during_the_scan_does_not_block` | L | 削除 | 消えたプロセスを疑っても clear が明示的に止まるだけ。 |
| `test_work_tree_of_a_process_with_an_absolute_git_dir_is_not_used` | L | 削除 | この fixture の linked cwd は単独で linked 側を unknown にする。`GIT_WORK_TREE` の優先を誤っても main 側が過剰停止するだけ。 |
| `test_hook_child_in_another_repository_does_not_block` | D | 削除 | 相対 `GIT_INDEX_FILE` で対象を認識する守りは `test_git_process_pointing_at_the_repository_through_its_environment_is_unknown` が代表。他 repository での過剰停止は L。 |

#### stale-git-lock-recovery: `test_ff_merge_keep_untracked.py`（30 関数）

| テスト関数 | 分類 | 扱い | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_fast_forwards_and_restores_every_conflicting_file` | S | 維持 | 退避した未追跡ファイル・symlink・mode を fast-forward 後に復元し、利用者データを失わない。 |
| `test_failed_fast_forward_restores_everything_and_keeps_head` | S | 維持 | merge 失敗時に退避ファイルを戻し、HEAD とローカル編集を残す。 |
| `test_not_a_fast_forward_changes_nothing` | S | 維持 | 非 fast-forward を通常 merge / 破壊的更新で進める事故を防ぐ。 |
| `test_backup_failure_changes_nothing` | S | 維持 | 退避先を作れないまま merge して未追跡ファイルを失う危険を防ぐ。 |
| `test_without_conflicts_it_only_fast_forwards` | L | 削除 | 衝突なしの失敗は Git コマンドのエラーで分かる。正常例は最初のテストにある。 |
| `test_already_up_to_date_is_a_noop` | L | 削除 | 再実行時の不要なエラーはその場で分かり、データ保全の独自の守りを検査しない。 |
| `test_inherited_git_dir_does_not_redirect_the_target` | S | 維持 | 継承した `GIT_DIR` / `GIT_WORK_TREE` により別 repository を更新する事故を防ぐ。 |
| `test_usage_errors_change_nothing` | S | 維持（縮約） | `--force` を受け入れて破壊的更新する危険だけ残す。他の欠落引数・未知 ref は解析 / Git の明示エラーで L。 |
| `test_outside_a_work_tree_is_a_usage_error` | L | 削除 | 管理外ディレクトリは Git の明示エラーで分かる。 |
| `test_ignored_file_on_an_added_path_is_kept` | S | 維持 | Git が無警告で上書きする ignored ファイルの内容を保つ。 |
| `test_files_under_a_directory_or_a_symlink_named_like_an_added_path_are_left_alone` | D | 削除 | directory / symlink が追加パスを塞ぐ守りは `test_ignored_content_that_could_not_be_put_back_stops_the_run` の同じ 2 分岐が代表。 |
| `test_interrupted_run_restores_files_and_reports_head` | S | 維持 | シグナル後の後片付け漏れで退避ファイルが消える、また HEAD の進みを誤報する回帰を防ぐ。 |
| `test_failure_to_list_candidates_changes_nothing` | S | 維持 | 衝突候補を列挙できないまま merge して ignored ファイルを無警告で上書きする危険を防ぐ。 |
| `test_ignored_content_that_could_not_be_put_back_stops_the_run` | S | 維持 | 復元先が塞がる ignored ファイル / directory / symlink を、先に merge して失う危険を防ぐ。 |
| `test_tracked_paths_that_change_between_file_and_directory_still_fast_forward` | L | 削除 | 追跡済みの file / directory の更新失敗は Git のエラーで分かり、未追跡データを置かない。 |
| `test_candidates_do_not_depend_on_the_callers_locale` | S | 維持 | locale 差で候補を落とすと ignored ファイルが Git に無警告で上書きされる。 |
| `test_untracked_nested_repository_that_files_are_added_into_stops_the_run` | S | 維持 | 未追跡の入れ子 repository 内の作業ファイルが上流により上書きされる危険を防ぐ。 |
| `test_added_submodule_over_an_existing_clone_still_fast_forwards` | S | 維持 | 既存 clone を丸ごと置換せず、その未追跡ファイルを残す正常例。 |
| `test_tracked_symlink_replaced_by_a_directory_still_fast_forwards` | L | 削除 | 追跡済み symlink の置換失敗は Git のエラーで分かり、未追跡内容を置かない。 |
| `test_ignored_file_where_a_tracked_directory_was_stops_the_run` | S | 維持 | index 上は directory でも実体が ignored ファイルになった場合の無警告削除を防ぐ。 |
| `test_untracked_file_where_a_submodule_is_added_stops_the_run` | D | 削除 | 追加 gitlink の位置にファイルがあると拒否する守りは `test_submodule_hidden_by_its_ignore_setting_is_still_seen` が代表。設定違いを網羅しない。 |
| `test_unborn_branch_is_refused_with_a_clear_message` | L | 削除 | unborn HEAD では merge 自体が明示エラーになり、ここで検査するのは文面と元ファイルの残存。 |
| `test_submodule_hidden_by_its_ignore_setting_is_still_seen` | S | 維持 | `.gitmodules` の ignore に隠れた gitlink 追加で ignored ファイルを失う危険を防ぐ。 |
| `test_ignored_file_in_a_submodule_turned_into_a_directory_stops_the_run` | S | 維持 | submodule を通常 directory に変える際に checkout 内の ignored log を上書きする危険を防ぐ。 |
| `test_ignored_file_on_the_way_inside_a_submodule_turned_into_a_directory_stops_the_run` | S | 維持 | submodule 内で追加先の途中にある ignored ファイルを削除する危険を防ぐ。 |
| `test_submodule_turned_into_a_file_stops_the_run_while_its_checkout_has_content` | S | 維持 | gitlink を file に変えるとき、checkout 全体とその未追跡内容を消す危険を防ぐ。 |
| `test_submodule_turned_into_a_file_fast_forwards_when_its_checkout_is_empty` | L | 削除 | 空 checkout での過剰停止は明示エラーとして分かる。正常更新の代表は別にある。 |
| `test_submodule_inside_a_directory_replaced_by_a_file_stops_the_run` | S | 維持 | 親 directory が file へ変わる際に子 submodule の未追跡内容を消す危険を防ぐ。 |
| `test_empty_submodule_inside_a_directory_replaced_by_a_file_fast_forwards` | L | 削除 | 空 submodule の過剰停止は明示エラーとなり、データ消失を検査しない。 |
| `test_failing_directory_listing_stops_the_run` | S | 維持 | directory 内の内容を確認できない場合に更新を進めると未追跡データを失い得る。 |

#### repo-cleanup-after-merge: `test_repo_cleanup_after_merge_contract.py`（2 関数）

| テスト関数 | 分類 | 扱い | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_related_skills_exist` | L | 削除 | リンク切れはスキル利用時や `scripts/check-layout.sh` で明らかになる。 |
| `test_evals_have_valid_structure_and_existing_files` | L | 削除 | JSON の構文・型・参照先の不備は読み込み時の例外 / ファイル不在で分かる。 |

#### repo-cleanup-after-merge: `test_detached_update.py`（20 関数）

| テスト関数 | 分類 | 扱い | 具体的な理由・D の代表 |
| --- | --- | --- | --- |
| `test_updates_to_detached_origin_main_without_changing_local_refs` | S | 維持 | 更新時にローカル main / 作業 branch を作成・移動すると利用者の ref と履歴が変わる。 |
| `test_repeated_cleanup_follows_remote_advancement_without_creating_main` | D | 削除 | detached 更新と main を作らない守りは `test_updates_to_detached_origin_main_without_changing_local_refs` が代表。 |
| `test_existing_main_is_retained_without_ref_or_reflog_updates` | S | 維持 | 既存 main の commit / reflog を動かすと利用者が持つ履歴を失う。 |
| `test_main_held_by_another_worktree_does_not_block_or_mutate_that_tree` | S | 維持 | 別 worktree の main と未保存・ignored 内容を更新元として扱う事故を防ぐ。 |
| `test_invocation_from_linked_project_targets_main_root_not_callers_feature` | S | 維持 | linked project からの実行で呼び出し元 feature の HEAD / refs を動かす事故を防ぐ。 |
| `test_branch_deletion_from_linked_project_uses_updated_main_head` | L | 削除 | 古い HEAD を基準にしたときは merged branch の削除を Git が拒否し、明示エラーになる。別 worktree の保護は直前のテストが担う。 |
| `test_branch_deletion_refuses_a_branch_not_merged_into_origin_main` | S | 維持 | 未マージ branch を `-D` で消して利用者の commit を失う危険を防ぐ。 |
| `test_final_status_from_linked_project_reports_main_not_dirty_caller` | S | 維持 | caller の dirty 状態を main の状態として報告すると、後続の片付け判断を誤る。 |
| `test_unclean_or_unreadable_main_tree_stops_before_checkout_and_branch_deletion` | S | 維持 | main の dirty / 読取失敗を無視した checkout と branch 削除によるデータ・履歴損失を防ぐ。 |
| `test_dirty_main_tree_is_rechecked_even_when_callers_linked_tree_is_clean` | D | 削除 | main の dirty 拒否は `test_unclean_or_unreadable_main_tree_stops_before_checkout_and_branch_deletion`、caller から main を選ぶ守りは `test_invocation_from_linked_project_targets_main_root_not_callers_feature` が代表。 |
| `test_ignored_file_collision_aborts_without_losing_data_or_branch_refs` | S | 維持 | Git の checkout が無警告で上書きし得る ignored な利用者ファイルを守る。 |
| `test_steps_8_and_11_stop_when_main_root_is_unset_instead_of_using_callers_repo` | S | 維持 | `MAIN_ROOT` 空で別 repository の branch を削除・誤報する事故を防ぐ。 |
| `test_step11_reports_main_root_even_when_called_from_another_repo` | D | 削除 | 正しい報告対象は `test_final_status_from_linked_project_reports_main_not_dirty_caller` が代表。別 repository の誤削除は `test_steps_8_and_11_stop_when_main_root_is_unset_instead_of_using_callers_repo` が守る。 |
| `test_step8_recheck_for_not_fully_merged_discriminates_merge_state` | S | 維持 | `branch -d` の拒否後に `-D` へ進む前の祖先確認を誤ると未マージ commit を消す。 |
| `test_cleanup_keeps_the_forks_local_main_out_of_deletion_candidates` | F∩S | 維持 | fork のローカル main を削除候補から外す固定値で、利用者所有の基準 branch 消失を防ぐ。 |
| `test_checkout_lock_failure_stops_before_subsequent_branch_deletion` | S | 維持 | checkout が index.lock で失敗した後、旧 HEAD のまま branch 削除へ進む損害を防ぐ。 |
| `test_tracked_world_deletion_stops_without_mutating_any_local_state` | S（迷い） | 維持 | 5 領域に追跡ファイルが残る旧 HEAD を更新すると clean なファイルも削除される。経路の撤去可否は未確定。 |
| `test_world_source_rename_outside_protected_roots_is_treated_as_deletion` | S（迷い） | 維持 | rename 検出が旧パスの削除を隠すと追跡中のワールド source を失う。経路の撤去可否は未確定。 |
| `test_deleted_path_diff_error_stops_before_checkout_or_branch_deletion` | S（迷い） | 維持 | 削除パス照会の失敗を空集合として扱うと、保護領域の追跡ファイルを削除し得る。経路の撤去可否は未確定。 |
| `test_protected_world_source_modification_still_allows_normal_update` | L | 削除 | 削除のない変更を過剰に拒否しても、更新の明示エラーとして分かる。通常更新の正常例は先頭のテストにある。 |

#### ワールド保護経路の撤去判断

**撤去と判定できない。** この worktree と `git worktree list` に見える checkout は #58 のマージ後のコミットを指す。一方、`README.md` の「追跡解除コミットを取り込む」は旧 checkout での追跡ファイル削除と 5 領域の保全を現行手順として明記している。見えている worktree だけでは、別ホスト・別 checkout・古い HEAD を保持した作業場所や、現在のスキルを旧 HEAD に対して使う経路の不存在を証明できない。`SKILL.md` の手順 7 には保護判定の呼び出しが残り、削除すると `--no-overwrite-ignore` でも追跡済みの clean なワールドファイルが消える。旧 checkout 自身の旧スキルは保護を持たないため README の初回移行手順も引き続き必要。呼び出し元・旧 checkout の不存在を別途確認できるまでは、コードと上記 3 テストを残す。

#### 維持する高リスク S の代表群

| 守り | 主な代表 | 分けて残す理由 |
| --- | --- | --- |
| ロック保持者の検出 | `test_live_holder_blocks_check_and_clear`、`test_proc_scan_finds_holder_when_lsof_is_unavailable`、`test_git_commit_holding_the_lock_without_an_fd_is_not_stale` | lsof の fd、lsof 不在時の `/proc` fd、Git が fd を閉じた hook / editor 待ちは別の検出経路。 |
| 判定不能なら削除しない | `test_unlistable_git_process_is_an_unknown_holder`、`test_union_keeps_unknown_when_lsof_finds_nothing`、`test_without_proc_lsof_alone_cannot_prove_a_lock_stale` | 個別プロセスの読取不可、lsof / proc 結合、proc 自体の不可用性は別の分岐。 |
| ロックの対象・競合 | `test_clear_removes_only_the_symlink_lock_not_its_target`、`test_inherited_git_environment_does_not_redirect_the_target`、`test_concurrent_clear_waits_for_the_lock_directory`、`test_clear_keeps_a_lock_replaced_during_the_check` | symlink 参照先、別 repository、並列 clear、検査後の差し替えは損害の原因が異なる。 |
| ff merge の退避と停止 | `test_fast_forwards_and_restores_every_conflicting_file`、`test_failed_fast_forward_restores_everything_and_keeps_head`、`test_interrupted_run_restores_files_and_reports_head`、`test_failure_to_list_candidates_changes_nothing` | 正常、Git 失敗、シグナル、候補列挙失敗でそれぞれ復元 / 停止の位置が異なる。 |
| Git が無警告で消す衝突 | `test_ignored_file_on_an_added_path_is_kept`、`test_ignored_content_that_could_not_be_put_back_stops_the_run`、`test_untracked_nested_repository_that_files_are_added_into_stops_the_run`、`test_submodule_turned_into_a_file_stops_the_run_while_its_checkout_has_content` | 単一 ignored ファイルは退避可能。directory / symlink、入れ子 repo、submodule checkout は元位置に復元できず先に拒否が必要。 |
| checkout と branch の保護 | `test_updates_to_detached_origin_main_without_changing_local_refs`、`test_existing_main_is_retained_without_ref_or_reflog_updates`、`test_branch_deletion_refuses_a_branch_not_merged_into_origin_main`、`test_ignored_file_collision_aborts_without_losing_data_or_branch_refs` | 新規 main、既存 main の改変、未マージ branch 削除、ignored ファイルの上書きを別々に防ぐ。 |
| 旧 HEAD のワールド保護 | `test_tracked_world_deletion_stops_without_mutating_any_local_state`、`test_world_source_rename_outside_protected_roots_is_treated_as_deletion`、`test_deleted_path_diff_error_stops_before_checkout_or_branch_deletion` | 追跡ファイルの削除、rename に隠れた削除、判定失敗後の続行を個別に防ぐ。経路の撤去可否は未確定。 |

#### 留意点

- `test_usage_errors_change_nothing` は安全な `--force` 拒否と L の一般的な解析エラーが混在する。維持するなら `--force` 場面に縮める。
- `test_rm_failure_reports_error_without_json` は権限に依存する fixture なので、root 実行でも削除失敗を確実に再現できるか確認する。判定自体は「失敗を成功と報告しない」S。
- `test_deleted_path_diff_error_stops_before_checkout_or_branch_deletion` はワールド保護を維持する場合にだけ残るテストで、撤去を判断するなら README と SKILL.md の該当呼び出し・説明も合わせて扱う。

### Issue #233: 指定範囲のテスト棚卸し

基準: `AGENTS.md`「テストの採用基準」、#228「利用者の決定」「削除と採用の基準」、#233「手がかり」。対象は本表に載せた 10 ファイルの **82 関数**。parametrize の全 variant は 1 行として扱う。`残す` は既存テストの採用、`消す` はテストの削除を提案する。D の「代表」は同じ守りを残す関数。ここでは追跡ファイルを変更していない。

#### `tests/skills`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_skill_frontmatter.py::test_frontmatter_is_valid_for_every_runtime` | F∩S | 残す。ただし権限に関係しない名前・説明文の形は削る | `allowed-tools` の型が変わると実行権限の解釈が黙って変わり、意図外のツールを使いうる（高）。権限値の固定だけを残す。全 skill の parametrize は 1 行。 |
| `test_skill_frontmatter.py::test_every_skill_directory_has_a_skill_file` | L | 消す | `SKILL.md` が無ければ当該スキルを使う最初の操作でファイル不在が分かる。 |
| `test_skill_packages.py::test_references_and_links_resolve` | L | 消す | リンク先が無ければ開く際にファイル不在として明らかになる。 |
| `test_skill_packages.py::test_execution_guidance_guards_cover_positive_and_negative_fixtures` | S | 残す | 検出器が誤って無条件に偽を返すと、禁止した Blender MCP・他エンジンへの誘導を見逃す。外部の処理経路へ作業を出す損害を防ぐ（高）。許容文の例もあり、何でも拒否する検出器は通らない。 |
| `test_skill_packages.py::test_no_positive_execution_guidance_in_skills_or_shared_references` | F∩S | 残す | スキル本文・参照文書に実行可能な Blender MCP・他エンジンへの誘導が混じると、定めた ResoLoop の操作範囲外へ作業を出しうる（高）。固定するのは文面全体ではなく危険な操作の有無。 |
| `test_skill_packages.py::test_provenance_license_and_document_coverage` | F∩S | 残す。ただし存在・一般的な形式の確認は削る | 取り込んだ資料の source commit・帰属・対象の一覧は凍結した取り込み履歴。誤った由来をそれらしく記録する損害を防ぐ（中）。出力パスの存在は L。 |

#### `monitoring-long-tasks/tests/test_task_watch_core.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_exit_is_completed_only_with_zero_and_declared_result` | S | 残す | exit 0 でも宣言済み結果が無い、または非 0 なのに `completed` と記録すると、未完了を成功として報告する（中）。正常完了の例も含む。 |
| `test_exit_without_declared_result_is_judged_by_exit_code` | D | 消す | exit code による成功・未完了の区別は `test_exit_is_completed_only_with_zero_and_declared_result` が代表。宣言結果なしの正常例は同関数の正常例と別の守りにならない。 |
| `test_safety_failure_precedes_deadline_and_other_reasons` | S | 残す | 安全失敗を期限超過などへ置き換えると、失敗の種類が最終記録から失われる（中）。 |
| `test_deadline_stops_even_while_progressing` | S | 残す | 進捗があるだけで期限を無視すると、宣言した上限を越えて対象が動き続ける（中）。 |
| `test_repeated_failure_stops_at_the_declared_count` | S | 残す | 同じ失敗が所定回数に達しても続行すると、失敗を繰り返す対象が期限まで動き続ける（中）。閾値の前の続行も確かめる。 |
| `test_new_investigation_in_reserve_is_stopped` | S | 残す | 保存用の予約時間に新たな調査を始めると、保存時間を使い切り途中結果を失いうる（高）。通常の finalize の例も含む。 |
| `test_no_progress_applies_only_before_research_deadline` | S | 残す | 無進捗を見逃して続行するか、予約時間に誤って停止すると、期限・保存の判断を誤る（中）。 |
| `test_safety_failure_recorded_before_exit_is_not_completed` | S | 残す | 終了コードと結果だけを見ると、記録済みの安全失敗を成功と報告する（中）。 |
| `test_undeclared_stop_holds_instead_of_stopping` | D | 消す | `stop=none` で hold を記録し実 signal を送らない守りは、`test_undeclared_stop_never_signals` が実プロセス・event の両方で代表する。 |
| `test_policy_rejects_values_outside_the_declared_ranges` | S（L 混在） | 残す。ただし `reserve_seconds >= deadline_seconds` の拒否に絞る | 予約時間が期限以上の指定を通すと、研究時間が 0 以下になって worker に直ちに finalize を求め、調査不足の成果を `completed` と記録しうる（中）。他の単純な範囲エラーは L。`stop=KILL` は CLI も拒否し、Policy を通しても `_stop_target` は SIGKILL にしないので、以前の強制停止という説明は誤りだった。 |
| `test_progress_reader_counts_only_new_items_and_complete_lines` | S | 残す | heartbeat・重複・未完了行を新しい進捗と数えると、無進捗の対象を進捗ありとして走らせ続ける（中）。完成した行を数える正常例もある。 |
| `test_records_before_the_reserve_offset_are_not_investigation` | S | 残す | finalize 要求直後の保存中に届いた記録を新規調査と誤認し停止すると、途中結果が失われうる（高）。実際の新規項目は止める例もある。 |
| `test_line_longer_than_read_limit_is_skipped_and_later_records_are_read` | S | 残す | 長い 1 行で読み取りが止まり、その後の安全失敗を取り込まなければ、失敗を見逃して続行する（高）。 |
| `test_backlog_beyond_read_limit_is_read_in_one_poll` | D | 消す | 読取上限を越えた後方の記録まで進む同じ `read_progress` のループは `test_line_longer_than_read_limit_is_skipped_and_later_records_are_read` が安全失敗の記録で代表する。件数の全量照合はこの守りを増やさない。 |
| `test_failures_are_counted_per_signature_and_first_safety_is_kept` | S | 残す | 署名別の失敗回数を混同すると誤停止・停止漏れになり、安全失敗の先頭記録を失うと調査対象を取り違える（中）。 |
| `test_missing_or_special_progress_file_is_not_progress` | L | 消す | 不在・FIFO の入力で読み取りが止まる、または無進捗になる場合は監視の停止・明白な停滞として表れる。このテストは危険な成功判定を確かめていない。 |

#### `monitoring-long-tasks/tests/test_task_watch_process.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_progressing_worker_completes_without_stop` | D | 消す | exit 0・結果ありの完了判定は core の `test_exit_is_completed_only_with_zero_and_declared_result`、実プロセスの結果ありの陽性例は `test_item_written_right_after_finalize_request_is_within_grace` が代表する。 |
| `test_heartbeat_only_worker_is_stopped_for_no_progress` | S | 残す | heartbeat を実進捗と誤認すると worker が走り続け、`confirmed` だけ偽装しても実 PID の生存確認で検出する（中）。実停止の代表。 |
| `test_repeated_failure_stops_worker` | D | 消す | 判定は core の `test_repeated_failure_stops_at_the_declared_count`、記録数は `test_failures_are_counted_per_signature_and_first_safety_is_kept`、実 signal は process の `test_heartbeat_only_worker_is_stopped_for_no_progress` が代表。 |
| `test_safety_failure_stops_at_first_record` | D | 消す | safety の優先判定は core の `test_safety_failure_precedes_deadline_and_other_reasons`、記録の読取は `test_failures_are_counted_per_signature_and_first_safety_is_kept`、実 signal は `test_heartbeat_only_worker_is_stopped_for_no_progress` が代表。 |
| `test_deadline_stops_even_while_progressing` | D | 消す | 期限判定は core の `test_deadline_stops_even_while_progressing`、実 signal は process の `test_heartbeat_only_worker_is_stopped_for_no_progress` が代表。 |
| `test_unstoppable_worker_is_held_and_left_running` | S | 残す | TERM を無視する worker を停止済みと誤報すると、残留プロセスを見逃して作業を終えてしまう（高）。PID の生存と state の保持も確かめる。 |
| `test_escalate_kill_confirms_stop_of_term_ignoring_worker` | S | 残す | kill へ段階を進めた後、実際に生存しているのに `confirmed=true` とする誤報を防ぐ（高）。 |
| `test_undeclared_stop_never_signals` | S | 残す | 宣言されていない停止 signal を実 worker に送ることを防ぐ（高）。core の決定だけでは signal 配送の回帰は検出できない。 |
| `test_partial_result_survives_stop_for_investigation_in_reserve` | D | 消す | 予約中の新規調査の停止判定は core の `test_new_investigation_in_reserve_is_stopped`、実 signal は `test_heartbeat_only_worker_is_stopped_for_no_progress`、同じ `_Watch.finish()` による途中成果の final への回収は `test_records_written_by_the_group_after_exit_reach_the_final` が代表する。 |
| `test_finalize_aware_worker_saves_and_completes` | D | 消す | finalize 要求後に worker が結果を保存し `completed` になる陽性例は、猶予中の項目も加えた `test_item_written_right_after_finalize_request_is_within_grace` が代表する。 |
| `test_item_written_right_after_finalize_request_is_within_grace` | S | 残す | finalize 要求直後の猶予中の記録を違反扱いすると、成果保存中の worker を止めて結果を失う（高）。 |
| `test_safety_failure_then_exit_is_not_completed` | D | 消す | 終了との競合を含む safety の非完了は core の `test_safety_failure_recorded_before_exit_is_not_completed` と process の `test_records_written_by_the_group_after_exit_reach_the_final` が代表。 |
| `test_records_written_while_stopping_reach_the_final` | D | 消す | stop 後も同じ `_Watch.finish()` が `observe()` を再実行する。最後の safety・saved を final に取り込む守りは `test_records_written_by_the_group_after_exit_reach_the_final` が代表する。 |
| `test_records_written_by_the_group_after_exit_reach_the_final` | S | 残す | leader の exit 0 後に child が記録した safety を読み損ねると、失敗を成功と報告する（高）。 |
| `test_processes_left_in_the_group_after_exit_are_held` | S | 残す | leader の終了だけで完了扱いすると、child が生きたまま controller が作業を終える（高）。 |
| `test_status_sees_the_group_after_the_watcher_is_killed` | S | 残す | watcher が SIGKILL された後、child の生存を見落とすと、止まっていない対象を停止済みとして扱う（高）。 |
| `test_stop_refuses_unrelated_and_caller_pids` | S | 残す | stale・再利用・caller の PID に signal を送ると無関係のプロセスを破壊する（高）。3 ケースは同じ identity 検証の代表群。通常の停止陽性例は `test_operator_stop_confirms_and_reports_operator`。 |
| `test_operator_stop_confirms_and_reports_operator` | S | 残す | operator 停止の通知だけで終了せず、実際に watcher が退出して確認済みと記録することを確かめる。虚偽の停止確認を防ぐ（高）。 |
| `test_relative_state_dir_round_trip` | S | 残す | 相対 state path を別の cwd 基準で解決すると、別 watch の状態を読んだり対象を止めたりする（高）。status・stop の対象が同じ絶対パスになることを確かめる。 |
| `test_status_of_finished_run_reports_final_and_dead_processes` | L | 消す | 終了済みを生存中と返す誤りは controller の待機・状態確認が終わらないという明らかな異常になる。正常完了の記録自体は `test_progressing_worker_completes_without_stop` が確かめる。 |
| `test_launch_failure_is_reported_as_incomplete` | S | 残す | 起動できない CLI を `completed` と最終報告すると、何も実行していないのに成功が残る（中）。 |
| `test_invalid_arguments_exit_2_without_creating_state` | S（L 混在） | 残す。ただし既存 state 保護に絞る | 誤った引数が既存の state directory を上書きすると監視記録を失う（高）。新規 state 不作成と終了コードだけは argparse/pydantic の L なので削る。 |

#### `pi-model-name/tests/test_pi_model_name_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_prints_runtime_model` | S | 残す | 現在の provider/model と違う名前をもっともらしく表示するとレビュー記録を誤帰属する（中）。正しい runtime の陽性例。 |
| `test_model_only_flag` | D | 消す | model だけの表示は `test_crosschecked_text_modes` の `--model` variant が代表。 |
| `test_strict_fails_closed_without_runtime` | S | 残す | runtime 不明なのに履歴から正式なモデル名を推測すると、レビュー担当を誤帰属する（中）。正常例は `test_prints_runtime_model`。 |
| `test_history_allowed_only_with_flag` | S | 残す | 明示 flag なしで履歴を正式なモデル名として返すと、古いモデルを現在の担当として記録する（中）。flag ありの陽性例も含む。 |
| `test_history_prefers_explicit_file_over_runtime_file` | S | 残す | 明示された session と別ファイルから取得すると、別の実行のモデルを現在の担当として記録する（中）。 |
| `test_history_uses_explicit_file_without_runtime_file` | L | 消す | 明示ファイルしかない場面でそれを読めなければ、出力がなく非 0 で失敗する。履歴を読む正常経路は `test_history_allowed_only_with_flag` でも実行する。 |
| `test_history_uses_subagent_file_without_runtime_file` | L | 消す | この入力には子エージェントの session 以外の候補が無い。読取が壊れれば出力なしの非 0 となり、履歴を読む陽性例は `test_history_allowed_only_with_flag` に残る。 |
| `test_history_does_not_fall_back_from_unreadable_explicit_file` | S | 残す | 明示したファイルが読めない時に環境側へ無言で fallback すると、別 session のモデルを正式に表示する（中）。陽性例は `test_history_prefers_explicit_file_over_runtime_file`。 |
| `test_history_invalid_utf8_fails_without_traceback` | S | 残す。ただし traceback 文面の確認は削る | 壊れた session を読み飛ばしてモデルを推測すると誤帰属する（中）。失敗表示の形式だけは L。 |
| `test_session_crosscheck_reports_matching_selected_and_observed` | S | 残す | selected と observed が一致するときの照合済みデータを維持する陽性例。全て conflict と返す実装による記録の欠落を防ぐ（中）。 |
| `test_runtime_and_selected_conflict_suppresses_text_answer` | S | 残す | runtime と選択済みモデルが食い違ってもテキストへモデル名を出すと、誤った担当を記録する（中）。 |
| `test_newer_observed_identity_conflicts` | S | 残す | 新しい observed provider/model の不一致を見逃すと、実際に応答したモデルを誤帰属する（中）。2 variant は同じ検査の provider/model 各軸。 |
| `test_observed_before_model_switch_is_warning` | S | 残す | 古い observed を現在のモデルとして採用すると、切替後の担当モデルを取り違える（中）。 |
| `test_crosscheck_ignores_abandoned_branch` | S | 残す | 放棄された session 分岐のモデルを採用すると、現在の会話とは別のモデルを担当として記録する（中）。 |
| `test_explicit_session_file_precedes_env_sources` | S | 残す | 明示ファイルより環境変数を優先すると、異なる session のモデルを採用する（中）。 |
| `test_pi_session_file_precedes_subagent_session` | S | 残す | 親 runtime の session より子の session を優先すると、子のモデルを親の担当として記録する（中）。 |
| `test_wrong_session_id_does_not_overrule_runtime_env` | S | 残す | session ID が違うファイルを runtime の照合に使うと、別実行のモデルによる偽の衝突・偽の一致を生む（中）。明示した場合の拒否と、暗黙の無視を両方確かめる。 |
| `test_unreadable_session_paths_follow_source_policy` | S | 残す | 明示パスが読めないのに暗黙ソースへ fallback すると、別 session を照合済みとして扱う（中）。自動パスでは警告付きで runtime を使う陽性例。 |
| `test_crosschecked_text_modes` | S | 残す | `--model`・`--provider`・`--session` の値を取り違えると、誤った担当をそのまま人が記録する（中）。3 variant を 1 行で判定。 |
| `test_json_without_session_path_reports_unchecked` | S | 残す | session が無いのに `selected`/`observed` を入れて照合済みのように見せると、未検証のモデルを正式に記録する（中）。 |
| `test_runtime_json_has_same_keys_with_and_without_session_file` | L | 消す | JSON のキー欠落は利用側の parse・キー参照でエラーとして現れる。キー集合を固定するテストはこの損害を追加で守らない。 |
| `test_runtime_env_stays_required_with_explicit_session_file` | S | 残す | runtime が無いとき、明示 session file を与えただけでその履歴を正式なモデル名として返す回帰は、session file の無い `test_strict_fails_closed_without_runtime` では拾えない。古いモデルの正式記録を防ぐ（中）。 |

#### `agent-handoff/tests/test_agent_handoff_skill_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_trigger_queries_have_valid_structure` | L | 消す | eval JSON の形・必須キーの欠落は eval の読込・実行時に解析エラーになる。 |
| `test_schema_documents_the_authored_fields` | F∩S | 残す | authored の `decisions`・`out_of_scope`・`verification`・`landing` が schema から消えると、引き継ぎ時に決定や境界を無言で落としうる（中）。これは利用者が確認する作業記録の保持範囲。 |
| `test_every_referenced_path_exists` | L | 消す | 指定されたファイルが無ければ開く・実行する時にファイル不在が明らかになる。過去の不具合の再発でも、今の基準では L。 |
| `test_schema_maps_review_fix_planning_hold_to_deferred` | F∩S | 残す | Hold を Skip 等へ写すと、未解決のレビュー指摘が延期記録から黙って消える（中）。状態対応の固定は記録損失を防ぐ。 |
| `test_evals_json_has_expectations` | L | 消す | eval の期待値が無ければ eval の読込・実行時に失敗する。 |
| `test_schema_requires_git_branch_head_status_in_json_fields` | F∩S | 残す | worktree・branch・head・status を引き継がないと、別 checkout の変更を対象として扱いうる（高）。操作対象を限定する schema 固定。 |
| `test_schema_allows_null_sources_spec` | L | 消す | Spec の無い場面で存在しない path を作ると、後続のファイル読込が失敗する。文面の `null` 固定は不要。 |
| `test_documents_and_code_have_separate_schema_fields` | F∩S | 残す | 文書とコードの checkout を混同すると、別リポジトリへの commit・push につながる（高）。操作対象を分ける schema 固定。 |

#### `planning-parallel-issues/tests/test_planning_parallel_issues_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_referenced_procedures_exist` | L | 消す | 参照先が無ければ手順を開く時にファイル不在が分かる。 |
| `test_validation_links_and_scenarios_resolve` | L | 消す | リンク不在・scenario のキー欠落は開く時または eval 実行時に明らかな失敗となる。 |
| `test_explicit_path_and_skill_references_exist` | L | 消す | 指定したローカル path や skill が無ければ開く時にエラーになる。 |

#### `rst-writer/tests/test_rst_writer_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_markdown_links_resolve` | L | 消す | 文書リンク先の不在は開く際に分かる。 |
| `test_templates_named_by_the_document_types_exist` | L | 消す | 指定された template が無ければ作成時にファイル不在となる。 |
| `test_every_eval_uses_existing_fixture_files` | L | 消す | fixture・対象ファイル不在や JSON 形の誤りは eval を実行すると失敗する。 |

#### `herdr-agent-task/tests/test_herdr_agent_task_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_states_match_the_command` | L | 消す | 文書にある状態をコマンドが受け付けなければ使用時に非 0 とエラー文が返る。 |

#### `simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`

| テスト関数 | 分類 | 扱い | 具体的な理由・代表 |
| --- | --- | --- | --- |
| `test_interpolation_is_limited_to_the_target_line` | F∩S | 残す | `$ARGUMENTS`・`$0`〜`$9` が対象行以外にあると、呼び出し引数でスキル本文のコードブロックまで展開され、意図外のコマンド・対象で作業しうる（高）。操作範囲を定める固定値。 |

#### 要注意点

- 再監査後の 82 行は、S 42、S（L 混在）2、F∩S 8、D 12、L 18。S と F∩S の残す候補は計 52 行。件数を合わせる目的では削っていない。
- 残す S の守りの群: `task_watch` は (1) 完了・安全失敗の判定、(2) 期限・無進捗・予約枠・失敗回数、(3) 進捗ログの読取、(4) 実 PID・process group の停止確認、(5) 最後の記録と既存 state の保全。`pi-model-name` は (1) runtime と履歴の境界、(2) 情報源の優先順・読めない時の扱い、(3) active branch と selected/observed の照合、(4) テキスト・JSON の出所表示。その他は実行権限、スキルの操作範囲、取り込み履歴、handoff の対象と記録、`$ARGUMENTS` の展開範囲。
- `task_watch` の `completed` と残存 PID は別の守り。core の結果判定を残すだけでは実プロセスの停止を証明できないため、`unstoppable`・`escalate-kill`・`residual_processes`・watcher 強制終了後の status は残す。
- `pi-model-name` の履歴 fallback・session の優先順・ID 照合は、どれも別の session を正しいモデルとして表示しうる。表示形式の重複だけを削り、fail-closed の拒否と正常例を残す。
- `simplify-in-subagent` の `$ARGUMENTS` は文面の固定値でも操作範囲の保護なので F∩S。削除対象の F と混同しない。
- `test_policy_rejects_values_outside_the_declared_ranges` と `test_invalid_arguments_exit_2_without_creating_state` は S と L が同じ関数に混在する。残す場合は、前者は予約時間の境界、後者は既存 state を上書きしない断言に絞る。
- この表は関数単位の一次監査。削除実装時は D の代表の残存と、F∩S の固定値が防ぐ損害を Spec とテストのコメントに明記する。
