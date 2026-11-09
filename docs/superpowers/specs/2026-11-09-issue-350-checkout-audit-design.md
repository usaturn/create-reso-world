# Issue #350: agent-runner の checkout 監査を保護する checkout とそれ以外に分ける

## 管理

- 文書管理リポジトリ: usaturn/create-reso-world（`DOC_ROOT` は実装の worktree `.worktrees/issue-350-checkout-audit-impl`、ブランチ `feat/issue-350-checkout-audit`。planning の版 `8e6a8eeb` は `.worktrees/issue-350-checkout-audit`（ブランチ `docs/issue-350-checkout-audit`）で作り、実装のブランチに fast-forward で取り込んだ）
- 対象: usaturn/create-reso-world、[#350](https://github.com/usaturn/create-reso-world/issues/350)（親 [#349](https://github.com/usaturn/create-reso-world/issues/349) のボードの key `checkout-audit`）
- 検証したコードの HEAD: `origin/main` の `690001b64ade22e91dfe54a9ad84a12c5d63931a`
- 移植元: usaturn/agent-workspace `0eea76aa` の #756（`f8eebecc`・`a6775eaa`・`ae606ed3`・`396bdca6`）
- 状態: draft
- 内容の承認: なし
- 実行許可: 2026-11-08T16:24Z の利用者の指示（加えて、停止の後の設計の変更と再開の指示 R8・R9） `/issue-to-pr #350 --implement claude-code_sonnet_default --merge --assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`。許可された範囲は、この Spec・Plan の実装、検証、commit、push、`main` 向けの PR 1 つの作成、PR 修正ループ（pr-review-fix-loop）、ループの `finalize.py` によるマージ（修正不要のときだけ）。内容の承認ではないので、状態は `draft` のまま。planning の時点の利用者の指示「#349 着手」は planning（Spec → Plan → handoff）だけの指示だった
- 関連する文書: Plan `docs/superpowers/plans/2026-11-09-issue-350-checkout-audit.md`、#187 の Spec `docs/superpowers/specs/2026-10-20-issue-187-checkout-audit-spec.md`、#243 の Spec `docs/superpowers/specs/2026-10-23-create-reso-world-issue243-remove-dsh-design.md`

## 意図と理由

runner は、開始前から登録されていたすべての checkout の内容を実行の前後で比べ、変化をすべて `outside_changes` に入れる。厳密な利用側（issue-to-pr の `implement_task`、review-verify の `dispatch` の accept、review-fix-planning の `run_roles`）は `outside_changes` があれば受け取らない。

create-reso-world では、ボードの子や PR の修正を複数のセッションが並行して進め、それぞれが自分の worktree を編集・回収する。今の監査は書き込み元を特定できないので、ほかのセッションの通常の作業だけで、費用をかけた実装・修正の確認・役割の実行が拒否される。#187 は DSH で隔離した担当に限って必須の監査を狭めたが、#243 で DSH を外したため、全登録で受け取りを止める挙動に戻っている。

agent-workspace の #756 は、run が「保護する checkout」（依頼された checkout と main worktree）を決め、保護する checkout の変化と監査できない登録だけで受け取りを止め、ほかの checkout の内容の変化と登録ごとの回収は `unprotected_changes` として報告する形にした。この子はそれを create-reso-world の設計（起動前の preflight・`checkout_policy`・`dsh_removed`）を保ったまま取り入れる。

## 目標

- 保護する checkout（依頼された `repository` の checkout。特定できなければ全登録）の `content_changed`・`removed`・`unavailable_*` は `outside_changes` に入り、3 つの利用側の受け取りを止める
- 保護しない checkout（main worktree＝親の checkout を含む）の `content_changed`・`removed`・`unavailable_*` は `unprotected_changes` に入り、受け取りを止めない（R8）
- 起動前の preflight は、保護する checkout が監査できないときだけ有料の起動の前に止まる。保護しない checkout が監査できなくても起動し、`unavailable_before` として `unprotected_changes` に報告する（R8）
- 受け取りを止めるかの判定を `workspace.blocks_acceptance` の 1 か所に置き、runner と `dispatch` の accept が同じ判定を使う
- 古い記録を安全側に読む: `protected` の無い `checkout_audit` は保護として、`unprotected_changes` の無い `BatchResult` は空として読む
- `run_roles` と `dispatch` は、修正を持つ worktree（HEAD が `revision`／`to` の checkout）以外を `repository` に渡されたら、起動・予約・出力先の作成の前に入力の誤りで止まる

## 目標にしないこと

- adapter（`tools/agent_runner/adapters/**`）の変更。create-reso-world の方が新しく厳しい
- `checkout_policy.py`・`require_auditable_workflow`・runner の起動前 preflight（`require_auditable_checkouts`）の撤去。preflight は残し、止める範囲だけを保護する checkout に狭める（R8。`checkout_policy.py` は docstring だけを直し、コードは変えない）
- `config.py` の `dsh_removed` ガード、`.devcontainer/install_beforehand.bash` の最小の個人設定
- `issue-to-pr/scripts/implement_task.py` の変更（`issue-review-steps`（#353）が所有する。`summarize` に `unprotected_changes` を足すのは #353）
- `tools/agent_runner/runtimes/*.rst` のうち、`cursor.rst` の既知の制限の 1 文以外
- 書き込み元の特定、ほかのセッションの登録の自動回収・repair・prune

## 避けること

- 保護する checkout の変化を、黙って受け取ること
- 古い記録（`protected` の無い観測）を保護しない側に読み、受け取りを通すこと
- 実行後に登録を一覧できないときに、消えた checkout を `removed`（受け取りを止めない）と分類すること。登録を一覧できなければ `unavailable_after` のままにする
- 依頼された checkout を特定できないとき（bare repository、`--show-toplevel` が取れない、どの登録とも実パスが一致しない）に、全登録を保護しない側に分類すること。特定できなければ全登録を保護する（R8 の「どうしようもない場合」）
- 依頼された checkout の監査不能を、ほかの checkout と同じく報告だけで通すこと
- `repository` の HEAD の検査を、self-review の 1 回枠の予約・出力先の作成・`require_auditable_workflow` の後に置くこと（拒否しても枠を消費してしまう）

## 受け入れる残りのリスク

`writes = false` は runner の指示であり sandbox ではないので、担当がほかのセッションの worktree に書き込むことはありうる。この変更の後、その書き込みは `unprotected_changes` に出るだけで受け取りを止めない。#187 の C3 と #243 が保った「全登録の内容の変化で受け取りを止める」は、この子で「保護する checkout の変化と、全登録の監査不能で止める」に置き換わる。

親 #349 の利用者の決定（2026-11-09）が `agent-runner` の堅牢化として #756 の移植を対象にしているので、この置き換えを受け入れる。

さらに 2026-11-08T17:33:08Z の直前の利用者の指示（R8）で、並列作業を優先し、main worktree（親の checkout）の変化と、ほかの checkout の監査不能でも止めないことにした。#756 は main worktree を保護し、監査できない登録をどの checkout でも止めるが、create-reso-world ではそれもやめる。そのため、次のリスクを受け入れる。

- 担当が親の checkout（`PARENT_ROOT`）やほかのセッションの worktree に誤って書き込んでも、`unprotected_changes` に出るだけで受け取りは止まらない
- ほかの checkout が監査できないときは、その checkout で何が起きたかを確かめられないまま受け取る

次で影響を抑える。

- 依頼された checkout（成果を持つ worktree）は保護したまま。その変化・消失・監査不能は、起動前・実行後のどちらでも止める
- 依頼された checkout を特定できないときは全登録を保護する
- 起動の時点で登録を一覧できなければ止める（依頼された checkout を見つけられない）
- `unprotected_changes` は runner の結果、`dispatch`・`run_roles` の出力、ループの記録に残す。利用者・controller はそれを見て、必要なら成果を確かめ直す

実行中に別のセッションが親の checkout を動かしても（repo-cleanup-after-merge の `origin/main` への追従など）、受け取りは止まらない。

## 設計

### `tools/agent_runner/workspace.py`

- モジュールの docstring に、保護する checkout と `blocks_acceptance` の説明を足す
- `CheckoutSnapshot(common_dir: Path | None = None)` に `protected: set[str]` と `common_dir` を足す。`common_dir` は、実行後に依頼された checkout が消えていても登録を一覧し直すために使う
- `_toplevel(repository) -> str | None`: `git rev-parse --show-toplevel` の実パス（`os.path.realpath`）。行末の改行だけを除く（パスに改行を含みうる）。checkout が無い（bare など）か取得できなければ `None`
- `_registered(common_dir) -> set[str] | None`: `git worktree list --porcelain -z` の `worktree ` 行のパスの集合。一覧できなければ `None`
- `snapshot_checkouts(repository)`:
  - `CheckoutSnapshot(git_common_dir(repository))` で作る
  - 実パスが `_toplevel(repository)` と同じ登録を保護する。`_toplevel` が `None` のとき、またはどの登録とも一致しないときは全登録を保護する（R8。main worktree は、依頼された checkout でなければ保護しない）
  - 開始前に監査できない登録の `CheckoutAudit` にも `protected` を入れる
- `require_auditable_checkouts`: 指紋が `None` の登録のうち、保護する checkout のものだけで `CheckoutAuditError` を投げる。保護しない checkout の失敗は snapshot（`None` と `failures`）に残し、`audit_checkouts` が `unavailable_before`（`protected=False`）として報告する。登録を一覧できないとき（`snapshot_checkouts` の `WorkspaceError`）は今までどおり止める（R8）
- `audit_checkouts(before)`:
  - 各観測に `protected`（`CheckoutSnapshot` なら保護集合に含まれるか。通常の dict なら常に `True`）を入れる
  - 実行後に読めない checkout は、いったん `unavailable_after` として集める。全指紋の後に `common_dir` で登録を 1 回だけ一覧し、一覧できて、そのパスが登録に無ければ `kind="removed"` にする。一覧できない・`common_dir` が無い・通常の dict の場合は `unavailable_after` のまま
  - `removed` の `reason` は読めなかった理由（`checkout_missing` など）をそのまま使う。`AuditReason` は増やさない
  - 結果はパスの順に並べる
- `blocks_acceptance(finding) -> bool`: `finding.protected`（R8。kind によらない。`protected` の無い古い記録は `True` なので止める）
- `changed_checkouts` は今のまま（全観測のパス）

### `tools/agent_runner/models.py`

- `CheckoutAudit.kind` に `removed` を足す。`protected: bool = True` を足し、docstring に「古い記録は保護として読む」を書く
- `BatchResult.unprotected_changes: list[str] = Field(default_factory=list[str])` を足し、docstring に `outside_changes` との違いと古い記録の読み方を書く
- `BatchResult._legacy_unrelated_audit` は残す

### `tools/agent_runner/runner.py`

- 開始前は今のまま `before = require_auditable_checkouts(repository)` を使う。この関数は内部で `snapshot_checkouts` を呼び、保護集合と `common_dir` を持つ snapshot を返す（決定 D1）
- 結果の `outside_changes` は `blocks_acceptance` が真の観測のパス、`unprotected_changes` は偽の観測のパスにする

### `.agents/skills/review-verify/scripts/dispatch.py`

- `from`/`to` を解決した後、同じ `try` で `head = resolve_revision(repository)` を得る。`head != data.to` なら `ValueError(REPOSITORY_NOT_AT_TO)` で止める。`require_auditable_workflow`・`verified_file` の読み込み・出力先の作成より前に置く
- `REPOSITORY_NOT_AT_TO` を `REQUEST_ERRORS` に足し、`main` が終了コード 2 と stderr の理由を返すようにする
- `check_batch`: 監査不能の検査と変化の検査を `blocks_acceptance` に揃える。`unavailable_*` の観測は `blocks_acceptance` が真のものだけで「run が保護する checkout を監査できない」として止め、`if diagnostics or batch.get("outside_changes")` を `if any(blocks_acceptance(item) for item in diagnostics) or batch.get("outside_changes")` にし、メッセージを「run が保護する checkout が変わった・消えた」に直す（R8）
- `main` の出力に `"unprotected_changes": batch.get("unprotected_changes", [])` を足す。終了コードの判定（`outside_changes` と `review_changes`）は変えない
- accept の経路では `unprotected_changes` を添字で読まない（変更前に保存した `dispatch.json` で `KeyError` にしない）

### `.agents/skills/review-fix-planning/scripts/run_roles.py`

- `source_head`/`revision` を解決した後、同じ `try` で `head = resolve_revision(repository)` を得る。`head != data.revision` なら `RoleInputError` で止める。出力先の検査・`require_auditable_workflow`・`write_exceptions`・self-review の予約より前に置く
- 出力に `"unprotected_changes": batch.unprotected_changes` を足す。終了コードの判定（`outside_changes` だけ）は変えない

### `.agents/skills/pr-review-fix-loop/scripts/loop.py`

- `BatchInfo` に `unprotected_changes: list[str] = Field(default_factory=list[str])` を足す（古い記録は空）
- `_review_batch` の `BatchInfo` と `review` の出力に `unprotected_changes` を入れる。ループは今までどおり警告だけで止めない
- Herdr 節・reconcile・診断のコードは変えない

### 文書（この子の範囲）

- `tools/agent_runner/interfaces.rst`: `BatchResult` の項目に `unprotected_changes` を足す。「期限と保持」の監査の段落を書き直す（保護する checkout の決め方＝依頼された checkout だけ、特定できなければ全登録、main worktree も依頼された checkout でなければ保護しないこと、`checkout_audit` の項目と 4 つの `kind`、`outside_changes` と `unprotected_changes` の違い、ほかの checkout の監査不能も報告だけであること、利用側が `outside_changes` だけで拒否すること、`blocks_acceptance`、古い記録の読み方、実行中に登録された checkout は監査しないこと、起動前の preflight が止まるのは保護する checkout が監査できないときと登録を一覧できないときだけであること）。`docs/agent-runner-checkout-recovery.md` への参照の文から、DSH を外した後は成り立たない「非隔離担当での直列運用」を外し、「消えた登録の所有者の照合・個別 repair / remove」だけを指す。冒頭の全体説明・CLI 例・`dsh_removed`・個人設定の説明は変えない
- `tools/agent_runner/checkout_policy.py`: モジュールと `require_auditable_workflow` の docstring だけを、保護する checkout の preflight に直す。コードは変えない（R8）
- `tools/agent_runner/runtimes/cursor.rst`: 「既知の制限」の `outside_changes` の 1 文だけを直す。実機の観測の記録（161・172 行付近）は当時の記録なので変えない
- `.agents/skills/review-fix-planning/references/execution.md`: `repository` は修正を持つ `MAIN_ROOT` で HEAD が `revision` と同じであること、違えば `run_roles` が起動・予約の前に終了コード 2 で止まること、runner がこの checkout だけを保護すること（ほかの checkout の変化・回収・監査不能は `unprotected_changes` に報告だけ）を書く。出力の項目に `unprotected_changes` があれば足す
- `.agents/skills/review-verify/references/fix-check.md`（決定 D3）: `repository` の行（HEAD が `to` の checkout）、dispatch の出力の項目と意味、受け取らない条件を直す

### 文書（所有の移動を親に提案するもの）

次の文は、この変更の後に実際の挙動と食い違う。#350 の「変更してよい」に無い（または別の子が所有する）ので、親 #349 にコメントで所有の移動を提案し、coordinator が認めたときだけ編集する（決定 D4）。

- 提案は、この planning のセッションが #349 に投稿する
- coordinator は利用者（または利用者が指名したセッション）とする
- 実装担当は返事を待たない。着手時に #349 の実行マップと全コメントを読み、承認があるファイルだけを直す。承認が無ければ編集せず、PR の本文に残る食い違いとして書き、#349 にその旨をコメントする

| ファイル | 食い違う記述 | 所有 |
| --- | --- | --- |
| `.agents/monitoring-runtimes.md` | 69 行目「既存の checkout の外部の変更は `outside_changes` として報告される」 | どの子にも無い |
| `.agents/skills/pr-review-fix-loop/references/records.md` | `review.batch` の行（`outside_changes` だけを挙げる） | `loop-reconcile`（reconcile 節）・`review-eval-hooks`（収集の注記）。この行はどちらの節でもない |
| `.devcontainer/README.md` | 927 行目付近の cursor の段落「runner が `outside_changes` として事後に報告する」 | `issue-review-steps`（#353） |
| `docs/agent-runner-checkout-recovery.md` | 3 行目「並行作業中の別 checkout の変化も成果の受け取りを拒否する理由になる。書き込みを伴う依頼は、ほかのセッションが停止しているときに行う」「隔離した担当で必須監査を限定できる条件」 | どの子にも無い |

## インターフェース

- `CheckoutAudit`: `path` / `kind`（`unavailable_before` | `unavailable_after` | `content_changed` | `removed`）/ `reason` / `locked` / `prunable` / `protected`（既定 `True`）
- `BatchResult`: `outside_changes`（保護する checkout の全観測）、`unprotected_changes`（保護しない checkout の全観測＝`content_changed`・`removed`・`unavailable_*`。既定 `[]`）、`checkout_audit`（R8）
- `workspace.blocks_acceptance(finding) -> bool`
- `workspace.snapshot_checkouts(repository) -> CheckoutSnapshot`（`protected`・`common_dir` を持つ）
- エラーの分類は変えない。起動前の preflight は `CheckoutAuditError` のまま。`dispatch`・`run_roles` の HEAD の検査は入力の誤り（終了コード 2）
- この子が `tools/agent_runner` の監査 API を定義する。#353・#356・#357 は使うだけで定義を変えない

## テスト

`AGENTS.md` の「テストの採用基準」に従い、S に当たる守りだけを足す・直す。

| テスト | 区分 | 防ぐ損害 |
| --- | --- | --- |
| `test_workspace.py` に、依頼された checkout の変化（止める）・main worktree の変化（止めない）・ほかの checkout が登録ごと消えた（`removed`、止めない）・ほかの checkout が登録を残して消えた（`unavailable_after`、止めない）を 1 つの parametrize で確かめるテスト（R8 で期待値を直す） | S | 依頼された checkout の変化を黙って受け取る。逆に、ほかの checkout の変化で受け取りを止めて並列作業を妨げる |
| `test_workspace.py` に、symlink 経由で渡された checkout を保護するテスト | S | パスの表記の違いで依頼された checkout を保護しない側に分類し、その変化を受け取る |
| `test_workspace.py` に、bare repository（自身の checkout が無い）では全登録を保護するテスト | S | 対象を特定できないときに全部を保護しない側に分類する |
| `test_workspace.py` に、依頼された checkout の実パスがどの登録とも一致しないとき全登録を保護するテスト（`_toplevel` を差し替える。R8 で追加） | S | 対象を見失ったときに、依頼された checkout の変化を受け取る |
| ~~`test_workspace.py` に、実行後に登録を一覧できないとき消えた checkout を `unavailable_after`（止める）にするテスト~~（R8 で削除。ほかの checkout の `removed` と `unavailable_after` はどちらも報告だけになり、受け取りの判定に関わらない） | — | — |
| `test_workspace.py` の `test_audit_diagnoses_unavailable_baseline` を、ほかの checkout の監査不能は `protected: False` で `blocks_acceptance` が偽、`require_auditable_checkouts(repository)` は止めずに snapshot の `failures` に残し、監査できない checkout 自身を依頼すると `CheckoutAuditError`（`SECRET` を含まない）で止まる、に直す（R8） | 既存の S を直す | 依頼された checkout の監査不能で起動してしまう。ほかの checkout の監査不能で起動を止めて並列作業を妨げる。診断に秘密が漏れる |
| `test_checkout_policy.py` の `test_unavailable_registration_blocks_work_without_launch_or_repair` を、ほかの checkout が監査できなくても起動して `unprotected_changes` に報告し、登録を repair しない、監査できない checkout 自身を依頼すると起動しない（`RunnerError`、出力先を作らない）、に直す（R8） | 既存の S を直す | 依頼された checkout を監査できないまま有料の起動をする。ほかの checkout のせいで起動を止める |
| `test_checkout_policy.py` の `test_batch_reports_parallel_checkout_edit` の期待値を `outside_changes == []`、`unprotected_changes == [neighbor]`、観測の `protected` が偽に直す | 既存の S を直す | runner が分類を結果に正しく分けない |
| `test_dispatch.py` に、`protected` の無い古い `content_changed` の記録を accept が拒否するテスト | S | 古い記録を保護しない側に読んで受け取る |
| `test_dispatch.py` に、ほかの checkout の内容の変化があっても dispatch が終了コード 0、`unprotected_changes` に出て、accept が受け取るテスト（1 件） | D 規則の通る例 | 何でも拒否する実装で古い記録のテストが通ってしまうのを防ぐ |
| `test_dispatch.py` に、HEAD が `to` でない `repository` を起動・出力先の作成の前に拒否し、`main` が終了コード 2 を返すテスト | S | 修正の worktree が保護されず、その変化を受け取る |
| `test_run_roles.py` に、self-review で HEAD が `revision` でない `repository` を予約・起動の前に拒否し、修正の worktree を渡すと通るテスト | S | 修正の worktree が保護されない。拒否しても 1 回枠を消費する |
| `test_dispatch.py` の `test_accept_does_not_attribute_a_disappeared_checkout_to_content_changes` と `test_fix_check_environment_preflight_does_not_launch` を削除する（R8） | — | ほかの checkout の消失・監査不能は報告だけになり、受け取り・起動を止めない。通る例は上の 1 件が代表する（D）。依頼された checkout の監査不能で起動しない守りは、それを実装する `checkout_policy`／runner のテスト（上の `test_checkout_policy.py`）に置く |

足さないもの（理由）:

- ループの `BatchInfo`・`review` の出力に `unprotected_changes` が入るテスト（AW の `test_review_reports_other_sessions_worktrees_apart_from_outside_changes`）: `_review_batch` は BatchResult 全体を `review-result.json`（`result_file`）に保存するので、`BatchInfo` に項目が無くても記録から消えない。項目の有無だけを見るテストは S に当たらない。実装時に一時的な確認で確かめる

- runner の層で `outside_changes`/`unprotected_changes` を分けるテスト（AW の `test_other_checkouts_are_reported_apart_from_outside_changes`）: `test_checkout_policy.py` の既存テストの修正と重なる（D）
- `run_roles` の「ほかのセッションの worktree で終了コード 1 にしない」「修正の worktree の変化は `outside_changes`」: runner の分類の守りと重なる（D）。`run_roles` は `outside_changes` だけで判定し、自分では分類しない
- AW の `project` の parametrize: create-reso-world に `projects.toml` が無い（D）
- 変更前の `dispatch.json` を accept しても `KeyError` にならないこと: 壊れればトレースバックか終了コード 2 で現れる（L）。実装時に一時的な確認で確かめる
- 出力・記録の項目の有無だけを見るテスト（`run_roles` の出力の `unprotected_changes` など）: S に当たらない

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04、Python は `uv` の管理）、リポジトリのルートを cwd にした `uv run pytest`。実 API・実 PR・有料の runner の起動はせず、偽の adapter と一時的な Git リポジトリだけを使う
- 実入力: 改行・非 ASCII を含む checkout のパス（例 `対象 checkout\n改行`）、symlink 経由のパス、bare repository、`git worktree remove --force` による回収、`shutil.rmtree` による登録を残した消失、`protected` の無い古い `checkout_audit`、`unprotected_changes` の無い古い `dispatch.json`
- 防御範囲: 保護する checkout（依頼された checkout。特定できなければ全登録）の変化・消失・監査不能（起動前・実行後）、起動時に登録を一覧できないこと、古い記録、修正の worktree 以外を `repository` に渡す誤り。対象外（報告だけ）は、保護しない checkout（main worktree を含む）の内容の変化・登録ごとの回収・監査不能。監査しないものは、実行中に登録された checkout（runner の試行を含む）、Gitignored の資源（R8）
- 検証:
  - `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/tests/test_models.py` が成功する
  - `uv run pytest .agents/skills/review-verify/tests/test_dispatch.py .agents/skills/review-fix-planning/tests/test_run_roles.py .agents/skills/pr-review-fix-loop/tests/test_loop_review.py .agents/skills/issue-to-pr/tests/test_implement_task_run.py` が成功する（`test_implement_task_run.py` は変えずに、保護する checkout の変化を拒否し続けることの退行確認）
  - `bash scripts/check-layout.sh` が成功する
  - 手動: `/tmp` の `mktemp -d` の中に一時的な Git と linked worktree を 2 つ作り、一方を依頼の checkout、他方を「別セッション」として内容を変え、`outside_changes` と `unprotected_changes` の分かれ方を確かめる。片付けは空値ガード付きの `rm -rf`
- 退行防止: adapter の解析・pr-review の version 8・`review_dir` の保護・#212 の診断・merged の 3 値・`--spec-commit` の既存テストが通る

## 依存の証拠

- 先行: なし（#350 の `blocked_by` は空。2026-11-08T15:59Z に確認）
- 後続: `issue-review-steps`（#353）・`loop-reconcile`（#356）・`review-eval-hooks`（#357）がこの子の API を使う
- 完了の条件: この子が `state_reason=completed` で close され、API と利用側の出力が `main` にあること

## 決めたこと（エージェントの判断。利用者の承認ではない）

| ID | 決めたこと | 検討した別案 | 理由 |
| --- | --- | --- | --- |
| D1 | runner の開始前は `require_auditable_checkouts` のままにする。保護集合はこの関数が内部で呼ぶ `snapshot_checkouts` から得る | AW のように runner で `snapshot_checkouts` を直接呼ぶ | Issue が runner の preflight の撤去を禁じている。Issue の「開始前の snapshot は `snapshot_checkouts` を使う」は、内部で使うことで満たす |
| D2（R8 で置き換え） | `require_auditable_checkouts` は create-reso-world の実装（指紋が `None` の全登録を拾う）を残す | AW の `snapshot.failures` だけを見る形 | 実質は同じで、失敗の記録が欠けても止まる今の形の方が安全 |
| D3 | review-verify の受け取り条件は `references/fix-check.md` を直し、`SKILL.md` は変えない。承認は求めず、#349 への提案のコメントで読み替えを知らせる | Issue の文面どおり `SKILL.md` を直す／D4 の 4 ファイルと同じく承認を求める | Issue は「受け取り条件の該当節」と内容で範囲を指定しており、create-reso-world ではその節が `references/fix-check.md` にある（`SKILL.md` に該当の文が無い）。Issue が意図した範囲の置き場所の読み替えで、範囲の拡大ではない。D4 の 4 ファイルは Issue が触れていない内容なので扱いを分ける。ほかの子の所有でもない |
| D4 | 範囲外の 4 ファイルの食い違いは、親 #349 に所有の移動を提案し、coordinator が認めたときだけ編集する。認められなければ編集せず、PR の本文に残る食い違いとして書く | 黙って範囲を広げる／食い違いを放置する | 親の「共有インターフェースと所有」が、ほかの子の所有ファイルの編集を禁じ、親のコメントでの提案を求めている |
| D5 | テストは S の守りだけを移植し、AW の runner の層・`run_roles` の重なるテストと `project` の parametrize を移植しない | AW のテストをすべて移植する | `AGENTS.md` の採用基準（S のみ、D は代表 1 件） |
| D6 | HEAD の検査は、`dispatch` は `require_auditable_workflow` と出力先の作成の前、`run_roles` は出力先の検査・`require_auditable_workflow`・予約の前に置き、入力の誤り（終了コード 2）にする | preflight の後に置く | 拒否したときに枠の消費・出力先の作成・監査の副作用を残さない |
| D7 | `cursor.rst` は「既知の制限」の 1 文だけを直し、実機の観測の記録は変えない | 観測の記録も新しい項目名に書き換える | 観測は当時の runner の出力の記録で、書き換えると事実が変わる |
| D8 | `removed` の `reason` は読めなかった理由を使い、`AuditReason` に値を足さない | `removed` 用の reason を足す | AW と同じ。`kind` で区別でき、保存済みの記録の検証を広げずに済む |
| D9 | Spec・Plan はこのブランチにコミットし、実装の PR（`Refs #350`）にコードと一緒に含める。文書だけの PR は作らない | 文書専用の PR | `AGENTS.md`「Spec・Plan の保存と公開」 |
| D10（R8 で置き換え） | 実行中に親の checkout（main worktree）が動いて受け取りが止まる制限は変えず、`interfaces.rst` に注意を書く | main worktree の HEAD の移動を保護の対象から外す | 今の挙動から変わらない既存の制限で、Issue が main worktree の保護を明記している。main worktree への誤った書き込みを止める守りを弱めない |
| D11 | ループの記録の項目のテストはコミットしない | AW のテストを移植する | `result_file` に BatchResult 全体が残るので記録は消えず、S に当たらない（builder check の指摘） |
| D12 | HEAD の検査は `run_roles` の全 phase（implement・self-review）に掛け、テストは self-review の 1 件にする | phase ごとにテストする | 検査は phase の分岐より前の 1 か所にある（D）。self-review は 1 回枠の予約もあるので、予約を消費しないことも同じテストで確かめられる |

## 実行の決定記録（issue-to-pr の run。エージェントの判断。利用者の承認ではない）

2026-11-08T16:24Z からの run（Claude Code / Opus 5.5、session `820ddf33-cf9c-4fd8-8f60-1c496bed5001`）で決めたこと。設計（D1〜D12）は変えない。

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| R1 | Plan の Task の実装担当は `claude-code_sonnet_default`（`fallback` なし。`implement_task.py check` の結果 `self: false`） | 雛形の既定 `self` | 利用者の指定 `--implement claude-code_sonnet_default` | 利用者の指示。担当の `failed`、再試行の上限に達した `retry`・`rejected` では止まり、このセッションが実装を引き取らない |
| R2 | ループの担当は、レビュー修正の `implement` が `claude-code_sonnet_default`、レビューの `inspect` が `pi_openai-codex_gpt6-sol_max`。サイクルの上限 3 と雛形 `.devcontainer/agent-runner.toml` は既定の適用（`self-review`・`fix-check` は `self`） | 個人設定の既定のまま | 利用者の指定 `--assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`（`loop.py check-options` が終了コード 0） | 利用者の指示。ループの停止・エラーでは止まる |
| R3 | 実行方式は、`superpowers:subagent-driven-development` の形で、各 Task を `implement_task.py run` で runner の担当に 1 つずつ順に依頼する。Task のレビューはこのセッションのサブエージェントが行う | このセッションが実装する（executing-plans） | issue-to-pr の 4 章の表（`self` が false） | issue-to-pr の手順 |
| R4 | Task 6（範囲外の 4 ファイル）は行わない。PR の本文に「残る食い違い」として書き、#349 にコメントする | 承認を待つ／黙って直す | #349 の所有の移動の提案（issuecomment-6723859987）に、着手時（2026-11-08T16:24Z）の時点で coordinator の返事が無く、実行マップも変わっていない。Plan の Task 6 の前提のとおり返事を待たない | D4・Plan の Task 6 |
| R5 | 実装のブランチは `feat/issue-350-checkout-audit`（worktree `.worktrees/issue-350-checkout-audit-impl`）を `main` の `690001b6` から作り、planning の commit `8e6a8eeb` を fast-forward で取り込む。planning の worktree・ブランチ `docs/issue-350-checkout-audit` は消さずに残す | planning のブランチ `docs/issue-350-checkout-audit` で実装を続ける | issue-to-pr の名前の規則（`feat/issue-N-<要約>`）と、捕捉した base の SHA から新しい worktree を作る手順。commit をそのまま取り込むので、公開した manifest の版（`8e6a8eeb`）と同じ内容が PR に入る | issue-to-pr の 3 章 |
| R6 | PR の Issue の指定は `Refs #350`。close と親 #349 の更新はマージの後に coordinator が行う | `Closes #350` | ボードの子（issue-to-pr の 5 章）で、#350 の本文も `Closes` を禁じている | issue-to-pr の 5 章 |
| R7 | 実装の claim `refs/heads/agent-claims/issue-350`（`8f0e0941c6ed30efa495a43997fec4067b16040c`）を取り、ループの `finish` の後に結果を #350 に書いてから解放する | claim を取らない | `planning-parallel-issues` と handoff の「受け手は新しい claim を取る」 | `planning-parallel-issues` |
| R8 | 利用者の指示「親の checkout（main worktree）が動いた場合と、監査できない登録がある場合でも、どうしようもない場合を除き、計画を修正して続行するようにして」（再開の claim を取った 2026-11-08T17:33:08Z の直前、並列作業を重視する、という前置き付き）に従い、保護する checkout を依頼された checkout だけにする。main worktree の変化と、ほかの checkout の監査不能（起動前・実行後）は `unprotected_changes` に報告するだけで、起動も受け取りも止めない。`blocks_acceptance` は `finding.protected` にする。「どうしようもない場合」は、依頼された checkout（成果を持つ worktree）の変化・消失・監査不能、依頼された checkout を特定できないこと（このときは全登録を保護する）、起動の時点で登録を一覧できないこと、と定める | #756 どおり main worktree を保護し、監査不能はどの checkout でも止める（planning の D10・Issue の受け入れ） | 並列作業では、ほかのセッションが親の checkout やほかの worktree を動かすのは普通の作業で、それで止まると直列の運用になる（Task 3 の 1 回目は #351 の worktree の変化で誤って拒否された）。依頼された checkout だけが成果の正しさに関わる | 利用者の指示。Issue #350 の受け入れ・#349 の境界の文面と異なるので、#350 にコメントで記録する。`checkout_policy.py` は docstring だけを直す |
| R9 | Task 3 で止まった run を、利用者の「続行」の指示で再開する。claim を取り直し（`a8cedb41`）、Plan に Task 2A（R8 の実装）を足してから、Task 3 を同じ担当に依頼し直す。依頼には「バックグラウンドのコマンドを使わない」を足す。保存した `1373fe6d` は R8 の前の設計で作ったので取り込まない | 保存した `1373fe6d` を取り込む／担当を変える | Task 3 の要件（`check_batch` の監査不能の扱い、削除するテスト）が R8 で変わる。担当の指定は利用者のもの | 利用者の指示 |
| R10 | Task 2A は Task 1・2 の後、Task 3 の前に置き、`workspace.py`・`checkout_policy.py`（docstring）・`test_workspace.py`・`test_checkout_policy.py`・`interfaces.rst`・`cursor.rst` を直す | Task 1・2 の担当に修正を依頼する | Task 1・2 はレビュー済みで、R8 は設計の変更なので、別の Task としてレビューする方が差分が明確 | issue-to-pr の手順 |
| R11 | 引き継ぎ後（2026-11-09、Claude Code / Opus 5.5 の受け手のセッション）に `origin/main` が `690001b6` から `d790e5f3`（PR #358、#351 のマージ）に進んでいたので、未 push の 5 つの commit を `d790e5f3` に rebase し、捕捉した base を `d790e5f3` に取り直す。この run の間に `main` がまた進んでも、所有ファイルとの重なりが無く衝突しなければ、同じように rebase して続ける（PR の本文に書く）。重なり・衝突・設計の前提（preflight・`checkout_policy`）の変化があれば止まる | 止まる／`690001b6` のまま続けて PR の時点で決める | `main` の変更は pr-review・repo-cleanup・devcontainer の掃除だけで、所有ファイルと重ならず `git merge-tree` も衝突しない。rebase の前後で `git diff <base> <head>` は同じで、Task 1・2 の内容は変わらない（SHA だけが変わる） | 利用者の指示（「rebase して続行、今後も同様」）。issue-to-pr の `recheck_bases` の停止に対する利用者の判断 |
