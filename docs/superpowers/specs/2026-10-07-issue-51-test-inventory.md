# Issue #51: テスト分類表

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: #51（#36・PR #46 の後続）、PR: 未作成
- 状態: draft
- 基準 HEAD: `a94f04eea41fce3fb344dd4a7f10a7a0692512c2`（PR #48 のマージ後）
- 関連 Plan: `docs/superpowers/plans/2026-10-07-issue-51-test-cleanup.md`
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-51-test-cleanup`（branch `chore/issue-51-test-cleanup`）
- PARENT_ROOT: `/workspaces/reso-world`

## 前後比較

## スキルのテスト

`<skill>/` は `.agents/skills/<skill>/tests/` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号。symlink は `scripts/check-layout.sh` 検査 4 が全スキルを検査し、`tests/scripts/test-check-layout.bash` の 6 がこのリポジトリで実行する（以下「check-layout」）。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `tests/skills/test_skill_frontmatter.py::test_shared_skills_are_discovered` | スキルの探索失敗 | 削除 | 根拠のない件数固定（10 件） | ルートが無ければ `::test_every_skill_directory_has_a_skill_file` が失敗する | |
| `tests/skills/test_skill_frontmatter.py::test_frontmatter_is_valid_for_every_runtime` | name・description・allowed-tools がランタイムの制約に反する | 維持 | 全スキル共通の frontmatter 検査。各スキル側の重複はここへ寄せた | — | |
| `tests/skills/test_skill_frontmatter.py::test_every_skill_directory_has_a_skill_file` | SKILL.md の無いスキル | 維持 | 構造の検査 | — | |
| `tests/skills/test_legacy_references.py::test_removed_skill_is_gone_from_every_runtime` | 撤去したスキルの再出現 | 削除 | 型 2 | 中身が移植元を指せば下の grep が検出する | #17 |
| `tests/skills/test_legacy_references.py::test_tracked_files_do_not_refer_to_the_migration_source` | 追跡ファイルが移植元のリポジトリ・`public/`・verify スクリプトを指す | 理由付き固定値として維持（除外パスの実在検査は削除） | 移植は続いており、指示が移植元を指すと誤対象の操作になる。理由を追記。除外パスの実在はテスト自身の設定の検査で、他領域のファイル削除と衝突する | — | #17, #22, #36 |
| `tests/skills/test_legacy_references.py::test_legacy_regex_pattern` | guard の正規表現の検出漏れ・誤検出 | 維持 | 実リポジトリに該当が無く、guard が働くことを示すのはこの正負の例だけ | — | |
| `tests/skills/test_skill_packages.py::test_targeted_skill_semantics` | 1 スキルの MCP・他エンジン案内 | 削除 | `SKILL_UNDER_TEST` が無いと常に skip。全スキル版と同じ検査 | `::test_no_positive_execution_guidance_in_skills_or_shared_references` | |
| `tests/skills/test_skill_packages.py::test_required_names_and_valid_frontmatter`（`read_skill` の frontmatter 検査を含む） | Blender スキルの欠落・frontmatter の誤り | 削除 | スキル名一覧の写しと共通検査の重複 | `test_skill_frontmatter.py`、`::test_provenance_license_and_document_coverage` の output_paths の実在 | |
| `tests/skills/test_skill_packages.py::test_installed_style_layout_preserves_standard_and_unrelated_content` | （なし） | 削除 | 型 5。配置処理を呼ばず、コピーした fixture を比べるだけ | 不要（実行するコードが無い） | #51 |
| `tests/skills/test_skill_packages.py::test_no_unapproved_guidance_or_false_runtime_claims` | 未導入スキル名の記述、seed・fog の説明文の欠落 | 削除 | 型 1・2。存在しないスキルへの委譲は操作を起こさない | 不要 | #36 |
| `tests/skills/test_skill_packages.py::test_references_and_links_resolve` | 壊れたリンク | 維持（共有 reference の実在の重複は削除） | 参照先の実在 | 共有 reference の実在は provenance の output_paths 検査 | |
| `tests/skills/test_skill_packages.py::test_execution_guidance_guards_cover_positive_and_negative_fixtures` | guard の否定判定の誤り | 維持 | guard が働くことを示す正負の例 | — | #36 |
| `tests/skills/test_skill_packages.py::test_no_positive_execution_guidance_in_skills_or_shared_references` | Blender MCP・他エンジンへの実行案内 | 理由付き固定値として維持 | ResoLoop の外で操作させない安全上の禁止。理由を追記 | — | #36 |
| `tests/skills/test_skill_packages.py::test_provenance_license_and_document_coverage` | 取り込み元 SHA・MIT 表記・出力ファイルの欠落 | 理由付き固定値として維持 | 凍結した取り込み履歴とライセンス表記 | — | |
| `agent-handoff/test_agent_handoff_skill_contract.py::test_skill_does_not_reference_the_removed_generator` | 撤去した CLI 名の再出現 | 削除 | 型 2 | 不要 | |
| `agent-handoff/…::test_skill_declares_claude_code_allowed_tools` | 許可の欠落、旧パスへの許可 | 削除 | 型 3。部分一致は許可の拡大を検出しない。旧パスは型 2 | 許可の型は `test_skill_frontmatter.py` | |
| `agent-handoff/…::test_trigger_queries_have_valid_structure` | eval 入力の型の誤り | 維持（`python-tdd-team` の不存在は削除: 型 2） | eval JSON の構造 | — | |
| `agent-handoff/…::test_schema_is_version_2_and_documents_the_authored_fields` | 版の変更、受け手に渡すキーの欠落 | 版の固定は削除（型 3）、キー検査は理由付き固定値として維持（`::test_schema_documents_the_authored_fields`） | decisions・out_of_scope・verification・landing は触ってはいけない範囲・検証・反映先を渡す | — | #36 |
| `agent-handoff/…::test_every_referenced_path_exists` | 存在しないパスの案内 | 維持 | 参照先の実在（過去の不具合の再発防止） | — | |
| `agent-handoff/…::test_schema_maps_review_fix_planning_hold_to_deferred` | Hold が fix・skip に変わる | 理由付き固定値として維持 | 人の判断待ちを実行・放棄に変えない | — | |
| `agent-handoff/…::test_evals_json_uses_expectations_not_assertions` | 採点基準の無い eval、旧キー | 維持（`::test_evals_json_has_expectations`。`assertions` の不存在は削除: 型 2） | eval JSON の構造 | — | |
| `agent-handoff/…::test_schema_requires_git_branch_head_status_in_json_fields` | 作業 checkout の情報の欠落 | 理由付き固定値として維持 | 誤った checkout での操作を防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_schema_allows_null_sources_spec` | spec の null が許されない | 理由付き固定値として維持 | 存在しない Spec パスの捏造を防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_documents_and_code_have_separate_schema_fields` | 文書とコードの root の混同 | 理由付き固定値として維持 | 別の checkout へのコミットを防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `find-docs/test_find_docs_contract.py`（ファイル削除）`::test_common_instructions_do_not_embed_tool_specific_commands` | `AGENTS.md` の `npx ctx7` | 削除 | 型 1 | 不要 | #36 |
| `find-docs/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `herdr-agent-task/test_herdr_agent_task_contract.py::test_command_script_exists` | コマンドの欠落 | 削除 | 重複 | `::test_states_match_the_command` がスクリプトを読む | |
| `herdr-agent-task/…::test_states_match_the_command` | 文書の状態とコマンドが受け付ける状態の不一致 | 維持 | 定義元と配置先の比較 | — | |
| `herdr-agent-task/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `monitoring-long-tasks/test_monitoring_long_tasks_skill_contract.py`（ファイル削除）`::test_runtime_skill_copies_are_byte_identical` | 2 経路の内容の不一致 | 削除 | 型 5（symlink の両経路で同じ実体） | check-layout | #51 |
| `monitoring-long-tasks/…::test_claude_loads_the_shared_instructions` | `CLAUDE.md` の読み込み指定の欠落 | 削除 | 重複 | `tests/scripts/test-instructions.bash`（`CLAUDE.md` の 1 行目） | #51 |
| `monitoring-long-tasks/…::test_runtime_instructions_do_not_reference_removed_scripts` | `scripts/ci/` の再出現 | 削除 | 型 2 | `test_legacy_references.py`（`scripts/ci/verify`・`verify.sh`） | |
| `pi-model-name/test_pi_model_name_contract.py::test_frontmatter` | name・description の誤り | 削除 | 共通検査の重複 | `test_skill_frontmatter.py` | |
| `pi-model-name/…::test_script_executable` | 実行権限の欠落 | 削除 | 重複 | 実行テストがスクリプトを直接起動する | |
| `pi-model-name/…::test_json_provenance_runtime` | runtime の JSON の誤り | 統合 | 同じ入力・経路 | `::test_json_without_session_path_reports_unchecked` | |
| `pi-model-name/…` のほかの実行テスト | 解析・優先順位・fail-closed の誤り | 維持 | スクリプトの実行 | — | |
| `planning-parallel-issues/test_planning_parallel_issues_contract.py::test_referenced_procedures_exist` | 壊れたリンク | 維持 | 参照先の実在 | — | |
| `planning-parallel-issues/…::test_validation_links_and_scenarios_resolve` | 壊れたリンク、scenarios の構造、`scripts/ci/` | 維持（`scripts/ci/` の不存在は削除: 型 2） | 参照先の実在・eval 構造 | `test_legacy_references.py` | |
| `planning-parallel-issues/…::test_explicit_path_and_skill_references_exist` | 存在しないパス・スキルの案内 | 維持 | 参照先の実在 | — | |
| `planning-parallel-issues/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `pr-review/test_pr_review_skill_contract.py::test_helper_has_one_real_copy_shared_through_the_skill_symlink` | helper の欠落、symlink、`.devin/skills` | 削除 | 重複・型 5・型 2 | helper は `test_pr_review_workspace.py` が読み込む。symlink・`.devin/skills` は check-layout 検査 4・5 | |
| `pr-review/…::test_skill_interpolation_is_limited_to_the_target_line` | `$ARGUMENTS`・`$N` の置換でコードが壊れる | 維持 | 実行時の展開の誤り | — | |
| `pr-review/…::test_skill_keeps_claude_code_permissions_consistent` | 許可の拡大、`--temp-root` が `/tmp` の外 | 理由付き固定値として維持 | 完全一致の許可リストは権限の境界 | — | #36 |
| `pr-review/…::test_pr_review_skills_have_no_legacy_path_selection` | 旧 devenv の選択の再出現 | 削除 | 型 2・4 | resolver の実行テスト（登録済みの経路・未知のリポジトリでの停止・`CODE_ROOT` の検証） | |
| `pr-review/…::test_review_budget_reference_is_required_and_resolves` | リンク切れ、予算 reference の欠落 | 書き換え（`::test_skill_links_resolve`） | 必須リンクは型 1、パスの一致は定数同士で恒真。リンクの実在だけ残す | — | |
| `pr-review/…` の resolver・preflight の実行テスト | 誤った checkout・remote の選択、停止しない | 維持 | resolver の実行 | — | |
| `pr-review/test_pr_review_workspace.py::test_review_artifact_paths_use_slash_sanitized_model_name` | （なし） | 削除 | 置換済みの名前を渡すだけで隣の検査と同じ経路 | `::test_review_artifact_paths_preserve_exact_model_name`、`::test_create_pins_slash_model_name_as_hyphenated_filename` | |
| `pr-review/test_pr_review_workspace.py::test_create_state_omits_main_snapshot` | 撤去した `main_snapshot` の再出現 | 削除 | 型 2・3 | `::test_save_allows_unrelated_main_changes` | |
| `pr-review/test_pr_review_workspace.py` の 3 関数の `state["version"] == 6` | 版の変更 | 削除 | 型 3 | create と load_state の版の不一致は save の往復（`::test_save_uses_only_pinned_paths` ほか）、旧版の拒否は `::test_load_state_rejects_previous_version` | |
| `pr-review/test_pr_review_workspace.py` のほかの実行テスト | 誤った保存先・後始末・中断・lock の誤り | 維持 | helper の実行 | — | #39 |
| `repo-cleanup-after-merge/test_repo_cleanup_after_merge_contract.py::test_allowed_tools_cover_the_commands_the_steps_run` | 許可の欠落 | 削除 | 型 3。部分一致は許可の拡大を検出しない | 許可の型は `test_skill_frontmatter.py` | |
| `repo-cleanup-after-merge/…::test_related_skills_exist` | 存在しないスキルの案内 | 維持 | 参照先の実在 | — | |
| `repo-cleanup-after-merge/…::test_evals_have_valid_structure_and_existing_files` | eval 構造・fixture の欠落 | 維持 | eval 構造・参照先の実在 | — | |
| `repo-cleanup-after-merge/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `repo-cleanup-after-merge/test_detached_update.py::test_cleanup_keeps_the_forks_local_main_out_of_deletion_candidates` | fork の `main` を削除候補にする | 理由付き固定値として維持 | 利用者所有の基準 ref。理由はテストに記載済み | — | PR #48 |
| `repo-cleanup-after-merge/test_detached_update.py` のほかの実行テスト | 誤対象の更新・削除、失敗時に止まらない | 維持 | 手順のコードの実行 | — | #47, PR #48 |
| `review-fix-planning/test_review_fix_planning_skill_contract.py::test_status_comment_snippet_escapes_heredoc_and_pins_repository` | heredoc でのコマンド実行、別リポジトリへの投稿 | 理由付き固定値として維持 | 成功経路を実行する検査が無く、この検査だけが守る | — | |
| `review-fix-planning/…::test_helper_has_one_real_copy_shared_through_the_skill_symlink` | helper の欠落、symlink | 削除 | 重複・型 5 | helper は `test_upsert_pr_comment.py` が読み込む。symlink は check-layout | |
| `review-fix-planning/…::test_allowed_tools_match_the_verification_and_spec_location` | 許可の欠落、旧パス | 削除 | 型 3。旧パスの不存在は型 2 | 許可の型は `test_skill_frontmatter.py` | |
| `review-fix-planning/…` の context・status の実行テスト | preflight が止まらない、誤った push 先 | 維持 | 手順のコードの実行 | — | |
| `review-fix-planning/test_upsert_pr_comment.py` | 他エージェントのコメントの上書き、別リポジトリへの投稿 | 維持 | helper の実行 | — | |
| `rst-writer/test_rst_writer_contract.py::test_profiles_and_resource_directories_exist` | profile・assets・fixtures の増減、旧 style guide | 削除 | 型 3（一覧の写し）・型 2 | `::test_markdown_links_resolve`・`::test_templates_named_by_the_document_types_exist`・`::test_every_eval_uses_existing_fixture_files` | |
| `rst-writer/…::test_markdown_links_resolve` | 壊れたリンク | 維持 | 参照先の実在 | — | |
| `rst-writer/…::test_templates_named_by_the_document_types_exist` | 存在しないテンプレートの案内 | 維持 | 参照先の実在 | — | |
| `rst-writer/…::test_every_eval_uses_existing_fixture_files` | eval 構造・fixture の欠落 | 維持 | eval 構造・参照先の実在 | — | |
| `rst-writer/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `simplify-in-subagent/test_simplify_in_subagent_contract.py::test_interpolation_is_limited_to_the_target_line` | `$ARGUMENTS`・`$N` の置換でコードが壊れる | 維持 | 実行時の展開の誤り。理由を追記 | — | |
| `simplify-in-subagent/…::test_frontmatter_keeps_only_keys_every_runtime_can_live_with` | argument-hint・subagent の値、allowed-tools の有無 | 削除 | 型 3。YAML リストの allowed-tools は共通検査が拒否する | `test_skill_frontmatter.py` | |
| `simplify-in-subagent/…::test_claude_code_reads_the_same_skill` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `stale-git-lock-recovery/test_stale_git_lock_recovery_contract.py::test_frontmatter_declares_name_and_trigger_conditions_only` | frontmatter のキー・値 | 削除 | 共通検査の重複とキー集合の写し | `test_skill_frontmatter.py` | |
| `stale-git-lock-recovery/…::test_bash_snippets_do_not_run_destructive_git_commands` | 利用者の作業を消すコマンド | 理由付き固定値として維持 | 安全上の禁止。理由はテストに記載済み | — | #36 |
| `stale-git-lock-recovery/…::test_skill_never_removes_the_lock_by_hand` | holder の確認を飛ばす `rm` | 理由付き固定値として維持 | 安全上の禁止。理由を追記 | — | |
| `stale-git-lock-recovery/…::test_bash_snippets_do_not_clobber_zsh_special_variables` | zsh で壊れるスニペット | 維持 | 実行時の誤り | — | |
| `stale-git-lock-recovery/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5 | check-layout | |
| `stale-git-lock-recovery/…` の helper の実行テスト | 生きている holder のロック削除、誤対象 | 維持 | helper の実行 | — | PR #30 |
| `stale-git-lock-recovery/test_ff_merge_keep_untracked.py::test_plain_merge_is_blocked_by_the_fixture` | （なし） | 削除 | 型 5（fixture と git だけを検査） | `::test_fast_forwards_and_restores_every_conflicting_file` が同じ fixture をスクリプトで実行する | |
| `stale-git-lock-recovery/test_ff_merge_keep_untracked.py` のほかの実行テスト | 未追跡ファイルの消失、誤対象 | 維持 | スクリプトの実行 | — | |

前後: ファイル 19→17（Python のみ、シェル 0）、行 6,529→6,126、収集 510→474（skip 1→0）、所要 95〜106 秒→100〜113 秒（`uv run pytest tests/skills .agents/skills -q` を複数回実測。消した検査は合計 0.3 秒ほどで、幅は `/proc` を走査する stale-git-lock-recovery のテストの揺れ）

## tests/scripts

`<py>` は `tests/scripts/test_superpowers_lifecycle.py` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `pyproject.toml` の testpaths（`tests` → `tests/skills`） | （同じ unittest の二重実行） | 統合 | `test_superpowers_*.py` を run-tests.bash とルート pytest の両方で実行していた。CI の skill-tests・README と同じ範囲にする | run-tests.bash の `test-superpowers-python.bash` | #51 |
| `tests/scripts/test-superpowers-python.bash` | Python のテストが run-tests.bash・CI で実行されない | 維持 | CI の devcontainer-tests が `tests/scripts` の Python を実行する唯一の経路 | — | |
| `<py>::test_current_callers_do_not_invoke_replacement` | 文書が `--replace-from` を案内する | 削除 | 型 1・2 | `test_superpowers_review_copy.py::test_replace_from_is_rejected_before_any_mutation`（変更前に拒否する） | #36 |
| `<py>::test_handoff_schema_separates_approval_current_authority_and_publication` | 承認・実行許可・完了根拠のフィールドの欠落 | 理由付き固定値として維持（`document_published` は削除） | 承認の無い版・許可の無い作業の再開を防ぐ。理由を追記 | `document_published` は agent-handoff の `::test_documents_and_code_have_separate_schema_fields` | #36 |
| `<py>::test_imported_documents_are_unchanged_since_import` | 取り込んだ過去文書の変更 | 理由付き固定値として維持 | 過去文書の SHA manifest | — | #36 |
| `<py>::test_the_unittest_suite_is_wired_into_the_existing_ci_runner` | runner の配線漏れ | 削除 | 型 4。wrapper を消すとこの検査も実行されなくなり、検出できない | 不要（wrapper があれば run-tests.bash が `tests/scripts/*.bash` の glob で実行し、一覧への書き忘れは起きない。wrapper の削除は検出しない） | #36 |
| `<py>::ImportedDocumentPortabilityTests`（3 関数） | SHA 照合が Git の履歴に依存する・変更を検出しない | 削除 | テスト自身（SHA 照合）しか検査しない。照合は作業ツリーのバイトだけを読む | SHA 照合は維持。Git の無いコピーで通ること、文書の変更で失敗することを今回確かめた | #36 |
| `<py>::EndToEndLifecycleTests::test_committed_version_and_resume_gate_eval_cases` | 再開判定表の誤り | 書き換え（`::test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked`） | handoff はテストが書いて読み戻すだけ、resolver の実行は重複。承認・許可の無い 5 ケースを ready にしない判定だけ理由付き固定値として残す | resolver は `test_superpowers_context.py::test_head_remote_preserves_no_pushurl_fallback`（外部 CODE_ROOT と head）・`::test_document_main_and_linked_roots_verify_requested_branch`（DOC_ROOT） | #36 |
| `<py>::EndToEndLifecycleTests::test_supported_route_reaches_simulated_publication_with_versioned_copies` | コピーの作成・非置換の誤り | 削除 | 実行部分は review-copy・context のテストと重複。承認記録・公開・復元はテストが書いた値を読み戻すだけ | `test-superpowers-review-copy.bash`、`test_superpowers_review_copy.py::test_new_versioned_name_leaves_the_old_copy_untouched`・`::test_committed_plan_copies_with_exact_bytes_full_sha_and_kind_flow`、`test_superpowers_context.py::test_document_main_and_linked_roots_verify_requested_branch` | |
| `<py>::EndToEndLifecycleTests::test_unsupported_external_implementation_route_records_blocked_state` | （なし） | 削除 | テストが書いた handoff を読み戻すだけ | 不要 | |
| `tests/scripts/test_superpowers_context.py` | 誤った checkout・remote の選択、認証情報の表示、Git の状態の変更 | 維持 | resolver の実行 | — | PR #16 |
| `test_superpowers_context.py::test_missing_unsupported_or_foreign_parent_origin_has_actionable_error` | 別ホストの scp 形式の origin を受け入れる | 統合 | `test-superpowers-review-copy.bash` の 12 だけが持っていた失敗ケースを移した | — | |
| `tests/scripts/test_superpowers_review_copy.py` | 既存コピーの差し替え、未コミットの正本、symlink・FIFO への書込み、競合 | 維持 | モジュールの実行 | — | PR #16 |
| `tests/scripts/test-superpowers-review-copy.bash` の 2〜14 | 同上（ラッパー経由） | 削除 | 同じモジュールの同じ分岐を Python のテストが実行する | `test_superpowers_review_copy.py` の対応するテスト（symlink 先へ書かないことは `::test_destination_changed_into_a_symlink_before_publish_does_not_follow`）。remote の形式・checkout のルートは `test_superpowers_context.py` が PARENT_ROOT・CODE_ROOT で検査し、DOC_ROOT も同じ `inspect_checkout`・`_require_origin` を通る。`--name spec.md` そのものの例は無く、名前の検査は別の誤った名前で見る | |
| `tests/scripts/test-superpowers-review-copy.bash` の 1 | ラッパーがモジュールを起動できない | 維持 | 利用者が実行するラッパーの唯一の実行 | — | |
| `tests/scripts/test-agent-config.bash` の Codex の `context7` 名 | ユーザー設定の context7 と項目が混ざる | 理由付き固定値として維持 | 8a95021 で直した不具合の再発防止 | — | |
| `test-agent-config.bash` の Codex の `env_vars` | 外部パッケージへ渡す秘密情報が増える | 理由付き固定値として維持 | 秘密情報の露出範囲。理由を追記 | — | |
| `test-agent-config.bash` の Codex・Cursor の command・args とマージの再現 | 設定値の変更 | 削除 | 型 3。マージの再現はテスト自身の計算で、名前の検査以上のことを検出しない | command・args は不要。マージの再現が狙った混線は、上の名前の検査が見る | |
| `test-agent-config.bash` の `.pi-lens.json`（`$schema`・ignore） | `$schema` の再追加、ignore の変更 | 削除 | 型 2・3 | 不要 | #19 |
| `test-agent-config.bash` の `sp-implementer.md`・`.devin/config.json` | model・一覧の変更、作らない設定ファイル | 削除 | 型 2・3 | `sp-implementer.md` の実在は check-layout の検査 2（4 プロジェクトの symlink が行き先を失うと失敗する）。`test-check-layout.bash` の 6 がこのリポジトリで実行する。model・一覧・`.devin/config.json` は不要 | |
| `tests/scripts/test-ci.bash` の trigger・job・コマンド・action の版・Blender | CI 定義の変更 | 削除 | 型 3（job・コマンド・版の写し）。存在しない action の版は CI の実行で失敗として表に出るが、job やコマンドを消したことは検出しない（意図した変更として差分で見る） | 不要。gitleaks の job を消すと下の検査が失敗する | |
| `test-ci.bash` の gitleaks のジョブと `.gitleaks.toml` | 秘密情報の見逃し、除外の拡大、allowlist が読まれない | 理由付き固定値として維持 | 秘密情報の検出の設定。正規表現は正負の例で実行する。理由を追記 | — | |
| `tests/scripts/test-docs.bash` の参照検査 | 存在しないファイル・スキルの案内 | 維持 | 参照先の実在 | — | #36 |
| `test-docs.bash` の `dsh` | 撤去した dsh の再記載 | 削除 | 型 2 | 不要（未導入のコマンドは実行時に失敗するだけ） | #17 |
| `test-docs.bash` の `docs/integration.md` の文言 | 統合手順の文言の変更 | 削除 | 型 1。2026-10-06 にも更新した現行の文書 | 不要 | |
| `test-docs.bash` の凍結した仕様・計画の 7 文字列 | レビューで直した箇所の書き戻し | 削除 | 型 1・2。修正の反映を一度確かめる検査で、文書の全体は守らない | 不要（凍結した文書は編集しない） | #36 |
| `tests/scripts/test-file-modes.bash` の glob の対象 | 実行権限の欠落 | 維持 | `scripts/*.sh` などを直接起動する | — | |
| `test-file-modes.bash` のランチャー 9 本 | ランチャーの権限・追跡の漏れ | 削除 | 型 3（ランチャー一覧） | `install_beforehand.bash` が `install -m 0755` で配置し、無ければそこで失敗する | |
| `test-file-modes.bash` の `checked -gt 30` | 対象を 1 件も読まない | 書き換え（`-gt 0`） | 根拠のない件数固定。空の走査だけを検出する | — | |
| `tests/scripts/test-gitignore.bash` | 秘密情報・私的データの追跡、ワールドのデータの追跡漏れ、許可外の追跡例外 | 理由付き固定値として維持 | ignore の範囲と追跡例外。理由を追記 | — | #36 |
| `tests/scripts/test-instructions.bash` の `CLAUDE.md` 1 行目・参照検査 | 読み込み指定の誤り、存在しない参照 | 維持 | 実際の読み込み指定、参照先の実在 | — | #51 |
| `test-instructions.bash` のペルソナ SHA | 利用者所有部分の変更 | 理由付き固定値として維持 | 利用者所有部分 | — | #36 |
| `test-instructions.bash` の `verify.sh`・`verify-devenv` | 移植元のスクリプト名 | 削除 | 重複 | `tests/skills/test_legacy_references.py` | #17 |
| `test-instructions.bash` の `AGENTS.md` の `reStructuredText`・`Gitleaks`・`contingency`・`AskUserQuestion`・`TaskOutput`・`npx ctx7` | 旧リポジトリ・ツール固有の文言 | 削除 | 型 1。誤対象の操作にならない | 不要 | #36 |
| `test-instructions.bash` の `.pi/APPEND_SYSTEM.md` の撤去した検証記録（`subagent-launch-verification`）・読み込み方式（`@.agents/skills/`）・設定（`PI_DISTILL_MODEL`）・旧引数（`async: false`） | 撤去した記述の再出現 | 削除 | 型 2 | 不要（再導入しても role API が拒否するか無効な記述にとどまり、誤対象の操作・秘密情報の露出にはならない） | #19 |
| `tests/scripts/test-check-layout.bash` の 6 と 44 | このリポジトリの配置の誤り、mounts の検査の skip | 統合（44 を 6 にまとめた） | 同じリポジトリで check-layout を 2 回実行していた | — | |
| `test-check-layout.bash` のほか | check-layout の判定・終了コードの誤り | 維持 | スクリプトの実行 | — | |
| `tests/scripts/test-new-world.bash` | 作成・適用の誤り、食い違いでの変更、冪等性 | 維持 | スクリプトの実行 | — | |
| `tests/scripts/test-resoloop-fork.bash` | 誤った remote・push、dirty な checkout の変更、版の誤り | 維持 | スクリプトの実行 | — | #41 |
| `tests/scripts/lib/path.bash`、`tests/scripts/fixtures/superpowers-imported-documents.sha256.json` | — | 維持 | 残る検査が使う | — | |

前後: ファイル Python 3→3・シェル 11→11、行 Python 1,367→1,011・シェル 1,697→1,430、収集 68（subtest 154）→61（144）、所要は隔離コピーで変更前後を交互に 2 回実行して run-tests の `tests/scripts/*.bash` 83〜84 秒→71〜77 秒・`uv run pytest tests/scripts` 46〜51 秒→42〜45 秒。ルート pytest からは同じ 68 件（約 45 秒）の二重実行を外した（収集 542→474）

## .devcontainer

`<sa>` は `.devcontainer/test-pi-superagents.bash`、`<cx>` は `.devcontainer/test-pi-openai-codex.bash`、`<hm>` は `.devcontainer/test-herdr-migration.bash`、`<py>` は `.devcontainer/tests/test_pi_mcp_cleanup.py` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号。「代わりの保証」には、変異を入れた一時コピーで失敗することを確かめた検査だけを書く。check-layout は `scripts/check-layout.sh`（`tests/scripts/test-check-layout.bash` の 6 がこのリポジトリで実行する）。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `.devcontainer/run-tests.bash` | — | 維持 | runner。glob で列挙するので、消したファイルの呼出しは残らない | — | |
| `.devcontainer/test-run-tests.bash` | runner の既定の対象・失敗の伝え方の誤り | 維持 | runner の実行 | — | |
| `.devcontainer/test-pi-mcp-cleanup.bash` | `<py>` が run-tests.bash・CI で実行されない | 維持 | `<py>` を実行する唯一の経路 | — | |
| `test-cleanup-workspace.bash` の 1（dry-run） | dry-run で消す・表示しない | 維持 | スクリプトの実行 | — | |
| `test-cleanup-workspace.bash` の 2（既定値 `/tmp`・1 日・dry-run なし） | 削除の範囲の拡大 | 理由付き固定値として維持（移植元の変数を渡す部分は削除） | 安全な操作範囲。理由を追記 | — | |
| `test-cleanup-workspace.bash` の `MAATLOG_CLEANUP_*`・yarn・`verify.sh`・Issue 番号 | 移植元の名残 | 削除 | 型 2。移植元の名前は重複 | `tests/skills/test_legacy_references.py`（スクリプトに `MAATLOG_CLEANUP_TMP_ROOT`・`verify.sh` を足すと失敗）。yarn・Issue 番号は不要 | #17 |
| `test-herdr-agent-task.bash` の CLI の実行テスト（23 関数） | 状態・タスク名・TTL の誤り、不正な入力の受理、herdr 無しでの失敗 | 維持 | CLI の実行 | — | |
| `test-herdr-agent-task.bash::test_herdr_toml_passes_config_check` | herdr が読めない設定 | 維持 | herdr の実行（未導入なら skip） | — | |
| `test-herdr-agent-task.bash::test_herdr_toml_agents` | 設定値の変更、存在しない `title` トークン | 削除 | 型 3 | `title` は `::test_herdr_toml_passes_config_check`（`herdr config check` が exit 1） | |
| `test-herdr-agent-task.bash::test_skill_files_exist_and_match` | symlink の誤り | 削除 | 型 5 | check-layout（実体のコピーに置き換えると失敗） | |
| `test-herdr-agent-task.bash` の `SKILL.md`・`.pi/APPEND_SYSTEM.md`・README の文言（3 関数） | 文言の変更 | 削除 | 型 1 | 不要 | |
| `test-herdr-agent-task.bash::test_cli_is_executable` | 実行権限の欠落 | 削除 | 重複 | 同じファイルの実行テスト（CLI を直接実行する） | |
| `test-herdr-status.bash` の git 状態・updater の実行テスト | 状態・ブランチ名・トークンの消去の誤り | 維持 | 実行 | — | |
| `test-herdr-status.bash::test_herdr_toml` | 色・キー・トークンの変更、組み込みトークンの使用 | 削除 | 型 3 | 不要 | |
| `test-herdr-status.bash` の `[ -x ]`（7 箇所） | 実行権限の欠落 | 削除 | 重複 | 同じファイルの実行テスト（直接実行する） | |
| `<hm>::test_config_and_syntax` | 設定値・関数名の変更、tmux の再混入、修復と起動の順序 | 削除 | 型 2・3・4。`zsh -n` は重複 | 起動先の cwd は `<hm>::test_launch_and_guards`（herdrstart の `cd` を消すと失敗）。`zsh -n` は `test-shell-tools.bash`。ほかは不要 | |
| `<hm>::test_launch_and_guards` | TTY 以外・herdr の中での起動、起動先の誤り | 維持 | 実行 | — | |
| `<hm>::test_session_cwd_repair`・`::test_session_cwd_repair_multi_workspace` | 起動中のセッションの書換え、一時ファイルの残留、誤った修復先 | 維持 | 実行 | — | |
| `<hm>::test_installer_wiring` | postCreate の手順・URL・順序の変更、tmux・bun・headroom の再混入 | 削除 | 型 2・3・4 | 不要 | |
| `<hm>::test_cc_launcher_env_unsets` の unset 一覧と汚染の実行 | 親シェルの認証情報・モデル指定の漏れ | 理由付き固定値として維持 | 認証の隔離。理由は記載済み | — | #36 |
| `<hm>::test_cc_launcher_env_unsets` の配列の宣言・共有回数・`claude-alibaba` の禁止・抽出 helper の検査・ccdu のモデル値 | 共有リストの使い忘れ、撤去した関数の再追加 | 削除 | 共有回数は汚染の実行と重複。型 2・3・5 | 汚染の実行（ccdu が共有リストを使わないと失敗）。`-u MAAS_ANTHROPIC_TOKEN` の追加は unset 一覧の比較で失敗 | #17 |
| `<hm>::test_cc_launcher_arguments_and_models` の `ccd`・`ccdo`・`ccds` | alias の引数の分割・転送の誤り | 維持 | alias の定義と実行の比較 | — | #36 |
| `<hm>::test_cc_launcher_arguments_and_models` のプロバイダ関数 | 引数の分割、権限フラグ、資格情報の送り先と渡し方、claude.ai の MCP の有効化 | 書き換え（モデル名・調整値の照合を削除） | モデル名・調整値は型 3。送り先・渡し方・MCP の無効化は秘密情報の保護として固定値。理由を追記 | — | #36 |
| `<hm>::test_cc_launcher_auth_and_exit_status` | 資格情報なしでの起動、終了コード・親の環境の変更、キーの優先順位 | 維持 | 実行 | — | |
| `test-initialize-mounts.bash` の 1・3・3b・4・5 | mount と作成の食い違い、`~/.claude.json` の破壊、書き込み可能化の漏れ | 維持 | 実行と定義元の比較 | — | |
| `test-initialize-mounts.bash` の 2（mount 一覧） | mount の増減 | 理由付き固定値として維持 | 永続領域・秘密情報の露出。理由を追記 | — | #36 |
| `test-initialize-mounts.bash` のコンテナ名・PATH | 設定値の変更 | 削除 | 型 3 | 不要 | |
| `test-install-beforehand.bash` の `bash -n` とプラグインの集合 | 構文の誤り、`enabledPlugins` との食い違い | 維持 | 構造、定義元との比較 | — | |
| `test-install-beforehand.bash` のプラグイン名 2 件・Codex・uv の順序・旧拡張・python3・重複・Issue 番号 | 手順の変更 | 削除 | 型 2・3・4 | cleanup と拡張の導入の順序は `<py>::test_provisioning_cleans_before_installing_only_retained_extensions`（cleanup を後ろへ移すと失敗）。ほかは不要 | |
| `test-install-resoloop.bash`・`test-report-resoloop-skills.bash`・`test-resoloop-tool.bash` | 版の取り違え、導入失敗の見逃し、別のパッケージとの一致、表示と終了コードの誤り | 維持 | スクリプトの実行 | — | #41 |
| `<cx>::test_launchers_accept_tilde_agent_dir`・`::test_missing_oauth_guides_login` | OAuth の探索の誤り、未認証での起動 | 維持（旧い案内文と API キーの不在の 2 件は削除） | 実行。消した 2 件は型 2 | — | |
| `<cx>::test_setup_places_independent_tiers_from_source` | tier の配置の誤り | 削除 | 重複 | `<sa>::test_setup_places_all_launcher_configs`（setup から piga を外すと失敗） | |
| `<cx>::test_launchers_select_models_and_forward_arguments` | 引数・tier 設定の bind の誤り、実行権限 | 削除 | 重複。実行権限は型 3 | `<sa>::test_launchers_select_regular_and_forward_user_arguments`、`<sa>::test_launchers_wrap_pi_with_their_own_config`（piga に pigs の設定を使わせると失敗） | |
| `<cx>::test_install_places_all_launchers_with_regular_mode` | postCreate の配置漏れ・権限・引数の誤り | 書き換え（ランチャーを定義元から列挙） | 一覧は型 3 | — | |
| `<cx>::test_live_openai_codex_models` | 実環境で解決できないモデル | 維持 | `PI_CODEX_LIVE_CHECK=1` のときだけ動く。定義元から読む | — | |
| `<sa>` の helper の実行テスト（bwrap・bind・dry-run・fail-closed の 7 関数） | bind の取り違え、設定・bwrap 無しでの起動、dry-run での実行 | 維持 | 実行 | — | |
| `<sa>::test_helper_exists` | helper の欠落 | 削除 | 重複 | helper を source する各テスト | |
| `<sa>::test_commandcode_models_are_defined_in_pi_models`・`::test_opencode_go_tiers_use_opencode_go`・`::test_configs_are_minimal_partial_configs` | 未定義のモデル、provider の誤り、部分 config の崩れ | 維持 | 定義元の比較・構造 | — | #36 |
| `<sa>::test_configs_hold_no_secrets`（旧 `test_no_deepinfra_and_no_secrets`） | tier 設定の秘密情報 | 理由付き固定値として維持（DeepInfra の禁止は削除） | 秘密情報。DeepInfra は型 2。理由を追記 | — | |
| `<sa>::test_launcher_files_are_executable` | ランチャーの git モード | 削除 | 型 3（ランチャー一覧）。tests/scripts と同じ判断 | postCreate で置いた後の権限は `<cx>::test_install_places_all_launchers_with_regular_mode`（`install -m 0644` にすると失敗） | |
| `<sa>::test_launchers_wrap_pi_with_their_own_config` | 別のランチャーの tier 設定の bind | 書き換え（定義元から列挙し、piga・pigs・pigl も対象） | 一覧は型 3 | — | |
| `<sa>::test_launchers_preserve_parent_model_selection` | 親モデル・引数の誤り | 削除 | 重複 | `<sa>::test_launchers_select_regular_and_forward_user_arguments`（pigo のモデル指定を変えると失敗） | |
| `<sa>::test_launchers_select_regular_and_forward_user_arguments` | regular の指定・引数の転送の誤り | 書き換え（定義元から列挙） | 一覧は型 3 | — | |
| `<sa>::test_opencode_key_reaches_child_process`・`::test_commandcode_key_check_runs_before_launch`・`::test_launcher_missing_config_fails_closed`・`::test_pigou_missing_provider_def_fails_with_guidance` | 資格情報の受け渡し、鍵・設定・provider 無しでの起動 | 維持 | 実行 | — | |
| `<sa>::test_pixg_oauth_guidance` | OAuth 無しでの起動、`~` の展開 | 維持（文言の 3 件は削除） | 実行。`SuperGrok`・`XAI_API_KEY` の文言は型 1・2、Codex の案内の不在は直後の引数の比較と重複 | — | |
| `<sa>::test_pigou_missing_model_def_fails_with_guidance`・`::test_pigou_models_json_uses_home_fallback` | 未定義のモデルでの起動、フォールバック先の誤り | 書き換え（モデル名を pigou の呼出しから読む） | モデル名は型 3 | — | |
| `<sa>::test_run_launcher_ignores_external_pi_coding_agent_dir` | （テストの helper の誤り） | 削除 | 型 5 | 不要 | |
| `<sa>::test_setup_places_all_launcher_configs`・`::test_setup_leaves_user_settings_untouched` | 配置漏れ、利用者の settings の変更 | 書き換え（ランチャーを定義元から列挙） | 一覧は型 3 | — | |
| `<sa>` のほかの setup の実行テスト（バックアップ・世代・冪等・`--if-absent` の 4 関数） | 利用者の設定の上書き・消失 | 維持 | 実行 | — | |
| `<sa>::test_setup_output_mentions_each_launcher` と setup 2 本の完了表示の検査 | 表示の文言 | 削除 | 型 1・3 | 不要 | |
| `<sa>::test_install_script_drops_pi_subagents`・`::test_install_script_installs_pi_superagents` | 置換・導入の誤り | 削除 | 型 4。実行テストと重複 | `<sa>` の `install_pi_extensions` の実行テスト（導入先を `npm:pi-subagents` にする、lock を見なくすると失敗） | |
| `<sa>::test_install_script_seeds_launcher_configs` | rebuild で利用者の tier 設定を置き換える | 理由付き固定値として維持 | 利用者所有部分。理由を追記 | — | |
| `<sa>` の `install_pi_extensions` の実行テスト（10 関数） | 旧拡張の残留、導入失敗の見逃し | 維持 | 実行 | — | |
| `<sa>::test_pixg_live_model` | 実環境で解決できないモデル | 維持 | `PI_XAI_LIVE_CHECK=1` のときだけ動く。定義元から読む | — | |
| `<sa>::test_readme_documents_the_mechanism` | README の文言 | 削除 | 型 1・3 | 不要 | |
| `test-readme.bash` の表と実装の比較 | 表と実装の食い違い | 維持 | 定義元と配置先の比較 | — | #36 |
| `test-readme.bash` の `/workspaces/reso-world` の禁止 | worktree・別の checkout から親の checkout を操作する | 理由付き固定値として維持 | 誤対象の操作。理由を追記 | — | |
| `test-readme.bash` の `maatlog`・Issue 番号・`project_doc_fallback_filenames`・撤去したエージェントの禁止 | 移植元の名残、撤去した設定の再導入 | 削除 | 型 2。`maatlog` は重複 | `maatlog` は `tests/skills/test_legacy_references.py`（`zshrc.txt` に足すと失敗）。`~/.dsh` の mount は `test-initialize-mounts.bash` の 2、`-u MAAS_ANTHROPIC_TOKEN` は `<hm>` の unset 一覧（どちらも足すと失敗）。ほかは不要 | #17, #36 |
| `test-resonite-feature.bash` | .NET の Feature・PATH・Blender の設定の変更 | 削除 | 型 3・4 | 不要 | |
| `test-shell-tools.bash` の実行テスト | 未導入ツールでの失敗、更新対象の誤り、秘密情報の読込み、`.venv` の探索 | 維持 | 実行 | — | |
| `test-shell-tools.bash` の `/home/vscode` の禁止 | 実際の HOME を操作する | 理由付き固定値として維持 | 誤対象の操作。理由を追記 | — | |
| `test-shell-tools.bash` の `update: grok` の不在 | 撤去したツールの更新 | 削除 | 型 2 | 不要 | #17 |
| `test-verify-resonite-tooling.bash` の 1・2 と `STEP_TOTAL` | 版の未確認、失敗の見逃し、進捗の総数の誤り | 維持 | 実行と構造 | — | |
| `test-verify-resonite-tooling.bash` の postCreate の呼出しと zshrc の PATH | 手順・PATH の変更 | 削除 | 型 4 | 不要 | |
| `<py>` の cleanup_pi_mcp.py・pi_json.py・provider setup の実行テスト | 誤対象の削除、中断時の残留、link の追従、資格情報の権限、利用者の設定の消失 | 維持 | 実行（安全条件） | — | #19 |
| `<py>::test_provisioning_cleans_before_installing_only_retained_extensions`・`::test_fresh_provisioning_and_rerun_install_only_retained_extensions` | cleanup の遅れ、撤去した拡張の再導入、利用者の宣言の消失、再実行での変化 | 書き換え（導入する拡張の一覧の照合を削除） | 一覧は型 3 | — | #19 |
| `<py>::test_provisioning_stops_on_cleanup_failure` | cleanup の失敗後の導入 | 書き換え（拡張名の不在 → 宣言が変わらないこと） | 拡張名は型 3。その拡張を一覧から外すと空振りする | — | |
| `<py>::test_project_builtin_mcp_settings_are_shared_with_worlds` | `.pi` の設定値の変更、ワールドの `.pi` の link 切れ | 削除 | 型 3（設定値・ワールド一覧） | link は check-layout（`slum03/.pi` の行き先を変えると失敗） | |
| `<py>::test_deepinfra_setup_does_not_reintroduce_distill_and_preserves_custom_models` の `pi-models.json` の検査 | 撤去した provider の再追加 | 削除（setup の実行は維持） | 型 2 | 不要 | #19 |
| `.devcontainer/tests/fake_pi_packages.py` | — | 維持 | `<py>` が使う | — | |

前後: ファイル シェル 17→16・Python 2→2（うち helper 1）、行 シェル 3,593→3,069・Python 1,837→1,818、収集 unittest 80→79（run-tests はファイル単位で 17→16）、所要 `bash .devcontainer/run-tests.bash .devcontainer/test-*.bash` が変更前 2 回で 50〜59 秒（1 回はファイル別の秒数の合計）→変更後 3 回で 49〜55 秒（大半は `test-pi-mcp-cleanup.bash` の 28〜36 秒で、変更前後とも揺れる）

## MyResoniteProject・akichi

`<mp>` は `MyResoniteProject/tests/tokyo_nova/`、`<ak>` は `akichi/tests/akichi/` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号。「代わりの保証」には、変異を入れた一時コピーで失敗することを確かめた検査だけを書く。シェルのテストは無い。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `<mp>test_ground_topology.py` | 地面の切り欠き・支持の誤り、地下への開口の塞ぎ、着地面の深さの誤り | 維持 | 生成した manifest の形状と collider の検査 | — | |
| `<mp>test_layout.py` の import の分岐と `assertIsNotNone`（`setUpClass`・`build_layout`） | （モジュールの未実装） | 削除 | TDD の RED 用の分岐。モジュールがあるので到達しない | 不要（モジュール・関数が無ければ import か属性参照で失敗する。`build_layout` の名前を変えると失敗することを確認） | |
| `<mp>test_layout.py::test_blockout_manifest_has_owned_root_and_stable_geometry_keys` の所有キー | 所有キーの変更 | 理由付き固定値として維持 | 既存の state と Resonite 上の所有ルートの対応。理由を追記 | — | |
| `<mp>test_layout.py` のほか（11 関数） | 広場への侵入、経路の本数・幅、キー・兄弟スロット名の重複、扉の開口、スロープの向き、展開ノード数の不足、看板の重複追加 | 維持 | 生成した layout・manifest の検査。`validate_layout` と同じ条件も含むが、`validate_layout` の規則の多くには検出の試験が無い | — | |
| `<mp>test_pipeline.py` の `getattr`・`callable` の確認 | （関数の未実装） | 削除 | TDD の RED 用。到達しない | 不要（`prepare_probe_manifest` の名前を変えると AttributeError で失敗することを確認） | |
| `<mp>test_pipeline.py::test_probe_manifest_is_scoped_with_resolvable_assets_and_japanese_capture` | プローブの所有キー・`ResoLoop_Test_*` の名前の誤り、asset の参照切れ | 理由付き固定値として維持 | 本体と別の所有範囲で試す安全条件（`AGENTS.md` の Resonite safety）。理由を追記 | — | |
| `<mp>test_probe.py` の `japanese_sign_strategy` | report の説明文の変更 | 削除 | 型 3（`probe.py` の定数の写し） | 不要 | |
| `<mp>test_probe.py` のほか | Blender で保存できない、テクスチャ・UV・法線・寸法の誤り | 維持 | Blender の実行（`resoloop blender run`） | — | |
| `<mp>test_assets.py::test_phone_assembly_has_repairable_physical_parts`（旧 `test_phone_assembly_is_dimensional_and_has_repairable_physical_parts`）の全体寸法 | 電話の全体寸法の誤り | 削除（部品の検査は維持し、関数名から寸法を外した） | 重複 | `<mp>test_task2_fix_round1.py::Task2FixRound1Tests::test_phone_details_are_exposed_inside_exact_overall_dimensions`（電話の長さを 0.150→0.152m にすると失敗） | |
| `<mp>test_assets.py` の `materials.ADAPTATION_NOTE` | 文書が参照する定数の削除 | 維持 | `docs/worlds/tokyo-nova/tokyo-nova-assets.rst` が参照先として挙げる定数の実在 | — | |
| `<mp>test_assets.py::test_catalog_records_finished_asset_design_and_exact_phone_scale` の除外語 | 人型・決済・IANUS・監視などの資産の混入 | 維持 | 生成した資産カタログの内容の制限。受入条件かどうかの記録が無く、消さずに残した | — | |
| `<mp>test_assets.py` のほか | 形状・資源 report・決定性・材質・合成の誤り | 維持 | 生成処理の実行 | — | |
| `<mp>test_task1_fix_regressions.py::test_every_building_front_door_has_an_outward_route_approach` の専用通路 3 本の集合 | 通路データの変更 | 削除 | 型 3。扉への接近は同じ関数の前半が検査する | 同じ関数の `missing == []`（`alley_west_game_room_access` を消すと失敗。`building_access_key` だけを外す変更では、削除した集合の比較だけが失敗した） | |
| `<mp>test_task1_fix_regressions.py::test_prop_catalog_omits_payment_live_stage_and_natural_roof_garden_near_misses` | レビューで除いた小物（決済・ライブ舞台・自然の屋上庭園）の再追加 | 維持 | 型 2 の形だが、内容の制限として残した。受入条件かどうかの記録が無い | — | |
| `<mp>test_task1_fix_regressions.py` のほか（11 関数） | 所有ルートの位置、建物の重なり、経路の建物への侵入、扉への接近、地下の深さ・開口、スロープの接地、カメラの高さ、証跡の上書き | 維持 | 生成した layout・manifest を `validate_layout` と別の実装で検査する。証跡の上書きは安全条件 | — | |
| `<mp>test_task2_fix_round1.py::test_north_phone_back_rests_on_the_repair_mat` | 電話が修理マットから浮く・沈む | 削除 | 重複 | `::test_phone_footprint_is_inside_mat_and_rests_on_its_top`（電話を 0.01m 浮かせると失敗） | |
| `<mp>test_task2_fix_round1.py` のほか（12 関数） | 閉じていない mesh、電話の寸法・部品のはみ出し、見えない壁、collider と形状の食い違い、通路の塞ぎ、看板の向き、部品の重なり・接地、カタログと配置の食い違い | 維持 | 生成処理の実行。レビュー指摘の再発防止 | — | |
| `<mp>test_task3_city.py` の `getattr` と `fail` | （関数の未実装） | 削除 | TDD の RED 用。到達しない | 不要（`build_city` の名前を変えると AttributeError で失敗することを確認） | |
| `<mp>test_task3_city.py` のほか（4 関数） | 施設・内装・建物の欠落、広場への collider の侵入、扉の塞ぎ、支えの無い小物、階段の不連続、全体の空の変更、置き換えない blockout の無効化 | 維持 | 生成処理の実行 | — | |
| `akichi/tests/__init__.py`、`<ak>__init__.py` | — | 維持 | テストをパッケージとして import する | — | |
| `<ak>test_build_helpers.py::test_ads_sector_keeps_cables_8_to_12` の `NIGHTLIFE_TOWERS` との共通部分 | ads セクタへの夜の街の広告の混入 | 削除 | 恒真（広告名 `ad-NN` と塔の ID `tower-NN` は交わらない） | `::test_ads_split_covers_all_ads_exactly_once`（ads セクタに夜の街の広告を残すと失敗。削除した行はこの変異でも通った） | |
| `<ak>test_build_helpers.py::test_vacant_sector_composition` の未使用の `vmin`・`vmax` | （なし。「空地の内側」とコメントにあるが検査していない） | 削除 | 使わない変数（ruff F841）。コメントを検査の内容に合わせた | 不要 | |
| `<ak>test_build_helpers.py` のほか | 座標変換・batch の誤り、セクタの取りこぼし・重複、非決定性、パレット外の材質、三角形数の超過、report の集計の誤り | 維持 | 生成処理の実行。セクタの件数は生成コードの定数と対で変わるが、取りこぼし・重複を検出する | — | |
| `<ak>test_buildings.py` | 塔の非決定性・寸法・接地の誤り、鉄筋・錆筋の有無、低層での例外 | 維持 | 生成処理の実行。低層の例外は c025abb で直した不具合 | — | |
| `<ak>test_geometry.py` | 閉じていない box、円柱・屋根の形、不正な入力の受理、UV の誤り | 維持 | 生成処理の実行 | — | |
| `<ak>test_layout.py::test_layout_counts` | 件数の変更 | 削除 | 型 3（`layout.py` の定数の写し） | 不要 | |
| `<ak>test_layout.py::test_vacant_lot_is_clear` | 塔の空地への侵入 | 削除 | 重複（`validate_layout` の項目 3 と同じ条件で、回転を見ない分だけ弱い） | `::test_layout_validates_clean`（塔を空地に置くと失敗）。検出は `::test_validator_detects_intrusion` も確かめる | |
| `<ak>test_layout.py` のほか（5 関数） | 非決定性、配置の検証の失敗、屋上広告の高さ、検証の見逃し、ID の重複 | 維持 | 生成処理の実行 | — | |
| `<ak>test_materials.py` の `len(mats) == 27` | パレットの件数の変更 | 削除 | 型 3（c025abb でその時点の件数に固定した値） | 使う材質がパレットから消えた場合は `<ak>test_props.py::test_props_use_only_palette_materials`・`<ak>test_build_helpers.py::test_batch_materials_all_exist_in_palette`（`rust` を消すと失敗）。材質を足す変更では suite 全体が通る | |
| `<ak>test_materials.py` のほか | export できない値・キー、ネオンの非発光、共有される dict | 維持 | 実行 | — | |
| `<ak>test_pipeline.py::test_manifest_structure` | 所有キー・所有ルート・セクタのスロットの誤り | 理由付き固定値として維持 | 既存の state と適用済みコンテンツの対応。理由を追記 | — | |
| `<ak>test_pipeline.py::test_signs_attached` | 看板の欠落・重複・文言の誤り | 書き換え（JSON の `in` の照合 → layout の看板との比較） | 1 枚の文言の写しと型名の有無だけを見ていた | — | |
| `<ak>test_pipeline.py::test_cameras_and_tests_present` | カメラの数・代表の指定・テスト名の変更 | 削除 | 型 3（`CAMERAS` 定数と固定のテスト名の写し） | 不要 | |
| `<ak>test_pipeline.py::test_manifest_component_type_counts` と `REAL_COMPONENT_COUNTS`・`REAL_ASSET_COUNT` | コミット済み manifest の件数の変更 | 削除 | 型 3。コミット済みの生成物を読むだけでパイプラインを実行しない（再利用・参照の書き換えを壊しても通った）。内容を変えるたびに期待値を対で直す | 合成 bundle の 4 テスト（再利用を止めると `::test_merge_reuses_shared_provider`、参照の書き換えを止めると `::test_merge_references_follow_renames` が失敗）。実 manifest の参照切れは `::test_manifest_references_resolve` | |
| `<ak>test_pipeline.py` のほか（6 関数） | 非決定性、参照切れ、キーの衝突・再利用・刈り込み・参照の追従の誤り | 維持 | 実行と参照先の実在 | — | |
| `<ak>test_props.py` | 非決定性、接地・寸法の誤り、屋上広告の脚の浮き、退化入力の受理、パレット外の材質 | 維持 | 生成処理の実行。屋上広告の脚は akichi の Task 5 で直した不具合 | — | |

前後: ファイル Python 17→17（テスト 15・`__init__.py` 2）、行 MyResoniteProject 1,492→1,459・akichi 940→892、収集 MyResoniteProject 52→51・akichi 66→62、所要は隔離コピーの変更前と交互に 3 回実行して MyResoniteProject 4.5〜5.0 秒→4.5〜4.6 秒（大半は `test_probe.py` の Blender と `test_task3_city.py`）・akichi 1.4〜1.5 秒→1.3〜1.4 秒

## slum02

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |

## slum03

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
