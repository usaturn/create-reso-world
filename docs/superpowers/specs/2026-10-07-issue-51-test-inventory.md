# Issue #51: テスト分類表

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: #51（#36・PR #46 の後続）、PR: 未作成
- 状態: draft
- 基準 HEAD: `a94f04eea41fce3fb344dd4a7f10a7a0692512c2`（PR #48 のマージ後）
- 関連 Plan: `docs/superpowers/plans/2026-10-07-issue-51-test-cleanup.md`
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-51-test-cleanup`（branch `chore/issue-51-test-cleanup`）
- PARENT_ROOT: `/workspaces/reso-world`

## #36 の判断を見直したもの

#36 の Spec（`docs/superpowers/specs/2026-10-06-issue-36-fixed-value-tests-design.md`）で残すとした検査のうち、今回削除・縮小したもの。各行の理由に「#36 では維持。今回見直し」と書いた。

- 第 3 章 A6（3 ファイルの移植元名・撤去ツール・無効設定・旧 API の `lacks`）: `test-docs.bash` の `dsh`、`test-instructions.bash` の `verify.sh`・`verify-devenv`・`AGENTS.md` の 6 語・`.pi/APPEND_SYSTEM.md` の 4 語、`.devcontainer/test-readme.bash` の `maatlog`・Issue 番号・`project_doc_fallback_filenames`・撤去したエージェント
- 第 3 章 A4（過去 Spec/Plan の固定履歴は変更しない）: `test-docs.bash` の凍結した仕様・計画の 7 文字列
- 第 4 章 D 表 `test_superpowers_lifecycle.py`: SHA 照合の portability、runner 配線、E2E の resolver・review-copy・handoff の実行、handoff schema の `document_published`
- 第 4 章 D 表 `test_skill_packages.py`: frontmatter・packaging、layout、委譲境界の guard（`test_no_unapproved_guidance_or_false_runtime_claims`、常に skip していた `test_targeted_skill_semantics`）
- 第 4 章 D 表の各スキル: symlink（agent-handoff・find-docs・herdr-agent-task・planning-parallel-issues・repo-cleanup-after-merge・rst-writer・simplify-in-subagent・stale-git-lock-recovery、pr-review・review-fix-planning の helper）、frontmatter・allowed-tools（agent-handoff・pi-model-name・repo-cleanup-after-merge・review-fix-planning・simplify-in-subagent・stale-git-lock-recovery）、agent-handoff の schema の版、monitoring-long-tasks の 3 件、find-docs のツール固有コマンドの禁止、herdr-agent-task のスクリプトの実在、pi-model-name の実行権限、rst-writer の profile・資源ディレクトリの実在

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
| `tests/skills/test_skill_packages.py::test_targeted_skill_semantics` | 1 スキルの MCP・他エンジン案内 | 削除 | `SKILL_UNDER_TEST` が無いと常に skip。全スキル版と同じ検査。#36 では維持。今回見直し | `::test_no_positive_execution_guidance_in_skills_or_shared_references` | |
| `tests/skills/test_skill_packages.py::test_required_names_and_valid_frontmatter`（`read_skill` の frontmatter 検査を含む） | Blender スキルの欠落・frontmatter の誤り | 削除 | スキル名一覧の写しと共通検査の重複。#36 では維持。今回見直し | `test_skill_frontmatter.py`、`::test_provenance_license_and_document_coverage` の output_paths の実在 | |
| `tests/skills/test_skill_packages.py::test_installed_style_layout_preserves_standard_and_unrelated_content` | （なし） | 削除 | Issue 原則 5。配置処理を呼ばず、コピーした fixture を比べるだけ。#36 では維持。今回見直し | 不要（実行するコードが無い） | #51 |
| `tests/skills/test_skill_packages.py::test_no_unapproved_guidance_or_false_runtime_claims` | 未導入スキル名の記述、seed・fog の説明文の欠落 | 削除 | 型 1・2。存在しないスキルへの委譲は操作を起こさない。#36 では維持。今回見直し | 不要 | #36 |
| `tests/skills/test_skill_packages.py::test_references_and_links_resolve` | 壊れたリンク | 維持（共有 reference の実在の重複は削除） | 参照先の実在 | 共有 reference の実在は provenance の output_paths 検査 | |
| `tests/skills/test_skill_packages.py::test_execution_guidance_guards_cover_positive_and_negative_fixtures` | guard の否定判定の誤り | 維持 | guard が働くことを示す正負の例 | — | #36 |
| `tests/skills/test_skill_packages.py::test_no_positive_execution_guidance_in_skills_or_shared_references` | Blender MCP・他エンジンへの実行案内 | 理由付き固定値として維持 | ResoLoop の外で操作させない安全上の禁止。理由を追記 | — | #36 |
| `tests/skills/test_skill_packages.py::test_provenance_license_and_document_coverage` | 取り込み元 SHA・MIT 表記・出力ファイルの欠落 | 理由付き固定値として維持 | 凍結した取り込み履歴とライセンス表記 | — | |
| `agent-handoff/test_agent_handoff_skill_contract.py::test_skill_does_not_reference_the_removed_generator` | 撤去した CLI 名の再出現 | 削除 | 型 2 | 不要 | |
| `agent-handoff/…::test_skill_declares_claude_code_allowed_tools` | 許可の欠落、旧パスへの許可 | 削除 | 型 3。部分一致は許可の拡大を検出しない。旧パスは型 2。#36 では維持。今回見直し | 許可の型は `test_skill_frontmatter.py` | |
| `agent-handoff/…::test_trigger_queries_have_valid_structure` | eval 入力の型の誤り | 維持（`python-tdd-team` の不存在は削除: 型 2） | eval JSON の構造 | — | |
| `agent-handoff/…::test_schema_is_version_2_and_documents_the_authored_fields` | 版の変更、受け手に渡すキーの欠落 | 版の固定は削除（型 3）、キー検査は理由付き固定値として維持（`::test_schema_documents_the_authored_fields`） | decisions・out_of_scope・verification・landing は触ってはいけない範囲・検証・反映先を渡す。版の固定は #36 では維持。今回見直し | — | #36 |
| `agent-handoff/…::test_every_referenced_path_exists` | 存在しないパスの案内 | 維持 | 参照先の実在（過去の不具合の再発防止） | — | |
| `agent-handoff/…::test_schema_maps_review_fix_planning_hold_to_deferred` | Hold が fix・skip に変わる | 理由付き固定値として維持 | 人の判断待ちを実行・放棄に変えない | — | |
| `agent-handoff/…::test_evals_json_uses_expectations_not_assertions` | 採点基準の無い eval、旧キー | 維持（`::test_evals_json_has_expectations`。`assertions` の不存在は削除: 型 2） | eval JSON の構造 | — | |
| `agent-handoff/…::test_schema_requires_git_branch_head_status_in_json_fields` | 作業 checkout の情報の欠落 | 理由付き固定値として維持 | 誤った checkout での操作を防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_schema_allows_null_sources_spec` | spec の null が許されない | 理由付き固定値として維持 | 存在しない Spec パスの捏造を防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_documents_and_code_have_separate_schema_fields` | 文書とコードの root の混同 | 理由付き固定値として維持 | 別の checkout へのコミットを防ぐ。理由を追記 | — | #36 |
| `agent-handoff/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `find-docs/test_find_docs_contract.py`（ファイル削除）`::test_common_instructions_do_not_embed_tool_specific_commands` | `AGENTS.md` の `npx ctx7` | 削除 | 型 1。#36 では維持。今回見直し | 不要 | #36 |
| `find-docs/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `herdr-agent-task/test_herdr_agent_task_contract.py::test_command_script_exists` | コマンドの欠落 | 削除 | 重複。#36 では維持。今回見直し | `::test_states_match_the_command` がスクリプトを読む | |
| `herdr-agent-task/…::test_states_match_the_command` | 文書の状態とコマンドが受け付ける状態の不一致 | 維持 | 定義元と配置先の比較 | — | |
| `herdr-agent-task/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `monitoring-long-tasks/test_monitoring_long_tasks_skill_contract.py`（ファイル削除）`::test_runtime_skill_copies_are_byte_identical` | 2 経路の内容の不一致 | 削除 | 型 5（symlink の両経路で同じ実体）。#36 では維持。今回見直し | check-layout | #51 |
| `monitoring-long-tasks/…::test_claude_loads_the_shared_instructions` | `CLAUDE.md` の読み込み指定の欠落 | 削除 | 重複。#36 では維持。今回見直し | `tests/scripts/test-instructions.bash`（`CLAUDE.md` の 1 行目） | #51 |
| `monitoring-long-tasks/…::test_runtime_instructions_do_not_reference_removed_scripts` | `scripts/ci/` の再出現 | 削除 | 型 2。#36 では維持。今回見直し | `test_legacy_references.py`（`scripts/ci/verify`・`verify.sh`） | |
| `pi-model-name/test_pi_model_name_contract.py::test_frontmatter` | name・description の誤り | 削除 | 共通検査の重複。#36 では維持。今回見直し | `test_skill_frontmatter.py` | |
| `pi-model-name/…::test_script_executable` | 実行権限の欠落 | 削除 | 重複。#36 では維持。今回見直し | 実行テストがスクリプトを直接起動する | |
| `pi-model-name/…::test_json_provenance_runtime` | runtime の JSON の誤り | 統合 | 同じ入力・経路 | `::test_json_without_session_path_reports_unchecked` | |
| `pi-model-name/…` のほかの実行テスト | 解析・優先順位・fail-closed の誤り | 維持 | スクリプトの実行 | — | |
| `planning-parallel-issues/test_planning_parallel_issues_contract.py::test_referenced_procedures_exist` | 壊れたリンク | 維持 | 参照先の実在 | — | |
| `planning-parallel-issues/…::test_validation_links_and_scenarios_resolve` | 壊れたリンク、scenarios の構造、`scripts/ci/` | 維持（`scripts/ci/` の不存在は削除: 型 2） | 参照先の実在・eval 構造 | `test_legacy_references.py` | |
| `planning-parallel-issues/…::test_explicit_path_and_skill_references_exist` | 存在しないパス・スキルの案内 | 維持 | 参照先の実在 | — | |
| `planning-parallel-issues/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `pr-review/test_pr_review_skill_contract.py::test_helper_has_one_real_copy_shared_through_the_skill_symlink` | helper の欠落、symlink、`.devin/skills` | 削除 | 重複・型 5・型 2。#36 では維持。今回見直し | helper は `test_pr_review_workspace.py` が読み込む。symlink・`.devin/skills` は check-layout 検査 4・5 | |
| `pr-review/…::test_skill_interpolation_is_limited_to_the_target_line` | `$ARGUMENTS`・`$N` の置換でコードが壊れる | 維持 | 実行時の展開の誤り | — | |
| `pr-review/…::test_skill_keeps_claude_code_permissions_consistent` | 許可の拡大、`--temp-root` が `/tmp` の外 | 理由付き固定値として維持 | 完全一致の許可リストは権限の境界 | — | #36 |
| `pr-review/…::test_pr_review_skills_have_no_legacy_path_selection` | 旧 devenv の選択の再出現 | 削除 | 型 2・4 | resolver の実行テスト（登録済みの経路・未知のリポジトリでの停止・`CODE_ROOT` の検証） | |
| `pr-review/…::test_review_budget_reference_is_required_and_resolves` | リンク切れ、予算 reference の欠落 | 書き換え（`::test_skill_links_resolve`） | 必須リンクは型 1、パスの一致は定数同士で恒真。リンクの実在だけ残す | — | |
| `pr-review/…` の resolver・preflight の実行テスト | 誤った checkout・remote の選択、停止しない | 維持 | resolver の実行 | — | |
| `pr-review/test_pr_review_workspace.py::test_review_artifact_paths_use_slash_sanitized_model_name` | （なし） | 削除 | 置換済みの名前を渡すだけで隣の検査と同じ経路 | `::test_review_artifact_paths_preserve_exact_model_name`、`::test_create_pins_slash_model_name_as_hyphenated_filename` | |
| `pr-review/test_pr_review_workspace.py::test_create_state_omits_main_snapshot` | 撤去した `main_snapshot` の再出現 | 削除 | 型 2・3 | `::test_save_allows_unrelated_main_changes` | |
| `pr-review/test_pr_review_workspace.py` の 3 関数の `state["version"] == 6` | 版の変更 | 削除 | 型 3 | create と load_state の版の不一致は save の往復（`::test_save_uses_only_pinned_paths` ほか）、旧版の拒否は `::test_load_state_rejects_previous_version` | |
| `pr-review/test_pr_review_workspace.py` のほかの実行テスト | 誤った保存先・後始末・中断・lock の誤り | 維持 | helper の実行 | — | #39 |
| `repo-cleanup-after-merge/test_repo_cleanup_after_merge_contract.py::test_allowed_tools_cover_the_commands_the_steps_run` | 許可の欠落 | 削除 | 型 3。部分一致は許可の拡大を検出しない。#36 では維持。今回見直し | 許可の型は `test_skill_frontmatter.py` | |
| `repo-cleanup-after-merge/…::test_related_skills_exist` | 存在しないスキルの案内 | 維持 | 参照先の実在 | — | |
| `repo-cleanup-after-merge/…::test_evals_have_valid_structure_and_existing_files` | eval 構造・fixture の欠落 | 維持 | eval 構造・参照先の実在 | — | |
| `repo-cleanup-after-merge/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `repo-cleanup-after-merge/test_detached_update.py::test_cleanup_keeps_the_forks_local_main_out_of_deletion_candidates` | fork の `main` を削除候補にする | 理由付き固定値として維持 | 利用者所有の基準 ref。理由はテストに記載済み | — | PR #48 |
| `repo-cleanup-after-merge/test_detached_update.py` のほかの実行テスト | 誤対象の更新・削除、失敗時に止まらない | 維持 | 手順のコードの実行 | — | #47, PR #48 |
| `review-fix-planning/test_review_fix_planning_skill_contract.py::test_status_comment_snippet_escapes_heredoc_and_pins_repository` | heredoc でのコマンド実行、別リポジトリへの投稿 | 理由付き固定値として維持 | 成功経路を実行する検査が無く、この検査だけが守る | — | |
| `review-fix-planning/…::test_helper_has_one_real_copy_shared_through_the_skill_symlink` | helper の欠落、symlink | 削除 | 重複・型 5。#36 では維持。今回見直し | helper は `test_upsert_pr_comment.py` が読み込む。symlink は check-layout | |
| `review-fix-planning/…::test_allowed_tools_match_the_verification_and_spec_location` | 許可の欠落、旧パス | 削除 | 型 3。旧パスの不存在は型 2。#36 では維持。今回見直し | 許可の型は `test_skill_frontmatter.py` | |
| `review-fix-planning/…` の context・status の実行テスト | preflight が止まらない、誤った push 先 | 維持 | 手順のコードの実行 | — | |
| `review-fix-planning/test_upsert_pr_comment.py` | 他エージェントのコメントの上書き、別リポジトリへの投稿 | 維持 | helper の実行 | — | |
| `rst-writer/test_rst_writer_contract.py::test_profiles_and_resource_directories_exist` | profile・assets・fixtures の増減、旧 style guide | 削除 | 型 3（一覧の写し）・型 2。#36 では維持。今回見直し | `::test_markdown_links_resolve`・`::test_templates_named_by_the_document_types_exist`・`::test_every_eval_uses_existing_fixture_files` | |
| `rst-writer/…::test_markdown_links_resolve` | 壊れたリンク | 維持 | 参照先の実在 | — | |
| `rst-writer/…::test_templates_named_by_the_document_types_exist` | 存在しないテンプレートの案内 | 維持 | 参照先の実在 | — | |
| `rst-writer/…::test_every_eval_uses_existing_fixture_files` | eval 構造・fixture の欠落 | 維持 | eval 構造・参照先の実在 | — | |
| `rst-writer/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `simplify-in-subagent/test_simplify_in_subagent_contract.py::test_interpolation_is_limited_to_the_target_line` | `$ARGUMENTS`・`$N` の置換でコードが壊れる | 維持 | 実行時の展開の誤り。理由を追記 | — | |
| `simplify-in-subagent/…::test_frontmatter_keeps_only_keys_every_runtime_can_live_with` | argument-hint・subagent の値、allowed-tools の有無 | 削除 | 型 3。YAML リストの allowed-tools は共通検査が拒否する。#36 では維持。今回見直し | `test_skill_frontmatter.py` | |
| `simplify-in-subagent/…::test_claude_code_reads_the_same_skill` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `stale-git-lock-recovery/test_stale_git_lock_recovery_contract.py::test_frontmatter_declares_name_and_trigger_conditions_only` | frontmatter のキー・値 | 削除 | 共通検査の重複とキー集合の写し。#36 では維持。今回見直し | `test_skill_frontmatter.py` | |
| `stale-git-lock-recovery/…::test_bash_snippets_do_not_run_destructive_git_commands` | 利用者の作業を消すコマンド | 理由付き固定値として維持 | 安全上の禁止。理由はテストに記載済み | — | #36 |
| `stale-git-lock-recovery/…::test_skill_never_removes_the_lock_by_hand` | holder の確認を飛ばす `rm` | 理由付き固定値として維持 | 安全上の禁止。理由を追記 | — | |
| `stale-git-lock-recovery/…::test_bash_snippets_do_not_clobber_zsh_special_variables` | zsh で壊れるスニペット | 維持 | 実行時の誤り | — | |
| `stale-git-lock-recovery/…::test_claude_code_reads_the_same_skill_through_a_symlink` | symlink の誤り | 削除 | 型 5。#36 では維持。今回見直し | check-layout | |
| `stale-git-lock-recovery/…` の helper の実行テスト | 生きている holder のロック削除、誤対象 | 維持 | helper の実行 | — | PR #30 |
| `stale-git-lock-recovery/test_ff_merge_keep_untracked.py::test_plain_merge_is_blocked_by_the_fixture` | （なし） | 削除 | Issue 原則 5（fixture と git だけを検査） | `::test_fast_forwards_and_restores_every_conflicting_file` が同じ fixture をスクリプトで実行する | |
| `stale-git-lock-recovery/test_ff_merge_keep_untracked.py` のほかの実行テスト | 未追跡ファイルの消失、誤対象 | 維持 | スクリプトの実行 | — | |

前後: ファイル 19→17（Python のみ、シェル 0）、行 6,529→6,126、収集 510→474（skip 1→0）、所要 95〜106 秒→100〜113 秒（`uv run pytest tests/skills .agents/skills -q` を複数回実測。消した検査は合計 0.3 秒ほどで、幅は `/proc` を走査する stale-git-lock-recovery のテストの揺れ）

## tests/scripts

`<py>` は `tests/scripts/test_superpowers_lifecycle.py` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `pyproject.toml` の testpaths（`tests` → `tests/skills`） | （同じ unittest の二重実行） | 統合 | `test_superpowers_*.py` を run-tests.bash とルート pytest の両方で実行していた。CI の skill-tests・README と同じ範囲にする | run-tests.bash の `test-superpowers-python.bash` | #51 |
| `tests/scripts/test-superpowers-python.bash` | Python のテストが run-tests.bash・CI で実行されない | 維持 | CI の devcontainer-tests が `tests/scripts` の Python を実行する唯一の経路 | — | |
| `<py>::test_current_callers_do_not_invoke_replacement` | 文書が `--replace-from` を案内する | 削除 | 型 1・2 | `test_superpowers_review_copy.py::test_replace_from_is_rejected_before_any_mutation`（変更前に拒否する） | #36 |
| `<py>::test_handoff_schema_separates_approval_current_authority_and_publication` | 承認・実行許可・完了根拠のフィールドの欠落 | 理由付き固定値として維持（`document_published` は削除） | 承認の無い版・許可の無い作業の再開を防ぐ。理由を追記。`document_published` は #36 では維持。今回見直し | `document_published` は agent-handoff の `::test_documents_and_code_have_separate_schema_fields` | #36 |
| `<py>::test_imported_documents_are_unchanged_since_import` | 取り込んだ過去文書の変更 | 理由付き固定値として維持 | 過去文書の SHA manifest | — | #36 |
| `<py>::test_the_unittest_suite_is_wired_into_the_existing_ci_runner` | runner の配線漏れ | 削除 | 型 4。wrapper を消すとこの検査も実行されなくなり、検出できない。#36 では維持。今回見直し | 不要（wrapper があれば run-tests.bash が `tests/scripts/*.bash` の glob で実行し、一覧への書き忘れは起きない。wrapper の削除は検出しない） | #36 |
| `<py>::ImportedDocumentPortabilityTests`（3 関数） | SHA 照合が Git の履歴に依存する・変更を検出しない | 削除 | テスト自身（SHA 照合）しか検査しない。照合は作業ツリーのバイトだけを読む。#36 では維持。今回見直し | SHA 照合は維持。Git の無いコピーで通ること、文書の変更で失敗することを今回確かめた | #36 |
| `<py>::EndToEndLifecycleTests::test_committed_version_and_resume_gate_eval_cases` | 再開判定表の誤り | 書き換え（`::test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked`） | handoff はテストが書いて読み戻すだけ、resolver の実行は重複。承認・許可の無い 5 ケースを ready にしない判定だけ理由付き固定値として残す。handoff・resolver の実行は #36 では維持。今回見直し | resolver は `test_superpowers_context.py::test_head_remote_preserves_no_pushurl_fallback`（外部 CODE_ROOT と head）・`::test_document_main_and_linked_roots_verify_requested_branch`（DOC_ROOT） | #36 |
| `<py>::EndToEndLifecycleTests::test_supported_route_reaches_simulated_publication_with_versioned_copies` | コピーの作成・非置換の誤り | 削除 | 実行部分は review-copy・context のテストと重複。承認記録・公開・復元はテストが書いた値を読み戻すだけ。#36 では維持。今回見直し | `test-superpowers-review-copy.bash`、`test_superpowers_review_copy.py::test_new_versioned_name_leaves_the_old_copy_untouched`・`::test_committed_plan_copies_with_exact_bytes_full_sha_and_kind_flow`、`test_superpowers_context.py::test_document_main_and_linked_roots_verify_requested_branch` | |
| `<py>::EndToEndLifecycleTests::test_unsupported_external_implementation_route_records_blocked_state` | （なし） | 削除 | テストが書いた handoff を読み戻すだけ。#36 では維持。今回見直し | 不要 | |
| `tests/scripts/test_superpowers_context.py` | 誤った checkout・remote の選択、認証情報の表示、Git の状態の変更 | 維持 | resolver の実行 | — | PR #16 |
| `test_superpowers_context.py::test_missing_unsupported_or_foreign_parent_origin_has_actionable_error` | 別ホストの scp 形式の origin を受け入れる | 統合 | `test-superpowers-review-copy.bash` の 12 だけが持っていた失敗ケースを移した | — | |
| `tests/scripts/test_superpowers_review_copy.py` | 既存コピーの差し替え、未コミットの正本、symlink・FIFO への書込み、競合 | 維持 | モジュールの実行 | — | PR #16 |
| `tests/scripts/test-superpowers-review-copy.bash` の 2〜14 | 同上（ラッパー経由） | 削除 | 同じモジュールの同じ分岐を Python のテストが実行する | `test_superpowers_review_copy.py` の対応するテスト（symlink 先へ書かないことは `::test_destination_changed_into_a_symlink_before_publish_does_not_follow`）。remote の形式・checkout のルートは `test_superpowers_context.py` が PARENT_ROOT・CODE_ROOT で検査し、DOC_ROOT も同じ `inspect_checkout`・`_require_origin` を通る。`--name spec.md` そのものの例は無く、名前の検査は別の誤った名前で見る | |
| `tests/scripts/test-superpowers-review-copy.bash` の 1 | ラッパーがモジュールを起動できない | 維持 | 利用者が実行するラッパーの唯一の実行 | — | |
| `tests/scripts/test-agent-config.bash` の Codex の `context7` 名 | ユーザー設定の context7 と項目が混ざる | 理由付き固定値として維持 | 8a95021 で直した不具合の再発防止 | — | |
| `test-agent-config.bash` の Codex の `env_vars` | 外部パッケージへ渡す秘密情報が増える | 理由付き固定値として維持 | 秘密情報の露出範囲。理由を追記 | — | |
| `test-agent-config.bash` の `.pi/mcp.json`・`.mcp.json` の HTTP header | 鍵の直書きによる露出 | 統合 | `.devcontainer/tests/test_pi_mcp_cleanup.py::test_project_builtin_mcp_settings_are_shared_with_worlds` だけが見ていた鍵の直書きの検査を、値が `${NAME}` の環境変数の参照であることだけに絞って移した。秘密情報の露出を防ぐ理由付き固定値で、private の CI は停止中のため gitleaks も動かない。理由をテストに記載 | — | #51 |
| `test-agent-config.bash` の Codex・Cursor の command・args とマージの再現 | 設定値の変更 | 削除 | 型 3。マージの再現はテスト自身の計算で、名前の検査以上のことを検出しない | command・args は不要。マージの再現が狙った混線は、上の名前の検査が見る | |
| `test-agent-config.bash` の `.pi-lens.json`（`$schema`・ignore） | `$schema` の再追加、ignore の変更 | 削除 | 型 2・3 | 不要 | #19 |
| `test-agent-config.bash` の `sp-implementer.md`・`.devin/config.json` | model・一覧の変更、作らない設定ファイル | 削除 | 型 2・3 | `sp-implementer.md` の実在は check-layout の検査 2（4 プロジェクトの symlink が行き先を失うと失敗する）。`test-check-layout.bash` の 6 がこのリポジトリで実行する。model・一覧・`.devin/config.json` は不要 | |
| `tests/scripts/test-ci.bash` の trigger・job・コマンド・action の版・Blender | CI 定義の変更 | 削除 | 型 3（job・コマンド・版の写し）。存在しない action の版は CI の実行で失敗として表に出るが、job やコマンドを消したことは検出しない（意図した変更として差分で見る）。setup-uv の版の固定は c443b5b の回帰防止だった（`astral-sh/setup-uv` には major タグ `v10` が無く、指すと CI が何も実行せずに失敗する）。それでも版の写しであり、存在しないタグは CI の実行で失敗として表に出るので消す | 不要。gitleaks の job を消すと下の検査が失敗する | |
| `test-ci.bash` の gitleaks のジョブと `.gitleaks.toml` | 秘密情報の見逃し、除外の拡大、allowlist が読まれない | 理由付き固定値として維持 | 秘密情報の検出の設定。正規表現は正負の例で実行する。理由を追記 | — | |
| `tests/scripts/test-docs.bash` の参照検査 | 存在しないファイル・スキルの案内 | 維持 | 参照先の実在 | — | #36 |
| `test-docs.bash` の `dsh` | 撤去した dsh の再記載 | 削除 | 型 2。#36 では維持。今回見直し | 不要（未導入のコマンドは実行時に失敗するだけ） | #17 |
| `test-docs.bash` の `docs/integration.md` の文言 | 統合手順の文言の変更 | 削除 | 型 1。2026-10-06 にも更新した現行の文書 | 不要 | |
| `test-docs.bash` の凍結した仕様・計画の 7 文字列 | レビューで直した箇所の書き戻し | 削除 | 型 1・2。修正の反映を一度確かめる検査で、文書の全体は守らない。#36 では維持。今回見直し | 不要（凍結した文書は編集しない） | #36 |
| `tests/scripts/test-file-modes.bash` の glob の対象 | 実行権限の欠落 | 維持 | `scripts/*.sh` などを直接起動する | — | |
| `test-file-modes.bash` のランチャー 9 本 | ランチャーの権限・追跡の漏れ | 削除 | 型 3（ランチャー一覧） | `install_beforehand.bash` が `install -m 0755` で配置し、無ければそこで失敗する | |
| `test-file-modes.bash` の `checked -gt 30` | 対象を 1 件も読まない | 書き換え（`-gt 0`） | 根拠のない件数固定。空の走査だけを検出する | — | |
| `tests/scripts/test-gitignore.bash` | 秘密情報・私的データの追跡、ワールドのデータの追跡漏れ、許可外の追跡例外 | 理由付き固定値として維持 | ignore の範囲と追跡例外。理由を追記 | — | #36 |
| `tests/scripts/test-instructions.bash` の `CLAUDE.md` 1 行目・参照検査 | 読み込み指定の誤り、存在しない参照 | 維持 | 実際の読み込み指定、参照先の実在 | — | #51 |
| `test-instructions.bash` のペルソナ SHA | 利用者所有部分の変更 | 理由付き固定値として維持 | 利用者所有部分 | — | #36 |
| `test-instructions.bash` の `verify.sh`・`verify-devenv` | 移植元のスクリプト名 | 削除 | 重複。#36 では維持。今回見直し | `tests/skills/test_legacy_references.py` | #17 |
| `test-instructions.bash` の `AGENTS.md` の `reStructuredText`・`Gitleaks`・`contingency`・`AskUserQuestion`・`TaskOutput`・`npx ctx7` | 旧リポジトリ・ツール固有の文言 | 削除 | 型 1。誤対象の操作にならない。#36 では維持。今回見直し | 不要 | #36 |
| `test-instructions.bash` の `.pi/APPEND_SYSTEM.md` の撤去した検証記録（`subagent-launch-verification`）・読み込み方式（`@.agents/skills/`）・設定（`PI_DISTILL_MODEL`）・旧引数（`async: false`） | 撤去した記述の再出現 | 削除 | 型 2。#36 では維持。今回見直し | 不要（再導入しても role API が拒否するか無効な記述にとどまり、誤対象の操作・秘密情報の露出にはならない） | #19 |
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
| `<hm>::test_cc_launcher_env_unsets` の配列の宣言・共有回数・`claude-alibaba` の禁止・抽出 helper の検査・ccdu のモデル値 | 共有リストの使い忘れ、撤去した関数の再追加 | 削除 | 共有回数は汚染の実行と重複。型 2・3、抽出 helper の検査は Issue 原則 5 | 汚染の実行（ccdu が共有リストを使わないと失敗）。`-u MAAS_ANTHROPIC_TOKEN` の追加は unset 一覧の比較で失敗 | #17 |
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
| `<sa>::test_run_launcher_ignores_external_pi_coding_agent_dir` | （テストの helper の誤り） | 削除 | Issue 原則 5 | 不要 | |
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
| `test-readme.bash` の `maatlog`・Issue 番号・`project_doc_fallback_filenames`・撤去したエージェントの禁止 | 移植元の名残、撤去した設定の再導入 | 削除 | 型 2。`maatlog` は重複。#36 では維持。今回見直し | `maatlog` は `tests/skills/test_legacy_references.py`（`zshrc.txt` に足すと失敗）。`~/.dsh` の mount は `test-initialize-mounts.bash` の 2、`-u MAAS_ANTHROPIC_TOKEN` は `<hm>` の unset 一覧（どちらも足すと失敗）。ほかは不要 | #17, #36 |
| `test-resonite-feature.bash` | .NET の Feature・PATH・Blender の設定の変更 | 削除 | 型 3・4 | 不要 | |
| `test-shell-tools.bash` の実行テスト | 未導入ツールでの失敗、更新対象の誤り、秘密情報の読込み、`.venv` の探索 | 維持 | 実行 | — | |
| `test-shell-tools.bash` の `/home/vscode` の禁止 | 実際の HOME を操作する | 理由付き固定値として維持 | 誤対象の操作。理由を追記 | — | |
| `test-shell-tools.bash` の `update: grok` の不在 | 撤去したツールの更新 | 削除 | 型 2 | 不要 | #17 |
| `test-verify-resonite-tooling.bash` の 1・2 と `STEP_TOTAL` | 版の未確認、失敗の見逃し、進捗の総数の誤り | 維持 | 実行と構造 | — | |
| `test-verify-resonite-tooling.bash` の postCreate の呼出しと zshrc の PATH | 手順・PATH の変更 | 削除 | 型 4 | 不要 | |
| `<py>` の cleanup_pi_mcp.py・pi_json.py・provider setup の実行テスト | 誤対象の削除、中断時の残留、link の追従、資格情報の権限、利用者の設定の消失 | 維持 | 実行（安全条件） | — | #19 |
| `<py>::test_provisioning_cleans_before_installing_only_retained_extensions`・`::test_fresh_provisioning_and_rerun_install_only_retained_extensions` | cleanup の遅れ、撤去した拡張の再導入、利用者の宣言の消失、再実行での変化 | 書き換え（導入する拡張の一覧の照合を削除） | 一覧は型 3 | — | #19 |
| `<py>::test_provisioning_stops_on_cleanup_failure` | cleanup の失敗後の導入 | 書き換え（拡張名の不在 → 宣言が変わらないこと） | 拡張名は型 3。その拡張を一覧から外すと空振りする | — | |
| `<py>::test_project_builtin_mcp_settings_are_shared_with_worlds` | `.pi` の設定値の変更、ワールドの `.pi` の link 切れ | 削除 | 型 3（設定値・ワールド一覧） | link は check-layout（`slum03/.pi` の行き先を変えると失敗）。header の値が環境変数の参照であることは `tests/scripts/test-agent-config.bash`（`.pi/mcp.json` の値を直書きにすると失敗） | |
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

`<s2>` は `slum02/tests/slum02/` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号、「原則」は Issue #51「原則として削除・統合するもの」の番号。「代わりの保証」には、変異を入れた一時コピーで失敗することを確かめた検査だけを書く。シェルのテストは無く、suite は Blender を起動しない（純 Python の層だけを検査する）。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `slum02/tests/__init__.py`、`<s2>__init__.py` | — | 維持 | テストをパッケージとして import する（`test_shacks.py` が `tests.slum02.test_stalls` の helper を読む） | — | |
| `<s2>test_ads.py::test_one_or_two_objects_per_ad` | spin 広告の分割漏れ | 削除 | 原則 4。名前の列の比較が件数も決める | `::test_names_sector_origin_and_determinism`（spin 広告を panel だけにすると失敗） | |
| `<s2>test_ads.py` のほか（13 関数） | spin の回転中心のずれ、ホロ素材の付け違い、非決定性、閉じていない mesh、非平面の面、遮蔽ボックスの不足、壁への埋まり、ホロ面と枠の隙間、投影機・支柱の誤り、看板・入口への広告の重なり、予算超過 | 維持 | 生成処理の実行。看板・入口との重なりは R18 で直した不具合 | — | |
| `<s2>test_build_pure.py::test_sector_order_fixed` | セクタの統合順の変更 | 理由付き固定値として維持 | `pipeline.merge_bundles` はこの順に統合し、衝突したキーを後のセクタ側で改名する。順序が変わると適用済みの state と安定キーが食い違う。理由を追記 | — | |
| `<s2>test_build_pure.py` のほか（2 関数） | 未登録セクタの受理、resource report の集計の誤り | 維持 | 実行 | — | |
| `<s2>test_geometry.py::test_tube_is_closed` | tube の穴あき | 削除 | 原則 4 | `::test_closed_primitives_have_positive_signed_volume[tube-catenary]`（tube の片側の蓋を消すと失敗） | |
| `<s2>test_geometry.py` のほか（11 関数、収集 21 件） | 閉じていない・内向きの primitive、開口の検証漏れ、カテナリー・回転・正規化・merge の誤り | 維持 | 実行。外向きの巻きは 5373608（R11）で直した不具合 | — | |
| `<s2>test_ground.py::test_puddles_and_manholes`（現 `test_every_puddle_is_placed`）のマンホールの件数 | マンホールの件数の変更 | 削除（水たまりの件数は残し、関数名から外した） | 型 3（`ground.MANHOLE_SITES` の件数の写し） | 不要 | |
| `<s2>test_ground.py` のほか（8 関数） | 地面の範囲・上面の向きの誤り、試行の上限で水たまりが 14 個に届かない、遠景の予算・範囲・窓明かりの欠落、非決定性、内向きの巻き、ピットの塞ぎ | 維持 | 生成処理の実行 | — | |
| `<s2>test_layout.py::test_deterministic` | 同じシードから違う layout ができる | 書き換え（キャッシュを通さない `_assemble()` と比較） | 原則 5。`build_layout()` はキャッシュした JSON を読み直すため、2 回呼ぶ比較は常に一致していた（`_backdrop` にグローバルな `random` を使わせても通った） | — | |
| `<s2>test_layout.py::test_counts` の外周 16 棟・内側 6 棟と体積 > 0 | 塔の件数の変更 | 削除 | 件数は型 3（角 4・辺 12 と `INNER_TABLE` の写し）。体積 > 0 は原則 5（高さ・footprint は生成時に正） | 不要 | |
| `<s2>test_layout.py::test_counts` のほか（屋台・クラブ・小屋・広告・Light の件数の範囲、影ありの Light ≤ 3） | 承認した範囲を外れる配置 | 理由付き固定値として維持 | 承認済みの設計仕様「街の構成」「予算の目安」と Plan の予算目安が定める範囲。理由を追記 | — | |
| `<s2>test_layout.py::test_radial_alleys_have_no_straight_exit` | 放射路地の本数の変更 | 削除 | 型 3。関数名と違い、路地の折れは検査していない | 不要 | |
| `<s2>test_layout.py::test_cable_attachments_exist` | ケーブルの件数の変更、存在しない取付先 | 削除 | 件数は型 3。取付先は原則 4（`validate_layout` の項目 7） | `::test_validate_clean`（取付先を `tower-99` にすると失敗） | |
| `<s2>test_layout.py::test_ads_mix` | 広告の種類・動き・看板の件数の変更 | 削除 | 型 3（生成コードの件数の写し） | 不要 | |
| `<s2>test_layout.py` のほか（8 関数） | 配置の検証の失敗、広場への侵入、東の壁の位置、範囲外、レイ判定の誤り、視線の抜け、layout.json の書き出し、遮蔽ボックスの出典の誤り、スポットの向き | 維持 | 生成処理と検証の実行。視線の検査は設計仕様の受入条件 | — | |
| `<s2>test_materials.py::test_palette_size_and_kinds`（現 `test_palette_kinds`）の件数の範囲（30〜48） | パレットの件数の変更 | 削除 | 型 3。設計仕様の素材数は目安（超えるときは根拠を記録する）で、値も仕様の 30〜40 と違う | 不要 | |
| `<s2>test_materials.py::test_palette_kinds` | postprocess が扱わない種類の素材の追加 | 理由付き固定値として維持 | `postprocess.convert_material` は holo 以外を頂点カラー素材に変換するので、新しい種類が黙って変換される。理由を追記 | — | |
| `<s2>test_materials.py::test_scroll_holo_materials_are_distinct_from_static` | スクロール用ホロ素材の欠落・静止用との共有 | 削除 | `is not` は同じ spec オブジェクトの共有しか見ず、素材名が別なら manifest では別の素材になる（原則 6）。実在の確認は原則 4 | 実在は `test_layout.py::test_validate_clean`（`holo_cyan_scroll` を消すと失敗） | |
| `<s2>test_materials.py` のほか（2 関数） | 存在しないノイズ・摩耗の参照、色の範囲外、発光しないネオン・ホロ、ノイズの範囲・サイズの誤り | 維持 | 参照先の実在と値の範囲 | — | |
| `<s2>test_nightlife.py::test_club_count_and_parts` | クラブの欠落、部品・素材・anchor の欠落 | 削除 | 原則 4。部品ごとの検査が同じ欠落で失敗する | `::test_names_sector_origin_and_determinism`（クラブを 1 軒減らすと失敗）、`::test_bead_curtain_strands`（ビーズを消す・`cloth_red` を別の素材にすると失敗）、`::test_posters`・`::test_shutter_half_open_and_slats_run_into_the_box`・`::test_red_lamps_and_bulbs`（それぞれの部品を消すと失敗）、`::test_neon_is_mounted_on_the_wall`（ネオン枠を消す・ネオン素材を別の素材にすると失敗）、`::test_sign_anchor_matches_layout_and_sits_on_board`・`::test_light_anchor_in_front_of_entrance`（anchor を消すと失敗） | |
| `<s2>test_nightlife.py` のほか（25 関数） | 高さ・予算の誤り、非決定性、閉じていない mesh、非平面の面、敷地のはみ出し、看板・照明の anchor のずれ、ビーズ・シャッター・ネオン・張り紙・ランプ・カーテン・室外機・雨樋の配置の誤り、広告との干渉、部品の貫通、露骨な表現の混入 | 維持 | 生成処理の実行。接触・干渉は Task 9 の教訓、広告との干渉は R18、表現の制限は Plan の Global Constraints | — | |
| `<s2>test_occlusion_coverage.py` | 遮蔽ボックスを満たさない生成物、未登録のセクタ | 維持 | 設計仕様の build 後の AABB 集計。全セクタを `sector_assemblies` で呼ぶ | — | |
| `<s2>test_overhead.py::test_cables_attach_to_real_mounts` | 端点が取付先の面に無い、meta の取付先の写し間違い | 削除 | 端点は原則 4（`validate_layout` の項目 7）。`meta["attach"]` を読む処理は無い（原則 6） | `test_layout.py::test_validate_clean`（端点を面から 1 m ずらすと失敗） | |
| `<s2>test_overhead.py::test_sector_registration` | overhead の登録漏れ | 削除 | 原則 4 | `test_occlusion_coverage.py::test_every_occluder_is_backed_by_geometry`（`@register("overhead")` を外すと失敗） | |
| `<s2>test_overhead.py` のほか（12 関数） | 端点・名前・種類の誤り、非決定性、閉じていない mesh、非平面の面、電線の本数・断面・たるみ、碍子の欠落、渡り廊下の手すり・屋根・遮蔽の不足、垂れ物の取付・高さ、ゴミの浮き・路上へのはみ出し、予算超過 | 維持 | 生成処理の実行 | — | |
| `<s2>test_pipeline.py::test_merge_renames_conflicts_and_rewrites_sources` | asset の改名・source の付け替えの誤り、セクタの表示名の変更 | 削除 | asset は原則 4。表示名は型 3 | `::test_merge_references_follow_renames`（source の付け替えを止める・衝突した asset を改名しないと失敗） | |
| `<s2>test_pipeline.py::test_build_unified_manifest_root_shape` のカメラ名 | カメラ名の変更 | 削除 | 型 3（`CAMERAS` の写し） | 不要 | |
| `<s2>test_pipeline.py::test_build_unified_manifest_root_shape` の存在テストの対象 | 存在テストが manifest に無い Slot を指す | 書き換え（決まった対象の `in` → 全対象が manifest の Slot キーに実在する） | 型 3（`_manifest_tests` の写し）。セクタ Slot のキーの書式を変えても通った | — | |
| `<s2>test_pipeline.py::test_build_unified_manifest_root_shape` の所有キー・所有ルート | 所有キー・所有ルートの変更 | 理由付き固定値として維持 | 既存の state と Resonite 上の Slum02_Slum の対応。理由を追記 | — | |
| `<s2>test_pipeline.py` の `from pathlib import Path` | — | 削除 | 使わない import（ruff F401）。変更前から未使用 | 不要 | |
| `<s2>test_pipeline.py` のほか（6 関数と root_shape の limits・後処理の Slot） | キーの衝突・再利用・刈り込み・参照の追従の誤り、bundle の欠落、limits の計算の誤り、後処理の未実行、非決定性 | 維持 | 合成 bundle での実行 | — | |
| `<s2>test_plaza.py::test_spray_layout_values` | スプレー文字の配置値の変更 | 削除 | 型 3（`spray_layout()` の定数の写し） | 不要 | |
| `<s2>test_plaza.py::test_floor_top_pits_and_cracks` の `FLOOR_TOP == 0.12` | 床の高さだけの変更 | 理由付き固定値として維持 | `postprocess.collider_slots` が柱の collider の基準高さ 0.185 を直接書いている。plaza・ground・postprocess・遮蔽の検査では、0.15 にしてもこの行だけが失敗した。理由を追記 | — | |
| `<s2>test_plaza.py` の `import math` | — | 削除 | 使わない import（ruff F401）。変更前から未使用 | 不要 | |
| `<s2>test_plaza.py` のほか（16 関数） | 構造物の欠落・はみ出し、東の壁の形・位置、スプレー文字の欠字（◎ を自前の形状で作る）、出入口の塞ぎ、内向きの巻き、予算・パレット外の素材・非決定性、ピットの塞ぎ、柱・クレーンレール・車・焚き火・機械台座の誤り、非平面の面 | 維持 | 生成処理の実行。◎ は Plan の Review Focus 4、車のリムは c70d392 で直した不具合 | — | |
| `<s2>test_plaza_press_wear.py` | 黄色い塗装のオレンジ化、摩耗の不足、塗装面の分割不足、スプレーの素材フィルタの誤り | 維持 | 生成処理の実行。9136ec3 で直した不具合 | — | |
| `<s2>test_plaza_scatter.py` | 瓦礫の沈み込み・浮き、立入禁止域への散布、散布数の過不足 | 維持 | 生成処理の実行。沈み込みは Plan の Review Focus 5 | — | |
| `<s2>test_postprocess.py` | 素材名の解析の誤り、PBS_Metallic の残り、参照切れ、駆動の対象・値の誤り、Light・collider・看板の件数と値の誤り、冪等性、未知の素材の受理 | 維持 | 後処理の実行。`::test_lights_colliders_and_shadow_budget` はほかの検査と一部重なるが、余分な Light を検出するのはこの関数だけ | — | |
| `<s2>test_scaffold.py::test_project_root_is_slum02` の `SEED == 260926` | シードの変更 | 理由付き固定値として維持 | コミット済みの bundle・report と適用済みのワールドはこのシードから生成した。理由を追記 | — | |
| `<s2>test_scaffold.py` のほか | プロジェクトルートの解決の誤り、フォント・OFL ライセンスの欠落 | 維持 | パスの解決と、OFL フォントの同梱条件 | — | |
| `<s2>test_shacks.py` | 継ぎはぎ・屋根の勾配・高さの誤り、非決定性、閉じていない mesh、非平面の面、柱の接地、パネルの浮き・沈み、重しの貫通・浮き、垂木・桁の接触、扉・窓・煙突・室外機・雨水ドラム・洗濯物の配置の誤り、隣の敷地への侵入、予算超過、bowtie の面、部品の貫通 | 維持 | 生成処理の実行。重しの接地は Task 9 の教訓、bowtie は 624059d で直した不具合 | — | |
| `<s2>test_stalls.py::test_market_counts` | 屋台・ジャンクの山の欠落 | 削除 | 原則 4 | `::test_names_ids_and_origin`（屋台を 1 軒・山を 1 つ減らすと失敗） | |
| `<s2>test_stalls.py::test_stalls_do_not_block_lane` | 柱・カウンターの路地への侵入 | 削除 | 原則 4。同じ部品を 0.2 m の余裕で見る、より弱い重複 | `::test_roof_eave_overhangs_lane_at_most_40cm_and_stall_stays_on_its_plot`（柱とカウンターを路地側へ 0.5 m ずらすと失敗） | |
| `<s2>test_stalls.py` のほか（15 関数） | 品物・カウンター・屋根の高さ・予算の誤り、名前・原点の誤り、閉じていない mesh、非平面の面、路地へのはみ出し、屋根の種類の偏り、たるみ、柱・棚・電球・看板の誤り、カウンターの支え、ジャンクの山の侵入、非決定性、汚れの位置、torus の巻き、重しの貫通・浮き | 維持 | 生成処理の実行。屋根の重しは 86717f5 で直した不具合 | — | |
| `<s2>test_towers.py::test_bay_and_floor_constants`（現 `test_floor_height_matches_layout`） | 階高が layout の `TOWER_FLOOR_H` と食い違う | 書き換え（`FLOOR_H == 3.2`・`BAY == 3.6` → `FLOOR_H == TOWER_FLOOR_H`） | 型 3（定数の写し）。ただし階高は layout の `core_height` の計算と対で、towers・layout・遮蔽・overhead の検査では towers 側だけを 3.0 にしてもこの行だけが失敗した。ベイ幅は写しなので外した | — | |
| `<s2>test_towers.py` の未使用の `oy0`・`oy1` | — | 削除 | 使わない変数（ruff F841）。変更前から未使用 | 不要 | |
| `<s2>test_towers.py` のほか（14 関数） | 塔の取りこぼし・重複、寸法・高さ・予算・素材数の誤り、必要な部品の欠落、窓の貫通、内向きの巻き・壁、付加物の埋まり、遮蔽の不足、非決定性、汚れ・崩落部の誤り | 維持 | 生成処理の実行。付加物の突き出しは 5d63b36 で直した不具合 | — | |
| `<s2>test_vcolor.py` | ノイズの非決定性・範囲外、足元の汚れ・錆・スプレーの誤り、色の範囲外 | 維持 | 実行 | — | |

前後: ファイル Python 21→21（テスト 19・`__init__.py` 2）、行 3,297→3,199、収集 215→202、所要は隔離コピーの変更前と交互に 3 回実行して 60.8〜65.2 秒→59.9〜62.7 秒（大半は `test_shacks.py::test_tyres_and_bricks_rest_on_the_roof_sheet` の約 27 秒）

## slum03

`<s3>` は `slum03/tests/slum03/` を表す。「型」は `AGENTS.md`「テストの採用基準」の作らない型の番号、「原則」は Issue #51「原則として削除・統合するもの」の番号。「仕様」は `docs/superpowers/specs/2026-09-27-slum03-cyberpunk-slum-design.md`、「密度仕様」は `docs/superpowers/specs/2026-09-28-slum03-density-upgrade-design.md`。「代わりの保証」には、変異を入れた一時コピーで失敗することを確かめた検査だけを書く。シェルのテストは無い。suite は `resoloop blender run` で Blender を起動する検査を含み、`artifacts/`・`content/` の凍結した run・manifest を読むだけで書き換えない。

| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |
| --- | --- | --- | --- | --- | --- |
| `<s3>conftest.py`、`<s3>helpers.py` | — | 維持 | 凍結した run と `density-baseline.json` を読む fixture、合成 report の helper。どちらも参照が残る | — | |
| `<s3>fixtures/density-gate-d2-evidence-redacted.json` | — | 維持（保護対象） | Gate D2 の証跡。`apply-log.md`・`live-verification.json` が参照する | — | #12 |
| `<s3>blender_*_probe.py`・`blender_corrupt_export.py`（pytest が呼ぶ 10 本） | — | 維持 | Blender 内で実行する probe。呼び出す検査が残る | — | |
| `<s3>blender_combined_probe.py`、`<s3>blender_task7_probe.py` | — | 維持 | pytest からは呼ばない。`task11-c` の `combined-preview.blend` と `task7-*` の `reopened.json`・PNG の証跡を検査・再生成するスクリプト | — | |
| `<s3>test_ads.py` | 平面の偽ホロ、主コピーの駆動、取付のない投影機、可動範囲の経路侵入、Blender での親子・変換・法線の誤り | 維持 | 生成処理と Blender の実行 | — | |
| `<s3>test_architecture_detail.py::test_legacy_unselected_builds_unchanged_and_representative_selected` | 選んでいない既存の建物のメッシュの変化 | 理由付き固定値として維持 | 密度仕様 7 章 Gate B「その他の既存内容は保持」。理由を追記 | — | |
| `<s3>test_architecture_detail.py` のほか（9 関数） | 変種の偽装、支えのない付属物、塗っただけの開口、向き・シードのずれ、扉の閉塞、法線の反転 | 維持 | 生成処理の実行 | — | |
| `<s3>test_asset_verification.py` | build エラー・セクタの欠落・材質・UV・侵入の見逃し、比較の独立性、資源の帰属、build の順序、保存 layout の受け渡し、v2 の証拠の偽装 | 維持（未使用の import を削除） | 検証処理の実行。`BUILD_ORDER` は駆動する AR を背景の後に作る順序 | — | |
| `<s3>test_backdrop.py::test_multiple_arcologies_are_north_of_river` | アーコロジーの数・位置・高さ・シルエットの変更 | 理由付き固定値として維持 | 仕様 4.5・9.1「景観」の受入条件。理由を追記 | — | |
| `<s3>test_backdrop.py` のほか（4 関数） | 箱だけの巨大建築、低層の背景街区の欠落、見えない面の窓、門の冠部の支えの欠落 | 維持 | 生成処理の実行。冠部は 67598eb で直した不具合 | — | |
| `<s3>test_blender_io.py::test_tracked_ground_probe_matches_current_world_coordinate_build` | （コミット済みの probe 出力の編集） | 削除 | 原則 5。`artifacts/slum03/probes/ground-report.json` を固定値と比べるだけで実装を通らず、現行の build が変わっても失敗しない | 不要（現行の地面の範囲は `::test_ground_build_reports_resonite_bounds_and_stable_export_name` と `test_ground.py` が生成して検査する） | |
| `<s3>test_blender_io.py` のほか（16 関数） | 軸変換、未登録セクタの受理、UV・hook・親子・proxy 名の誤り、報告の上書き | 維持 | Blender の実行 | — | |
| `<s3>test_build.py` | 編集用ソースと出力の混同、UV・材質の欠落、ラベルの向き、AR 文字の遮蔽、保存 layout の不使用、未タグの部品 | 維持 | Blender の実行。`::test_checked_in_layout_is_accepted_by_current_layout_validator` はコミット済みの `layout.json` と生成器の比較 | — | |
| `<s3>test_candidate_scope.py::test_representative_candidate_limits_are_sized_from_its_own_content` | 候補の limits が基準の値のまま残る | 削除 | 原則 4。`compose_candidate` は段階によらず同じ行で limits を付け直す | `test_density_integration.py::test_full_candidate_limits_are_sized_from_the_written_content`（limits を付け直さない変異で失敗。削除した検査も同じ変異で失敗） | |
| `<s3>test_candidate_scope.py` のほか（22 関数） | 保護対象の資源・Slot・共有 provider の変更、範囲外のノード、別 run の資源、参照される stub の削除 | 維持 | 適用範囲を守る安全条件の実行 | — | |
| `<s3>test_colliders.py::test_postprocess_does_not_duplicate_colliders` | 再実行での collider の重複 | 削除 | 原則 4。同じ bundle で postprocess の冪等性を 3 か所で検査していた | `test_native_materials.py::test_exported_palette_providers_become_vertex_color_or_holo_without_losing_renderer_refs`・`test_drivers.py::test_scan_clones_only_driven_material_and_pans_texture_not_slot` の最終行（collider を重複して足す変異で両方失敗） | |
| `<s3>test_colliders.py::test_yarol_collider_rotates_with_visible_facade` | Yarol の collider の回転漏れ | 削除 | 原則 4（建物の collider は同じ 1 行で向きを渡す）、型 3（Yarol の位置・寸法の写し） | `::test_noncardinal_building_yaw_is_kept_on_collider_slot`（向きを渡さない変異で失敗）。Yarol の collider の存在は `::test_nightlife_facades_have_simple_owned_building_colliders` | |
| `<s3>test_colliders.py::test_v2_open_stall_only_collides_with_real_low_parts_and_preserves_legacy_boxes` の `len(original) == 34` | 旧 collider の件数の変更 | 削除 | 型 3。旧 collider の保持は同じ関数の `boxes[:len(original)] == original` が見る | 不要 | |
| `<s3>test_colliders.py` のほか（10 関数） | 活動床への collider の侵入、橋・検問の通路の塞ぎ、評価後の形状からのはみ出し、v2 の所有キーの変更・消失 | 維持（未使用の import を削除） | collider 生成の実行 | — | |
| `<s3>test_delivery.py::test_baseline_fixture_retains_original_mesh_count` | 凍結した基準の manifest の変更 | 削除 | 原則 4。同じファイルの SHA を `test_density_model.py` が固定している | `test_density_model.py::test_saved_baseline_has_original_fixed_hash_and_slot_keys`（メッシュ資源を 1 件消すと失敗） | #12 |
| `<s3>test_delivery.py::test_canonical_manifest_is_portable_and_contains_live_qa` | 採用した宣言の所有キー・設置高さの変更、資源の参照切れ、QA の欠落 | 理由付き固定値として維持 | 採用 run を適用した宣言。設置高さ Y=4.5 は密度仕様 2 章。理由を追記 | — | #12 |
| `<s3>test_delivery.py::test_superseded_task12_delivery_evidence_is_kept_as_history`、`::test_review_candidate_counts_and_hash_come_from_its_own_evidence` | 凍結した証跡と記録の食い違い、pending の格上げ | 理由付き固定値として維持 | 凍結した履歴。後者に理由を追記 | — | #12 |
| `<s3>test_delivery.py` のほか（9 関数） | 証拠の無い pass、警告の見逃し、カメラの root 高さ、Panner の安定キー | 維持（未使用の import を削除） | 判定処理と統合の実行 | — | |
| `<s3>test_density_acceptance.py` | 別の manifest・段階への受入の流用、暗い画像・未確認の pass、保存・再読込の未確認 | 維持 | 受入判定の実行 | — | #12 |
| `<s3>test_density_blockout.py` | Gate A の視点の高さ・地区の変更 | 理由付き固定値として維持 | 密度仕様 7 章 Gate A の確認条件。理由を追記 | — | |
| `<s3>test_density_candidate.py` | blockout・別段階の受理と出力の作成、別の layout の要約、旧キー・平面の誤判定、来歴の欠落、同じバイトの別資源、参照される stub の削除 | 維持 | CLI と処理の実行 | — | |
| `<s3>test_density_dispatch.py::test_build_density_cli_rejects_blockout_stage` | CLI が blockout 段階を受け付ける | 削除 | 原則 4。同じ CLI を実行し、出力と state が残らないことまで見る検査がある | `test_density_candidate.py::test_blockout_stage_rejected_without_output`（argparse と `prepare` の両方の拒否を外す変異で失敗）。守らなくなる点: argparse の拒否だけを外す変更（`prepare` が同じ段階を拒否するので出力は作られない） | |
| `<s3>test_density_dispatch.py` のほか（4 関数） | 種類の混在したセクタの取りこぼし・重複、旧メッシュの変化、未対応の種類の受理 | 維持 | 生成処理の実行 | — | |
| `<s3>test_density_integration.py` | 全域候補の範囲・再生成・件数・hash の偽装、代表 report の流用、順序依存、比較の見逃し、limits の超過 | 維持 | 処理の実行 | — | |
| `<s3>test_density_layout.py::test_selected_key_classifier_rejects_the_old_unresolvable_key` | （テスト内の helper の分類の誤り） | 削除 | 原則 5（テスト内の helper だけを検査）、原則 4（旧キーが選択に無いことは隣の関数が見る） | `::test_full_selected_keys_resolve_to_exactly_one_class`（`district-ground` を選択キーに戻すと失敗） | |
| `<s3>test_density_layout.py::test_full_selected_keys_resolve_to_exactly_one_class` の JSON の往復 | （なし） | 削除 | 原則 5。文字列の JSON の往復は常に一致する | 不要 | |
| `<s3>test_density_layout.py` のほか（12 関数） | 97 単位・4 地区の不足、既存の姿勢の変化、偏り・重なり・背景での水増し、通路・Yarol 入口の塞ぎ、取付による免除の悪用、変種の欠落、選択キーの分類 | 維持（未使用の import・変数を削除） | 生成処理と密度検査の実行。物量は密度仕様 4.1 の受入条件 | — | |
| `<s3>test_density_live_evidence.py::test_unknown_reapply_counts_are_not_treated_as_zero` | （テスト内の helper の誤り） | 削除 | 原則 5。テスト内の `reapply_zero` だけを検査 | 不要 | |
| `<s3>test_density_live_evidence.py::test_committed_reapply_pass_requires_known_zero_counts` | 件数が不明なままの再適用の pass | 削除 | 原則 4 | `::test_reapply_writes_and_imports_are_zero_from_recorded_counts`（記録した件数を null にすると失敗） | #12 |
| `<s3>test_density_live_evidence.py::test_superseded_records_remain_only_as_history` の `'Gate D2'`・`'Task 10'` の照合 | 記録の文言の変更 | 削除（現行節が採用 manifest の SHA を記録することの検査は維持） | 型 1 | 不要 | #12 |
| `<s3>test_density_live_evidence.py` のほか（7 関数） | 採用候補と記録・基準の食い違い、件数の不一致、Grabbable の失敗の隠蔽、人の確認の格上げ、生のライブ ID の混入 | 理由付き固定値として維持 | #12 の証跡を宣言と結び付け、推測で pass にしない。生の ID は秘密情報の保護 | — | #12 |
| `<s3>test_density_metrics.py` | 和集合の二重計上、間口の抜け、偽の開口、空の形状、接触の無い取付、重なり、layout の digest の不一致、縁石の誤判定 | 維持（未使用の import・変数を削除） | 密度検査の実行 | — | |
| `<s3>test_density_model.py::test_legacy_layout_not_full_density` の `len(legacy_layout.__dataclass_fields__) == 9` | Layout の項目数の変更 | 削除 | 型 3（件数固定）。既定値付きの項目を末尾に足すだけで失敗していた | 旧形式の互換は `::test_old_eight_positional_arguments_still_construct_layout`（density の前に必須の項目を挿む変異で失敗） | |
| `<s3>test_density_model.py::test_saved_baseline_has_original_fixed_hash_and_slot_keys` | 凍結した基準 manifest・代表の Slot キーの変更 | 理由付き固定値として維持 | `apply-log.md`・`live-verification.json` が記録する基準。理由を追記 | — | #12 |
| `<s3>test_density_model.py::test_legacy_manifest_is_saved_baseline_even_when_canonical_changes` | （conftest の fixture の読み先） | 削除 | 原則 5。テストの fixture だけを検査 | 不要 | |
| `<s3>test_density_model.py` のほか（6 関数） | 旧 layout の密度扱い、型付きの往復、不正な密度の受理、シードの非決定性 | 維持 | 実行。`REPRESENTATIVE_KEYS` は Gate B で選んだ 3 単位で、`density_candidate.prepare` も同じ集合を要求する | — | |
| `<s3>test_density_views.py::test_shared_preview_has_usable_comparison_quality_without_changing_legacy_quality` | 描画設定の変更 | 削除 | 型 3（`preview_quality` の設定値の写し） | 不要 | |
| `<s3>test_density_views.py::test_comparison_uses_identical_root_local_pose_and_fov` の `candidate == baseline` | （なし） | 削除 | 原則 5。同じ入力で 2 回呼んだ結果を比べる恒真の検査 | 不要 | |
| `<s3>test_density_views.py` のカメラの検査（`::test_shared_cameras_have_local_height_and_market_inward_direction`・`::test_near_cameras_target_authored_surfaces_and_market_shelves_from_common_pose`・`::test_extra_synchronized_views_face_washing_and_both_stock_orientations`） | 比較カメラの名前・向き・注視点が直す前に戻る | 理由付き固定値として維持 | 4d7fa5a のレビュー修正（旧カメラが空の区画を写していた）。直した姿勢は `representative-review-fix5` の比較画像と受入記録に使われている。理由を追記 | — | |
| `<s3>test_density_views.py` のほか（4 関数） | QA の追加で既存のカメラ・テスト・内容が変わる、root ローカルの姿勢の誤り、review 候補の hash・limits の誤り | 維持 | 実行 | — | |
| `<s3>test_detail_evidence.py` | 自己申告の detail、未使用の頂点による範囲の拡大、不正な group・取付・循環・未知の profile | 維持 | 実行 | — | |
| `<s3>test_drivers.py` | 回転の再適用、走査の対象の誤り、駆動 Slot の欠落・重複、無関係なキーの変更による駆動の消失 | 維持 | postprocess の実行 | — | |
| `<s3>test_evaluated_detail.py` の import の wrapper（`importlib`） | （モジュールの未実装） | 削除（直接 import に書き換え） | 原則 6。TDD の RED 用で、モジュールがあるので役割を失った | 不要（関数名を変えると import で収集エラーになることを確認） | |
| `<s3>test_evaluated_detail.py` のほか（11 関数） | 実際の面からの計測、欠けた・潰れた・偽の形状、layout の digest の不一致、輪郭外の偽の部品、取付の接触 | 維持 | 実行 | — | |
| `<s3>test_forest.py` | 森の幹・枝・樹冠の欠落、平板な背景、内向きの樹冠 | 維持 | 生成処理の実行 | — | |
| `<s3>test_geometry.py` | 外向きでない箱・壁、材質と submesh の順序、カテナリー・回転の誤り | 維持 | 実行 | — | |
| `<s3>test_graffiti.py::test_graffiti_is_exactly_the_north_wall_south_face_copy` | 文字列・北壁の位置・面の向きの変更、フォントの欠落 | 理由付き固定値として維持 | 仕様 D-05・4.3・9.1「工場壁」の受入条件。理由を追記 | — | |
| `<s3>test_graffiti.py::test_missing_font_glyph_is_explicit_error` | 欠けた字形の黙認 | 維持 | 実行 | — | |
| `<s3>test_ground.py::test_scenic_pads_are_dark_distinct_from_default_floor` | 素材名の変更 | 削除 | 型 3。`ground.py` の素材名の写しで、暗さも既定床との違いも検査していない | 不要 | |
| `<s3>test_ground.py::test_full_ground_stains_are_coplanar_surface_cells_only` のハッシュ | 旧版・代表の地面のメッシュの変化 | 理由付き固定値として維持 | 密度仕様 7 章 Gate B。理由を追記 | — | |
| `<s3>test_ground.py` のほか（11 関数） | 地面の範囲・下面の誤り、重なる歩行面、景観の下地の欠落・川の覆い、森の奥の地平線、汚れの浮き・はみ出し、路面の詳細の欠落・段差・非決定性・予算超過、店先へのごみ、90 度でない向きの受理 | 維持 | 生成処理の実行。路面の詳細は密度仕様の改訂 1 | — | |
| `<s3>test_layout.py::test_layout_dimensions_and_repeatability`、`::test_plan_includes_canonical_sector_anchors_and_distinct_domains`、`::test_walkable_road_runs_beyond_district_and_river_is_outside_district` | 承認した寸法・用途・視点・道路と川の範囲の変更、旧東壁の再導入 | 理由付き固定値として維持 | 仕様 D-03・D-04・D-07・4 章・9.1 の受入条件。理由を追記 | — | |
| `<s3>test_layout.py` のほか（11 関数） | 別シードでの公共通路の変化、往復・プロセス間の非決定性、不正な寸法・ベクトル長・取付の受理、必須の景観・視点・境界の欠落 | 維持（未使用の import を削除） | 実行 | — | |
| `<s3>test_lighting.py` | 所有範囲外の光源、影付きの追加光源、既存 6 灯の変化 | 維持 | 実行 | — | |
| `<s3>test_market_detail.py` | 商品の過大・数の水増し、前面の閉塞、内向きの天幕、姿勢・シードのずれ、棚と支柱・筋交いの非接触、アンテナと筋交いの干渉 | 維持 | 生成処理の実行 | — | |
| `<s3>test_materials.py::test_palette_covers_concrete_metal_and_emission` | パレットの値・Blender の素材名の接頭辞の変更 | 削除 | 型 3（`materials.py` の定数の写し） | 接頭辞は `test_plaza.py::test_generated_plaza_reopens_with_editable_scatter_and_static_uv_color_exports`（`BLENDER_PREFIX` を変えると失敗）。守らなくなる点: `neon_cyan` の発光強度と 2 素材の family の値 | |
| `<s3>test_materials.py::test_vertex_wear_is_deterministic_and_grimy_at_ground` | 非決定性、足元の汚れの不足 | 維持（未使用の import を削除） | 実行 | — | |
| `<s3>test_merchandise.py` | 箱だけの商品、数の水増し、支えの無い・見えない商品、配管の継ぎ目のねじれ | 維持 | 生成処理の実行 | — | |
| `<s3>test_native_materials.py` | 素材の変換漏れ・参照切れ、未知の素材の受理 | 維持 | postprocess の実行 | — | |
| `<s3>test_nightlife.py` | 看板だけの店先、通り抜けられる隙間、支えの無い看板・天幕、変種の偽装、敷地のはみ出し、collider キーの変更 | 維持 | 生成処理の実行 | — | |
| `<s3>test_overhead.py` | 浮いたケーブルの端、活動空間への侵入、分割による本数の水増し、たるみ・支えの欠落 | 維持 | 生成処理の実行 | — | |
| `<s3>test_ownership.py` | 所有範囲外の参照・親、不正な参照・資源の出所、symlink の脱出、改名した所有ルート | 維持（未使用の import を削除） | 安全条件の実行 | — | |
| `<s3>test_pipeline.py` | 資源・素材の改名と参照の付け替え・共有・再利用の誤り、書き出しの相対パス、セクタの欠落、合成 report の受理、別版の report の混入 | 維持（未使用の import を削除） | 統合の実行 | — | |
| `<s3>test_plaza.py::test_legacy_and_staged_plaza_geometry_is_unchanged` | 旧版・代表・ブロックアウトの広場のメッシュの変化 | 理由付き固定値として維持 | 密度仕様 7 章 Gate B。理由を追記 | — | |
| `<s3>test_plaza.py` のほか（7 関数） | 旧東壁の再導入、スプレー文字・瓦礫・床の詳細の誤り、中央床への大きな瓦礫・collider、段差 | 維持 | 生成処理と Blender の実行。旧東壁なしは仕様 9.1 | — | |
| `<s3>test_preview.py` | 証跡の描画スクリプトの非推奨 API | 維持 | 395bc66 で直した不具合（Blender 5 の `world.use_nodes`）。現行の `build.py` で作った広場を描画する | — | |
| `<s3>test_probe_manifest.py::test_probe_manifest_is_owned_and_keeps_assets_relative` | プローブの所有キー・`ResoLoop_Test_*` の名前の誤り、資源の参照切れ | 理由付き固定値として維持 | プロジェクトの `AGENTS.md`「Resonite safety」。理由を追記 | — | |
| `<s3>test_probe_manifest.py` のほか（3 関数） | 外へ出る資源・親の受理 | 維持 | 安全条件の実行 | — | |
| `<s3>test_road_river.py::test_bridge_matches_road_and_bank_span` | 橋の範囲の変更 | 理由付き固定値として維持 | 仕様 4.1 の表。理由を追記 | — | |
| `<s3>test_road_river.py` のほか（10 関数） | 両岸に届かない橋、検問の開口の塞ぎ、欄干・護岸の欠落、支えの非接触、重複した路面、同一平面の面、Blender の再読込 | 維持 | 生成処理と Blender の実行 | — | |
| `<s3>test_root_anchor.py` | 既存の床の編集、不正な入力の受理、所有ルート外の変更 | 維持 | 実行 | — | |
| `<s3>test_ruins.py` | 塗っただけの窓、無傷のスラブ、建物の結合、経路への侵入、鉄筋のはみ出し | 維持 | 生成処理の実行 | — | |
| `<s3>test_scaffold.py::test_project_scaffold_is_standalone` の雛形ファイルの存在 | ファイルの欠落 | 削除（slum02 の混入とシードの検査は残す） | 原則 4。`pyproject.toml`・`uv.lock`・`AGENTS.md`・`.resoloop.json` は `scripts/check-layout.sh` の検査 6、`content/main.json` は隣の関数が読む。`modeling` の `__init__.py` は無くても import できる | 不要（`modeling/__init__.py` を消しても書き換えた関数は通り、変更前の関数は失敗することを確認） | |
| `<s3>test_scaffold.py::test_project_scaffold_is_standalone`（残り） | slum02 のコード・state の混入、既定シードの変更 | 理由付き固定値として維持 | 仕様 4.1・7.2・9.1「所有」。理由を追記 | — | |
| `<s3>test_scaffold.py::test_project_guide_names_ownership_and_state` | `AGENTS.md` の文言の変更 | 削除 | 型 1 | 不要（所有キー・所有ルート・state のパスの設定は `::test_scaffold_manifest_and_flux_use_the_approved_world_identity` が見る） | |
| `<s3>test_scaffold.py::test_scaffold_manifest_and_flux_use_the_approved_world_identity` | 所有キー・所有ルート・state のパスの変更、Grabbable の付与 | 理由付き固定値として維持 | 適用済みの state との対応と、街全体を Grabbable にしない判断。理由を追記 | — | #12 |
| `<s3>test_scatter.py::test_legacy_scatter_plan_is_unchanged_for_existing_candidates`、`::test_full_perimeter_scatter_is_unchanged_by_the_floor_debris` | 旧版・全域の外周の瓦礫の移動 | 理由付き固定値として維持 | 既存の瓦礫を動かさない。理由は既存のコメント | — | |
| `<s3>test_scatter.py` のほか（11 関数） | 鉄筋のはみ出し、入口・中央床への侵入、偏りの無い散布、床の瓦礫の高さ・種類・粗密、配置できない床での無限ループ | 維持 | 生成処理の実行（`floor_coverage` は `test_plaza.py` も使う） | — | |
| `<s3>test_scene_preview.py::test_combined_preview_includes_near_north_and_bright_detail_views` | 補助の視点の欠落 | 削除 | 型 3（`preview.VIEWS` の写し）、原則 4 | `::test_combined_preview_reads_persisted_custom_labels_and_builds_supplemental_views`（`VIEWS` から `west-detail` を消すと失敗） | |
| `<s3>test_scene_preview.py` のほか（3 関数） | 欠けたシーンの描画、単独プレビューでの可視性の主張、保存 layout の文字の位置 | 維持 | Blender の実行 | — | |
| `<s3>test_shacks.py` | 支えの無い屋根、平らな波板、住戸の結合、入口・通路の塞ぎ | 維持 | 生成処理と Blender の実行 | — | |
| `<s3>test_sightlines.py` | 北の巨大建築・東の森・西南の街の視線の遮り | 維持（未使用の import を削除） | 視線判定の実行。仕様 4.5・9.1 | — | |
| `<s3>test_signs.py::test_labels_have_fixed_parent_local_pose_and_readable_copy` | 看板の位置・文言の変更 | 書き換え（Yarol の位置と `NIGHT SHIFT` の照合を外し、親・文字・回転の検査を残す） | 型 3（`layout_district.py`・`layout_ads.py` の値の写し）。offset から位置への変換は `::test_japanese_main_copy_stays_on_fixed_parent_with_exact_unicode` が見る | — | |
| `<s3>test_signs.py` のほか（2 関数） | 親の解決の誤り、日本語の主コピーの位置・文字の誤り | 維持（未使用の import を削除） | 実行 | — | |
| `<s3>test_spatial.py` | 回転後の範囲、評価後の侵入、床の免除の誤り、不正な範囲の受理、床の瓦礫の高さ | 維持（未使用の import を削除） | 実行 | — | |
| `<s3>test_stalls.py::test_representative_market_dispatch_changes_only_selected_west` | 選んでいない market-east のメッシュの変化 | 理由付き固定値として維持 | 密度仕様 7 章 Gate B。理由を追記 | — | |
| `<s3>test_stalls.py` のほか（6 関数） | 通路の幅、棚・支えの欠落、UV、証跡の描画スクリプトの非推奨 API、種類の振り分け | 維持 | 生成処理と Blender の実行。`::test_task5_preview_renders_without_deprecation_warning` は 60c4cd2 で直した不具合 | — | |
| `<s3>test_utilities.py` | 用途の取りこぼし・重複、設備・生活痕の欠落、所有物の外・保護空域への設備、Yarol の変化、選択キー・姿勢の変化 | 維持（未使用の import を削除） | 生成処理の実行。物量は密度仕様 4.1 | — | |
| `<s3>test_uv.py` | UV の面積、退化した面の受理 | 維持 | 実行 | — | |
| `<s3>test_yarol.py` | 向き・敷地の誤り、入れる内装、支えの無いネオン、外装の隙間 | 維持 | 生成処理の実行。敷地と向きは仕様 4.4 | — | |

前後: ファイル Python 67→67（テスト 53・probe 12・`conftest.py`・`helpers.py`。ほかに JSON の fixture 1）、行 テスト 8,245→8,107・Python 全体 9,004→8,866、収集 538→520、所要は着手前の実行と、隔離コピーで変更前・変更後を交互に 2 回ずつ実行して 127.3〜131.5 秒→127.1〜128.4 秒（削除したのは軽い検査だけで、差は誤差の範囲。大半は Blender を起動する検査）

## 行動比較

AGENTS.md に「テストの採用基準」を入れる前と後で、エージェントの計画とレビューが変わるかを比べた。

- 条件: 変更前は `/workspaces/reso-world`（基準 HEAD a94f04e の detached checkout）、変更後は `.worktrees/issue-51-test-cleanup` を cwd にした。コマンドは `claude -p "<prompt>" --model sonnet --tools Read,Grep,Glob`。各場面・各条件 1 回で、prompt は両条件で同じ。終了コードはすべて 0
- prompt と出力は scratchpad（`task8/`）にあり、コミットしない

| 場面 | 変更前 | 変更後 |
| --- | --- | --- |
| 1 README の見出し | テスト不要と書くが、Task 単位の記載は無い。新規テストなし | 各 Task に「テストの要否: 不要」と理由、代わりの検証を書く。新規テストなし |
| 2 skill の description | 要否の明示なし。既存テストを実行する。新規テストなし | 各 Task に「不要」と理由を書く。新規テストなし |
| 3 pi-superagents のモデル | 要否の明示なし。新規テストなしだが、既存テストの fake pi のモデル名を更新する手順を含む | 「作らない型 3」を挙げ、既存テストは実行して確認するだけ。新規テストなし |
| 4 安全条件の不具合 | symlink の回帰ケースを先に追加する Task を含む | 「テストの要否: 必要」として、同様の回帰ケースを追加する Task を含む |
| 5 テスト追加差分のレビュー | 不要なテストとして指摘（根拠は基本方針と memory。型の番号なし） | 不要なテストとして指摘（作らない型 1・3・4 を番号で挙げる） |

所見:

- 主な差は、Task ごとにテストの要否と理由を書くようになったことと、作らない型を番号で引くこと
- 場面 4 の回帰テストは前後とも省略しなかった
- 場面 5 は前後とも指摘した
- 変更前でも作らない型のテストは出なかった

注意:

- 各条件 1 回なので、結果は傾向として読む
- memory（MEMORY.md）は両条件で読まれており、既存の方針が前後どちらの結果にも効いている（場面 5 は前後とも memory の「可変な値を固定値でテストしない」を根拠に挙げる）
- 変更後の cwd は本ブランチ（`chore/issue-51-test-cleanup`）の worktree で、採用基準のほかに本 Issue の Spec・分類表も読める。変更後の出力はブランチ名や Issue #51 のテスト整理に触れており（`s2-after.md`・`s3-after.md`・`s5-after.md`）、前後の差が採用基準だけによるとは言い切れない（交絡）
- 場面 3 は、変更前の出力にあった既存テストの fake pi のモデル名を更新する手順が、変更後の出力には無い
- 場面 5 の 1 回目は、変更後だけ scratchpad の差分ファイルを読めずレビューできなかった。この差は cwd の違いによる読み取り権限の差で、採用基準による差ではない。両条件に `--add-dir` を付けて再実行し、表には再実行の結果を使った
- `--tools` は可変長引数なので、prompt を先に置かないと prompt が渡らない
