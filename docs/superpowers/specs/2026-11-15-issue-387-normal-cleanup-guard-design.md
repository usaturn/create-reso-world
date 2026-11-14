# Issue #387: 通常のレビュー完了の cleanup でも利用者作業を検査して保持する

## 管理・実行許可

- 状態: `draft`（issue-to-pr の実行委任で作成。内容の承認は得ていない）
- 対象: https://github.com/usaturn/create-reso-world/issues/387
- 利用者指示（2026-11-15）: `/issue-to-pr #387 --merge --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`
- issue-to-pr の委任として、推奨案で設計し、検証・commit・push・PR 作成、PR 修正ループ（`--merge`）による修正不要の確認後のマージまで進む。実行許可であり、内容の承認（`approved`）ではない。
- repository: `usaturn/create-reso-world`。base: origin / `refs/heads/main` / `c8a2f58ffb65eced3e18993d97c439bb2d23197b`。
- Spec・Plan はコードと同じ worktree・PR に含める。確認用コピーは作らない。

## 目的と原因

PR レビューの通常の完了処理（`review_run.complete`）は、保存の成功後に `pr_review_workspace.cleanup` を strict 指定なしで呼ぶ。非 strict の `cleanup` は、保存済みのレビュー・候補とセッション worktree の登録を確かめるだけで `git worktree remove --force` を実行する。strict な退役（`reap-check` / `cleanup --strict-reap`）が `_require_clean_worktree` で行う利用者作業の検査（HEAD が固定 commit か、detached か、変更・未追跡・cache 以外の ignored ファイル、skip-worktree / assume-unchanged、submodule の HEAD と gitlink の一致・変更）を通らないため、strict なら `retained` にする submodule の未 push commit を、通常の完了は終了コード 0 で消す（Issue の再現: submodule のローカル commit オブジェクトが全保存領域から失われ、保存レビューだけが残る）。

## 範囲・除外

変更する。

- `.agents/skills/pr-review/scripts/pr_review_workspace.py` の非 strict `cleanup`: 保存ロックの中、ref・worktree を消す前に、strict と同じ `_require_clean_worktree(worktree, target, state)` を実行する。検査に失敗したら何も消さず、`RetirementRefused`（`retirement="saved"`）を送出する。
- `.agents/skills/pr-review/references/noninteractive.md`: complete の `cleanup` と CLI の通常 `cleanup` が利用者作業を見つけると削除を拒否し、セッションを保持することを、結果の表の行に足す。
- テスト（S）: 下の「テスト」のとおり。

変更しない。

- strict 退役（`validate_reapable_session`・`strict_cleanup`・`reap-check`）の判定内容。別ブランチ／stash／deinit 保全の不足は別原因で対象外（Issue 本文の除外）。
- 非 strict `cleanup` の既存の保存条件（`require_saved_review`・`require_session_worktree`・`require_saved_findings`、version 7/8 の pinned ref の compare-and-delete、保存ロック）。順序を変えず、検査を足すだけにする。
- `review_run.complete` の結果の形と終了コード。既存の仕様（noninteractive.md「保存済みで cleanup だけ失敗したとき」）どおり、`status: failed`・`cleanup: failed`・`reason`・`review_file`・`findings_file`・`active_findings`・`state_file`・`retained_paths` を返す。
- pr-review-fix-loop の reviewer 判定。
- セッションディレクトリの既知エントリ・backup の中身の検査（`_require_known_entries`・`_require_known_backup`）は通常の cleanup に足さない。これらは「利用者が worktree に置いた作業」ではなく、退役の可否の厳格化であり、通常完了の後片付けを不要に止める。

## 決定記録

### D1: 通常 cleanup に足す検査の範囲

- 選択した案: strict の worktree 検査 `_require_clean_worktree` をそのまま呼ぶ。
- 検討した別案: (a) HEAD と submodule の HEAD 一致だけを新しく検査する。(b) `review_run.complete` から `cleanup --strict-reap` を呼ぶ。
- 選択理由: 受け入れ条件は「strict 側が保持する利用者作業を保存成功だけで削除しない」であり、その定義は既に `_require_clean_worktree` にある。(a) は未追跡ファイル・変更など strict が守る作業を通常完了だけ消し続け、守りの定義を 2 つに分ける。(b) は create journal・既知エントリ・backup の検査まで課し、通常完了が必要とする後片付け（Issue の「すべての削除入口を無条件に同じ挙動へ変えない」）を超える。
- 委任指示または停止条件: issue-to-pr の推奨案委任。トレードオフとして、レビュー担当が worktree に cache 以外の未追跡ファイルを作った場合も cleanup は拒否され、`status: failed` になる（データを消さない側に倒す）。保持したセッションは、定期掃除・repo-cleanup-after-merge の strict 退役でも同じ検査で保持と報告され、利用者作業が残る限り自動では退役しない。回収は、利用者が作業を退避・削除してから strict 退役で行う。

### D2: 検査の位置

- 選択した案: 保存ロックの中で、`require_session_worktree` の後、pinned ref の削除と `git worktree remove --force` の前に 1 回行う。
- 検討した別案: ロックの前後で 2 回行う（strict と同じ）。
- 選択理由: 削除の直前にロックの中で判定すれば、判定から削除までの間に別のレビュー保存が割り込まない。ロック前の 1 回目は早期拒否の最適化にとどまり、通常完了では不要。ref を先に消してから拒否すると、保持したセッションの pinned ref だけ失われるので、ref の削除より前に置く。
- 委任指示または停止条件: 推奨案委任。

### D3: 拒否の表現

- 選択した案: `RetirementRefused(message, retirement="saved")` を送出する。CLI の通常 `cleanup` は既存の `main` の分岐で終了コード 1 と `status: "retained"`・`reason`・`retained_paths` の JSON を返す。`review_run.complete` は既存の `except (OSError, ValueError, RuntimeError)` で受け、`cleanup: failed`・`reason`・`retained_paths` を返す。
- 検討した別案: (a) `WorkspaceError` のまま（CLI は終了コード 2 の `error:`）。(b) complete に新しい `cleanup: "retained"` の値を足す。
- 選択理由: (a) は「状態を読めない・引数の誤り」と同じ終了コードになり、保持の判断と区別できない。(b) は結果の値域を広げ、loop・SKILL の判定を変える必要が出る。既存の `cleanup: failed` と `reason`・`retained_paths` で呼出元は保持を判別できる（Issue の受け入れ条件「保持理由・残したパスを呼出元が判別できること」）。
- 委任指示または停止条件: 推奨案委任。

### 割り当て（helper の検査結果を写す）

- Plan の Task の担当: `--implement pi_alibaba_qwen4-max_max`（利用者の指定）。`fallback` は設定のまま `[]`。`self: false`。
- Spec レビュー: `--spec-review pi_alibaba_qwen4-max_max`（利用者の指定）。`fallback` は `[]`。設計レビューは指定なし。
- PR 修正ループ（`check-options`）: `max_cycles` 3（既定の適用）。`--assign implement=pi_alibaba_qwen4-max_max`、`--assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`（利用者の指定）。`self-review`・`fix-check` は `self`（既定の適用）。template は `.devcontainer/agent-runner.toml`（既定の適用）。

## テスト

AGENTS.md の「テストの採用基準」で S（無言のデータ損失・失敗を成功と報告しない）に当たるものだけを書く。

1. `.agents/skills/pr-review/tests/test_pr_review_workspace.py`: 保存済みセッションの submodule（`ignore=all`、パス `sub módulo`）にローカル commit を置き、非 strict の `cleanup` を CLI（`workspace.main(["cleanup", "--state", ...])`）で実行する。終了コード 1・`status: "retained"`、worktree・submodule gitdir・セッションディレクトリ・保存レビューが残り、commit オブジェクトが `git cat-file -e` で読めること。正常対照として、同じ fixture の clean な submodule セッションは非 strict `cleanup` で終了コード 0 で退役すること（既存の正常対照テストがあればそれを使い、重複させない）。
2. `.agents/skills/pr-review/tests/test_review_run.py`: 通常の `review_run.complete` の経路で、submodule（`sub módulo`）にローカル commit があり、親 worktree の HEAD は固定 commit のままの場合、保存は成功し（`review_file`・`findings_file` が存在する）、新しい検査が submodule の HEAD と gitlink の不一致で cleanup を拒否して `status: failed`・`cleanup: failed`・`reason`・`retained_paths` が返り、worktree・submodule の commit オブジェクト・state_file が残ること。親 worktree の HEAD を変える入力は使わない（save の `verify_state` が先に "pinned commit" で拒否し、cleanup に到達しないため）。clean な通常完了が `cleanup: success` で退役する既存テストが正常対照になる。

既存の strict 退役テスト、保存ロック・version 7/8・pinned ref・候補一覧のテストは変えずに全て通ること。

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04、git、uv）。ローカルの実 Git fixture（`tmp_path`）。実モデルの起動・実 PR の削除はしない。
- 実入力: 非 ASCII・空白を含む submodule パス `sub módulo`、`ignore=all` の submodule、submodule 内のローカル commit（複数行の `local.txt`）。親 worktree の HEAD は固定 commit のまま（CLI の cleanup・complete の両経路で同じ入力）。親 worktree の HEAD 不一致は complete では save が先に拒否するので、この Issue の入力にしない。
- 防御範囲: 対象は非 strict `cleanup`（CLI と `review_run.complete` の両方の入口）が、`_require_clean_worktree` が拒否する状態のセッションを消さないこと。対象外の反例: clean な保存済みセッション（submodule の有無に関わらず）は従来どおり退役する。cache（`.venv`・`__pycache__` など）だけの ignored ファイルは退役を妨げない。strict 退役の判定内容は変えない。
