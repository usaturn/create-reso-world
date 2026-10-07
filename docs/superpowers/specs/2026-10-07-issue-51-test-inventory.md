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
| `<py>::test_the_unittest_suite_is_wired_into_the_existing_ci_runner` | runner の配線漏れ | 削除 | 型 4。wrapper を消すとこの検査も実行されなくなり、検出できない | run-tests.bash が `tests/scripts/*.bash` を glob で列挙する | #36 |
| `<py>::ImportedDocumentPortabilityTests`（3 関数） | SHA 照合が Git の履歴に依存する・変更を検出しない | 削除 | テスト自身（SHA 照合）しか検査しない。照合は作業ツリーのバイトだけを読む | SHA 照合は維持。Git の無いコピーで通ること、文書の変更で失敗することを今回確かめた | #36 |
| `<py>::EndToEndLifecycleTests::test_committed_version_and_resume_gate_eval_cases` | 再開判定表の誤り | 書き換え（`::test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked`） | handoff はテストが書いて読み戻すだけ、resolver の実行は重複。承認・許可の無い 5 ケースを ready にしない判定だけ理由付き固定値として残す | resolver は `test_superpowers_context.py::test_head_remote_preserves_no_pushurl_fallback` | #36 |
| `<py>::EndToEndLifecycleTests::test_supported_route_reaches_simulated_publication_with_versioned_copies` | コピーの作成・非置換の誤り | 削除 | 実行部分は review-copy・context のテストと重複。承認記録・公開・復元はテストが書いた値を読み戻すだけ | `test-superpowers-review-copy.bash`、`test_superpowers_review_copy.py::test_new_versioned_name_leaves_the_old_copy_untouched`・`::test_committed_plan_copies_with_exact_bytes_full_sha_and_kind_flow`、`test_superpowers_context.py::test_document_main_and_linked_roots_verify_requested_branch` | |
| `<py>::EndToEndLifecycleTests::test_unsupported_external_implementation_route_records_blocked_state` | （なし） | 削除 | テストが書いた handoff を読み戻すだけ | 不要 | |
| `tests/scripts/test_superpowers_context.py` | 誤った checkout・remote の選択、認証情報の表示、Git の状態の変更 | 維持 | resolver の実行 | — | PR #16 |
| `test_superpowers_context.py::test_missing_unsupported_or_foreign_parent_origin_has_actionable_error` | 別ホストの scp 形式の origin を受け入れる | 統合 | `test-superpowers-review-copy.bash` の 12 だけが持っていた失敗ケースを移した | — | |
| `tests/scripts/test_superpowers_review_copy.py` | 既存コピーの差し替え、未コミットの正本、symlink・FIFO への書込み、競合 | 維持 | モジュールの実行 | — | PR #16 |
| `tests/scripts/test-superpowers-review-copy.bash` の 2〜14 | 同上（ラッパー経由） | 削除 | 同じモジュールの同じケースを Python のテストが実行する | `test_superpowers_review_copy.py` の対応するテスト。remote の形式・checkout のルートは `test_superpowers_context.py` | |
| `tests/scripts/test-superpowers-review-copy.bash` の 1 | ラッパーがモジュールを起動できない | 維持 | 利用者が実行するラッパーの唯一の実行 | — | |
| `tests/scripts/test-agent-config.bash` の Codex の `context7` 名 | ユーザー設定の context7 と項目が混ざる | 理由付き固定値として維持 | 8a95021 で直した不具合の再発防止 | — | |
| `test-agent-config.bash` の Codex の `env_vars` | 外部パッケージへ渡す秘密情報が増える | 理由付き固定値として維持 | 秘密情報の露出範囲。理由を追記 | — | |
| `test-agent-config.bash` の Codex・Cursor の command・args とマージの再現 | 設定値の変更 | 削除 | 型 3。マージの再現はテスト自身の計算で、名前の検査以上のことを検出しない | 名前の検査 | |
| `test-agent-config.bash` の `.pi-lens.json`（`$schema`・ignore） | `$schema` の再追加、ignore の変更 | 削除 | 型 2・3 | 不要 | #19 |
| `test-agent-config.bash` の `sp-implementer.md`・`.devin/config.json` | model・一覧の変更、作らない設定ファイル | 削除 | 型 2・3 | `sp-implementer.md` の実在は check-layout（プロジェクトの symlink が行き先を要求する） | |
| `tests/scripts/test-ci.bash` の trigger・job・コマンド・action の版・Blender | CI 定義の変更 | 削除 | 型 3。誤りは CI の実行で失敗として表に出る | 不要 | |
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
| `test-instructions.bash` の `.pi/APPEND_SYSTEM.md` の撤去したスキル・`@.agents/skills/`・`PI_DISTILL_MODEL`・`async: false` | 撤去した記述の再出現 | 削除 | 型 2。旧引数は role API が受け付けないだけで、誤対象の操作にならない | スキル名は `test-docs.bash --refs` が実在を見る | #19 |
| `tests/scripts/test-check-layout.bash` の 6 と 44 | このリポジトリの配置の誤り、mounts の検査の skip | 統合（44 を 6 にまとめた） | 同じリポジトリで check-layout を 2 回実行していた | — | |
| `test-check-layout.bash` のほか | check-layout の判定・終了コードの誤り | 維持 | スクリプトの実行 | — | |
| `tests/scripts/test-new-world.bash` | 作成・適用の誤り、食い違いでの変更、冪等性 | 維持 | スクリプトの実行 | — | |
| `tests/scripts/test-resoloop-fork.bash` | 誤った remote・push、dirty な checkout の変更、版の誤り | 維持 | スクリプトの実行 | — | #41 |
| `tests/scripts/lib/path.bash`、`tests/scripts/fixtures/superpowers-imported-documents.sha256.json` | — | 維持 | 残る検査が使う | — | |

前後: ファイル Python 3→3・シェル 11→11、行 Python 1,367→1,011・シェル 1,697→1,430、収集 68（subtest 154）→61（144）、所要は隔離コピーで変更前後を交互に 2 回実行して run-tests の `tests/scripts/*.bash` 83〜84 秒→71〜77 秒・`uv run pytest tests/scripts` 46〜51 秒→42〜45 秒。ルート pytest からは同じ 68 件（約 45 秒）の二重実行を外した（収集 542→474）

## .devcontainer

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |

## MyResoniteProject・akichi

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |

## slum02

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |

## slum03

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
