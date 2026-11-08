# Issue #350: agent-runner の checkout 監査を保護する checkout とそれ以外に分ける

## 管理

- 文書管理リポジトリ: usaturn/create-reso-world（`DOC_ROOT` は `.worktrees/issue-350-checkout-audit`、ブランチ `docs/issue-350-checkout-audit`）
- 対象: usaturn/create-reso-world、[#350](https://github.com/usaturn/create-reso-world/issues/350)（親 [#349](https://github.com/usaturn/create-reso-world/issues/349) のボードの key `checkout-audit`）
- 検証したコードの HEAD: `origin/main` の `690001b64ade22e91dfe54a9ad84a12c5d63931a`
- 移植元: usaturn/agent-workspace `0eea76aa` の #756（`f8eebecc`・`a6775eaa`・`ae606ed3`・`396bdca6`）
- 状態: draft
- 内容の承認: なし
- 実行許可: なし。利用者の指示「#349 着手」は、親の開始手順による planning（Spec → Plan → handoff）の指示であり、実装・PR・マージの許可ではない
- 関連する文書: Plan `docs/superpowers/plans/2026-11-09-issue-350-checkout-audit.md`、#187 の Spec `docs/superpowers/specs/2026-10-20-issue-187-checkout-audit-spec.md`、#243 の Spec `docs/superpowers/specs/2026-10-23-create-reso-world-issue243-remove-dsh-design.md`

## 意図と理由

runner は、開始前から登録されていたすべての checkout の内容を実行の前後で比べ、変化をすべて `outside_changes` に入れる。厳密な利用側（issue-to-pr の `implement_task`、review-verify の `dispatch` の accept、review-fix-planning の `run_roles`）は `outside_changes` があれば受け取らない。

create-reso-world では、ボードの子や PR の修正を複数のセッションが並行して進め、それぞれが自分の worktree を編集・回収する。今の監査は書き込み元を特定できないので、ほかのセッションの通常の作業だけで、費用をかけた実装・修正の確認・役割の実行が拒否される。#187 は DSH で隔離した担当に限って必須の監査を狭めたが、#243 で DSH を外したため、全登録で受け取りを止める挙動に戻っている。

agent-workspace の #756 は、run が「保護する checkout」（依頼された checkout と main worktree）を決め、保護する checkout の変化と監査できない登録だけで受け取りを止め、ほかの checkout の内容の変化と登録ごとの回収は `unprotected_changes` として報告する形にした。この子はそれを create-reso-world の設計（起動前の preflight・`checkout_policy`・`dsh_removed`）を保ったまま取り入れる。

## 目標

- 保護する checkout（依頼された `repository` の checkout と main worktree）の `content_changed`・`removed`・`unavailable_*` は `outside_changes` に入り、3 つの利用側の受け取りを止める
- 保護しない checkout の `content_changed`・`removed` は `unprotected_changes` に入り、受け取りを止めない
- 保護しない checkout の `unavailable_*` は `outside_changes` に入り、受け取りを止める（監査できない登録は、どの checkout でも拒否する）
- 受け取りを止めるかの判定を `workspace.blocks_acceptance` の 1 か所に置き、runner と `dispatch` の accept が同じ判定を使う
- 古い記録を安全側に読む: `protected` の無い `checkout_audit` は保護として、`unprotected_changes` の無い `BatchResult` は空として読む
- `run_roles` と `dispatch` は、修正を持つ worktree（HEAD が `revision`／`to` の checkout）以外を `repository` に渡されたら、起動・予約・出力先の作成の前に入力の誤りで止まる

## 目標にしないこと

- adapter（`tools/agent_runner/adapters/**`）の変更。create-reso-world の方が新しく厳しい
- `checkout_policy.py`・`require_auditable_workflow`・runner の起動前 preflight（`require_auditable_checkouts`）の撤去・変更
- `config.py` の `dsh_removed` ガード、`.devcontainer/install_beforehand.bash` の最小の個人設定
- `issue-to-pr/scripts/implement_task.py` の変更（`issue-review-steps`（#353）が所有する。`summarize` に `unprotected_changes` を足すのは #353）
- `tools/agent_runner/runtimes/*.rst` のうち、`cursor.rst` の既知の制限の 1 文以外
- 書き込み元の特定、ほかのセッションの登録の自動回収・repair・prune

## 避けること

- 保護する checkout の変化を、黙って受け取ること
- 古い記録（`protected` の無い観測）を保護しない側に読み、受け取りを通すこと
- 実行後に登録を一覧できないときに、消えた checkout を `removed`（受け取りを止めない）と分類すること。登録を一覧できなければ `unavailable_after` のままにする
- 監査できない登録を、保護しない checkout だという理由で通すこと
- `repository` の HEAD の検査を、self-review の 1 回枠の予約・出力先の作成・`require_auditable_workflow` の後に置くこと（拒否しても枠を消費してしまう）

## 受け入れる残りのリスク

`writes = false` は runner の指示であり sandbox ではないので、担当がほかのセッションの worktree に書き込むことはありうる。この変更の後、その書き込みは `unprotected_changes` に出るだけで受け取りを止めない。#187 の C3 と #243 が保った「全登録の内容の変化で受け取りを止める」は、この子で「保護する checkout の変化と、全登録の監査不能で止める」に置き換わる。

親 #349 の利用者の決定（2026-11-09）が `agent-runner` の堅牢化として #756 の移植を対象にしているので、この置き換えを受け入れる。次で影響を抑える。

- 依頼された checkout と main worktree は保護したまま
- 監査できない登録は、保護するかどうかにかかわらず止める
- 起動前の preflight は全登録を確かめ、監査できない登録があれば有料の起動の前に止める
- `unprotected_changes` は runner の結果、`dispatch`・`run_roles` の出力、ループの記録に残す

main worktree（`PARENT_ROOT`）を保護するので、実行中に別のセッションが親の checkout を動かすと（repo-cleanup-after-merge の `origin/main` への追従など）、`content_changed` として受け取りが止まる。これは今の挙動（全登録の変化で止める）から変わらない既存の制限であり、この子では変えない。`interfaces.rst` に、実行中は親の checkout を動かさないことを書く。

## 設計

### `tools/agent_runner/workspace.py`

- モジュールの docstring に、保護する checkout と `blocks_acceptance` の説明を足す
- `CheckoutSnapshot(common_dir: Path | None = None)` に `protected: set[str]` と `common_dir` を足す。`common_dir` は、実行後に依頼された checkout が消えていても登録を一覧し直すために使う
- `_toplevel(repository) -> str | None`: `git rev-parse --show-toplevel` の実パス（`os.path.realpath`）。行末の改行だけを除く（パスに改行を含みうる）。checkout が無い（bare など）か取得できなければ `None`
- `_registered(common_dir) -> set[str] | None`: `git worktree list --porcelain -z` の `worktree ` 行のパスの集合。一覧できなければ `None`
- `snapshot_checkouts(repository)`:
  - `CheckoutSnapshot(git_common_dir(repository))` で作る
  - `git worktree list` の先頭のレコード（main worktree）と、実パスが `_toplevel(repository)` と同じ登録を保護する。`_toplevel` が `None` なら全登録を保護する
  - 開始前に監査できない登録の `CheckoutAudit` にも `protected` を入れる
- `require_auditable_checkouts`: 今の create-reso-world の実装（指紋が `None` の登録をすべて拾う）を変えない
- `audit_checkouts(before)`:
  - 各観測に `protected`（`CheckoutSnapshot` なら保護集合に含まれるか。通常の dict なら常に `True`）を入れる
  - 実行後に読めない checkout は、いったん `unavailable_after` として集める。全指紋の後に `common_dir` で登録を 1 回だけ一覧し、一覧できて、そのパスが登録に無ければ `kind="removed"` にする。一覧できない・`common_dir` が無い・通常の dict の場合は `unavailable_after` のまま
  - `removed` の `reason` は読めなかった理由（`checkout_missing` など）をそのまま使う。`AuditReason` は増やさない
  - 結果はパスの順に並べる
- `blocks_acceptance(finding) -> bool`: `finding.protected or finding.kind in ("unavailable_before", "unavailable_after")`
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
- `check_batch`: 監査不能の検査は今のまま残す。`if diagnostics or batch.get("outside_changes")` を `if any(blocks_acceptance(item) for item in diagnostics) or batch.get("outside_changes")` にし、メッセージを「run が保護する checkout が変わった・消えた」に直す
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

- `tools/agent_runner/interfaces.rst`: `BatchResult` の項目に `unprotected_changes` を足す。「期限と保持」の監査の段落を書き直す（保護する checkout の決め方、bare のとき全登録、`checkout_audit` の項目と 4 つの `kind`、`outside_changes` と `unprotected_changes` の違い、利用側が `outside_changes` だけで拒否すること、`blocks_acceptance`、古い記録の読み方、実行中に登録された checkout は監査しないこと、実行中に親の checkout を動かすと受け取りが止まること）。`docs/agent-runner-checkout-recovery.md` への参照の文から、DSH を外した後は成り立たない「非隔離担当での直列運用」を外し、「消えた登録の所有者の照合・個別 repair / remove」だけを指す。起動前の `require_auditable_workflow` の文、冒頭の全体説明・CLI 例・`dsh_removed`・個人設定の説明は変えない
- `tools/agent_runner/runtimes/cursor.rst`: 「既知の制限」の `outside_changes` の 1 文だけを直す。実機の観測の記録（161・172 行付近）は当時の記録なので変えない
- `.agents/skills/review-fix-planning/references/execution.md`: `repository` は修正を持つ `MAIN_ROOT` で HEAD が `revision` と同じであること、違えば `run_roles` が起動・予約の前に終了コード 2 で止まること、runner がこの checkout と main worktree を保護することを書く。出力の項目に `unprotected_changes` があれば足す
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
- `BatchResult`: `outside_changes`（保護する checkout の全観測と、全 checkout の `unavailable_*`）、`unprotected_changes`（保護しない checkout の `content_changed`・`removed`。既定 `[]`）、`checkout_audit`
- `workspace.blocks_acceptance(finding) -> bool`
- `workspace.snapshot_checkouts(repository) -> CheckoutSnapshot`（`protected`・`common_dir` を持つ）
- エラーの分類は変えない。起動前の preflight は `CheckoutAuditError` のまま。`dispatch`・`run_roles` の HEAD の検査は入力の誤り（終了コード 2）
- この子が `tools/agent_runner` の監査 API を定義する。#353・#356・#357 は使うだけで定義を変えない

## テスト

`AGENTS.md` の「テストの採用基準」に従い、S に当たる守りだけを足す・直す。

| テスト | 区分 | 防ぐ損害 |
| --- | --- | --- |
| `test_workspace.py` に、依頼された checkout の変化・main worktree の変化・ほかの checkout が登録ごと消えた（`removed`、止めない）・ほかの checkout が登録を残して消えた（`unavailable_after`、止める）を 1 つの parametrize で確かめるテスト | S | 保護する checkout の変化や、登録が残ったままの消失を、黙って受け取る |
| `test_workspace.py` に、symlink 経由で渡された checkout を保護するテスト | S | パスの表記の違いで依頼された checkout を保護しない側に分類し、その変化を受け取る |
| `test_workspace.py` に、bare repository（自身の checkout が無い）では全登録を保護するテスト | S | 対象を特定できないときに全部を保護しない側に分類する |
| `test_workspace.py` に、実行後に登録を一覧できないとき消えた checkout を `unavailable_after`（止める）にするテスト | S | 一覧の失敗で `removed` に分類し、監査できない状態を受け取る |
| `test_workspace.py` の `test_audit_diagnoses_unavailable_baseline` の期待値に `protected: False` を足し、`blocks_acceptance` が真であることを確かめる | 既存の S を直す | 保護しない checkout の監査不能を通す |
| `test_checkout_policy.py` の `test_batch_reports_parallel_checkout_edit` の期待値を `outside_changes == []`、`unprotected_changes == [neighbor]`、観測の `protected` が偽に直す | 既存の S を直す | runner が分類を結果に正しく分けない |
| `test_dispatch.py` に、`protected` の無い古い `content_changed` の記録を accept が拒否するテスト | S | 古い記録を保護しない側に読んで受け取る |
| `test_dispatch.py` に、ほかの checkout の内容の変化があっても dispatch が終了コード 0、`unprotected_changes` に出て、accept が受け取るテスト（1 件） | D 規則の通る例 | 何でも拒否する実装で古い記録のテストが通ってしまうのを防ぐ |
| `test_dispatch.py` に、HEAD が `to` でない `repository` を起動・出力先の作成の前に拒否し、`main` が終了コード 2 を返すテスト | S | 修正の worktree が保護されず、その変化を受け取る |
| `test_run_roles.py` に、self-review で HEAD が `revision` でない `repository` を予約・起動の前に拒否し、修正の worktree を渡すと通るテスト | S | 修正の worktree が保護されない。拒否しても 1 回枠を消費する |

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
- 防御範囲: 保護する checkout（依頼された checkout と main worktree）の変化・消失・監査不能、全 checkout の監査不能、古い記録、修正の worktree 以外を `repository` に渡す誤り。対象外は、保護しない checkout の内容の変化と登録ごとの回収（報告だけ）、実行中に登録された checkout（runner の試行を含む）、Gitignored の資源
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
| D2 | `require_auditable_checkouts` は create-reso-world の実装（指紋が `None` の全登録を拾う）を残す | AW の `snapshot.failures` だけを見る形 | 実質は同じで、失敗の記録が欠けても止まる今の形の方が安全 |
| D3 | review-verify の受け取り条件は `references/fix-check.md` を直し、`SKILL.md` は変えない。承認は求めず、#349 への提案のコメントで読み替えを知らせる | Issue の文面どおり `SKILL.md` を直す／D4 の 4 ファイルと同じく承認を求める | Issue は「受け取り条件の該当節」と内容で範囲を指定しており、create-reso-world ではその節が `references/fix-check.md` にある（`SKILL.md` に該当の文が無い）。Issue が意図した範囲の置き場所の読み替えで、範囲の拡大ではない。D4 の 4 ファイルは Issue が触れていない内容なので扱いを分ける。ほかの子の所有でもない |
| D4 | 範囲外の 4 ファイルの食い違いは、親 #349 に所有の移動を提案し、coordinator が認めたときだけ編集する。認められなければ編集せず、PR の本文に残る食い違いとして書く | 黙って範囲を広げる／食い違いを放置する | 親の「共有インターフェースと所有」が、ほかの子の所有ファイルの編集を禁じ、親のコメントでの提案を求めている |
| D5 | テストは S の守りだけを移植し、AW の runner の層・`run_roles` の重なるテストと `project` の parametrize を移植しない | AW のテストをすべて移植する | `AGENTS.md` の採用基準（S のみ、D は代表 1 件） |
| D6 | HEAD の検査は、`dispatch` は `require_auditable_workflow` と出力先の作成の前、`run_roles` は出力先の検査・`require_auditable_workflow`・予約の前に置き、入力の誤り（終了コード 2）にする | preflight の後に置く | 拒否したときに枠の消費・出力先の作成・監査の副作用を残さない |
| D7 | `cursor.rst` は「既知の制限」の 1 文だけを直し、実機の観測の記録は変えない | 観測の記録も新しい項目名に書き換える | 観測は当時の runner の出力の記録で、書き換えると事実が変わる |
| D8 | `removed` の `reason` は読めなかった理由を使い、`AuditReason` に値を足さない | `removed` 用の reason を足す | AW と同じ。`kind` で区別でき、保存済みの記録の検証を広げずに済む |
| D9 | Spec・Plan はこのブランチにコミットし、実装の PR（`Refs #350`）にコードと一緒に含める。文書だけの PR は作らない | 文書専用の PR | `AGENTS.md`「Spec・Plan の保存と公開」 |
| D10 | 実行中に親の checkout（main worktree）が動いて受け取りが止まる制限は変えず、`interfaces.rst` に注意を書く | main worktree の HEAD の移動を保護の対象から外す | 今の挙動から変わらない既存の制限で、Issue が main worktree の保護を明記している。main worktree への誤った書き込みを止める守りを弱めない |
| D11 | ループの記録の項目のテストはコミットしない | AW のテストを移植する | `result_file` に BatchResult 全体が残るので記録は消えず、S に当たらない（builder check の指摘） |
| D12 | HEAD の検査は `run_roles` の全 phase（implement・self-review）に掛け、テストは self-review の 1 件にする | phase ごとにテストする | 検査は phase の分岐より前の 1 か所にある（D）。self-review は 1 回枠の予約もあるので、予約を消費しないことも同じテストで確かめられる |
