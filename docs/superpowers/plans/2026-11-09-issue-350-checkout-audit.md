# Issue #350 checkout 監査の保護区分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 文書管理リポジトリ: usaturn/create-reso-world（`DOC_ROOT` は実装の worktree `.worktrees/issue-350-checkout-audit-impl`、ブランチ `feat/issue-350-checkout-audit`。planning の版 `8e6a8eeb` は `.worktrees/issue-350-checkout-audit` で作った）
- 対象: [#350](https://github.com/usaturn/create-reso-world/issues/350)（親 [#349](https://github.com/usaturn/create-reso-world/issues/349)、key `checkout-audit`）
- 基準: `origin/main` の `690001b64ade22e91dfe54a9ad84a12c5d63931a`
- 内容の承認: なし。実行許可: 2026-11-08T16:24Z の利用者の指示 `/issue-to-pr #350 --implement claude-code_sonnet_default --merge --assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`（範囲は Spec の「管理」と「実行の決定記録」）

**Goal:** runner の checkout 監査で、依頼された checkout だけを「保護する」対象にし、ほかの checkout（main worktree を含む）の内容の変化・登録ごとの回収・監査不能は `unprotected_changes` として報告するだけにする（Spec の R8。Task 1・2 は R8 の前の設計で実装し、Task 2A で R8 に合わせる）。

**Architecture:** `tools/agent_runner/workspace.py` が保護集合と `removed` の分類と `blocks_acceptance` を持ち、runner がその判定で `outside_changes` と `unprotected_changes` を分ける。利用側（`dispatch`・`run_roles`・ループ）は `outside_changes` だけで拒否し、`unprotected_changes` を出力・記録に足す。`dispatch` と `run_roles` は、修正を持つ worktree 以外を `repository` に渡されたら起動前に止める。

**Tech Stack:** Python 3.14（`uv`）、pydantic v2、pytest、Git の linked worktree。

**Spec:** `docs/superpowers/specs/2026-11-09-issue-350-checkout-audit-design.md`

## Global Constraints

- 起動前の preflight（`require_auditable_checkouts`・`require_auditable_workflow`）を撤去・変更しない
- `tools/agent_runner/adapters/**`・`checkout_policy.py`・`config.py` の `dsh_removed`・`.devcontainer/install_beforehand.bash`・`issue-to-pr/scripts/implement_task.py` を変えない
- `BatchResult._legacy_unrelated_audit` を残す
- 古い記録: `protected` の無い `CheckoutAudit` は `protected=True`、`unprotected_changes` の無い `BatchResult` は `[]`
- `blocks_acceptance(finding)` は `finding.protected`（Spec の R8。Task 1 の時点の `finding.protected or finding.kind in ("unavailable_before", "unavailable_after")` を Task 2A で置き換える）
- 保護する checkout は依頼された checkout だけ。特定できない（`_toplevel` が `None`、どの登録とも実パスが一致しない）ときは全登録を保護する。起動前の preflight（`require_auditable_checkouts`）は保護する checkout の監査不能と登録の一覧の失敗でだけ止まる（R8）
- テストは偽の adapter と一時的な Git だけを使う。実 API・実 PR・有料の runner を起動しない
- テストは `AGENTS.md` の「テストの採用基準」の S だけをコミットする（Spec の「テスト」の表）
- 所有ファイルは #350 の「変更してよい」と、Spec の決定 D3 の `references/fix-check.md` に限る。Task 6 の 4 ファイルは、coordinator の承認があるときだけ編集する
- `/tmp` を使うときは `mktemp -d` の中に置き、`rm -rf` は `${VAR:?}` の空値ガード付きにする

## Review Focus

1. パスに改行・非 ASCII を含む checkout（`対象 checkout\n改行`）を依頼に渡したとき、保護する側に分類される（Task 1 の parametrize のパスに含める）
2. symlink 経由で依頼の checkout を渡したとき、保護する側に分類される（Task 1 の symlink のテスト）
3. 依頼された checkout の実パスがどの登録とも一致しないとき、全登録を保護して止める。依頼された checkout 自身が監査できないとき、有料の起動をしない（Task 2A の一致しない target・preflight のテスト。R8 の前の「一覧失敗で removed にしない」は、ほかの checkout が報告だけになったので守りの対象から外した）
4. 変更前に保存した `dispatch.json`（`protected` の無い観測）を accept したとき、受け取らない（Task 3 の古い記録のテスト）
5. self-review で誤った checkout を渡したとき、1 回枠を消費せずに止まる（Task 4 のテストで `activities == []` を確かめる）

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）、リポジトリのルートを cwd にした `uv run pytest`。HOME・`GIT_*` はテストの既存の隔離（`tools.test_support.plugin` の `outside_runner` など）に従う
- 実入力: 改行・非 ASCII を含む checkout のパス、symlink 経由のパス、bare repository、`git worktree remove --force` による回収、`shutil.rmtree` による登録を残した消失、`protected` の無い古い `checkout_audit`、`unprotected_changes` の無い古い `dispatch.json`
- 防御範囲:
  - 対象（止める）: 保護する checkout（依頼された checkout。特定できなければ全登録）の `content_changed`・`removed`・`unavailable_*`（起動前は有料の起動の前に止める）、起動時に登録を一覧できないこと、`protected` の無い古い観測、HEAD が `to`／`revision` でない `repository`
  - 対象外（止めない・報告だけ）: 保護しない checkout（main worktree を含む）の `content_changed`・`removed`・`unavailable_*`（R8）。実行中に登録された checkout（runner の試行を含む）は監査しない。Gitignored の資源・symlink の参照先は今までどおり範囲外
- 実行して確かめる S の条件は、各 Task の Step 1 で実装前にテストにする。S でない条件（出力の項目の有無、古い `dispatch.json` で `KeyError` にならないこと）は、統合確認の一時的な確認で確かめる

## ファイルの構成

| ファイル | 役割 | Task |
| --- | --- | --- |
| `tools/agent_runner/workspace.py` | 保護集合、`removed` の分類、`blocks_acceptance` | 1 |
| `tools/agent_runner/models.py` | `CheckoutAudit.protected`・`kind="removed"`、`BatchResult.unprotected_changes` | 1 |
| `tools/agent_runner/tests/test_workspace.py` | 分類の S のテスト | 1 |
| `tools/agent_runner/runner.py` | `outside_changes`/`unprotected_changes` の分割 | 2 |
| `tools/agent_runner/tests/test_checkout_policy.py` | 既存の隣の checkout のテストの期待値 | 2 |
| `tools/agent_runner/interfaces.rst`・`runtimes/cursor.rst` | 監査の説明 | 2・2A |
| `tools/agent_runner/workspace.py`・`models.py`（docstring）・`checkout_policy.py`（docstring）・`tests/test_workspace.py`・`tests/test_checkout_policy.py` | 保護を依頼された checkout だけにする（R8） | 2A |
| `.agents/skills/review-verify/scripts/dispatch.py`・`references/fix-check.md`・`tests/test_dispatch.py` | accept の判定、HEAD の検査、出力 | 3 |
| `.agents/skills/review-fix-planning/scripts/run_roles.py`・`references/execution.md`・`tests/test_run_roles.py` | HEAD の検査、出力 | 4 |
| `.agents/skills/pr-review-fix-loop/scripts/loop.py` | 記録と出力の `unprotected_changes` | 5 |
| `.agents/monitoring-runtimes.md`・`pr-review-fix-loop/references/records.md`・`.devcontainer/README.md`・`docs/agent-runner-checkout-recovery.md` | 食い違う文（承認があるときだけ） | 6 |

## 実装前の確認（controller）

1. 実装の worktree を最新の `origin/main` から作る（例 `.worktrees/issue-350-checkout-audit`、ブランチは実行タスクが決める）。このブランチの Spec・Plan の commit が無いホストでは、#350 の manifest から 2 ファイルを復元して sha256 を照らし、最初の commit にする
2. `origin/main` が基準 `690001b6` から進んでいれば、所有ファイルの差分を `git diff 690001b6 origin/main -- <所有ファイル>` で確かめ、Plan の行番号・前提が変わっていないかを照らす。変わっていれば contingency に従う
3. #349 の Publication ledger と #350 の全コメントを読み、所有の移動の提案（Task 6）への coordinator の判断を確かめる

確認の結果（2026-11-08T16:24Z、issue-to-pr の run）:

1. `.worktrees/issue-350-checkout-audit-impl`（ブランチ `feat/issue-350-checkout-audit`）を `690001b6` から作り、`8e6a8eeb` を fast-forward で取り込んだ。#350 の manifest から復元した 4 ファイルの sha256・バイト数は宣言値と一致し、Spec・Plan は `8e6a8eeb` の blob と同じだった
2. `origin/main` は `690001b6` のまま。行番号・前提は変わらない
3. #349 の所有の移動の提案（issuecomment-6723859987）に返事は無く、実行マップの #350 の行も変わっていない。Task 6 は行わない（Spec の R4）

### 要件照合（Spec の条件 → Task → 観測 → 検証）

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 保護する checkout（依頼された checkout。特定できなければ全登録）の変化・消失・監査不能で止める | 1・2・2A | `protected=True` の観測が `outside_changes` に入る。起動前の監査不能は起動しない | Task 1 の parametrize・symlink・bare のテスト、Task 2A の一致しない target・preflight のテスト |
| 保護しない checkout（main worktree を含む）の変化・回収・監査不能は止めない（R8） | 1・2・2A・3 | `unprotected_changes` に入り、起動し、dispatch の終了コード 0、accept が受け取る | Task 2A の parametrize・`test_checkout_policy.py`、Task 3 の通る例 |
| 古い記録を安全側に読む | 1・3 | `protected` 無しは `True`、`unprotected_changes` 無しは `[]` | Task 3 の古い記録のテスト、統合確認の一時的な確認 |
| HEAD が `to`／`revision` でない `repository` を起動前に拒否 | 3・4 | 終了コード 2、出力先・予約を作らない | Task 3・4 のテスト |
| 起動前の preflight を残す | 2（変えない） | `require_auditable_checkouts`・`require_auditable_workflow` が残る | 統合確認の `git diff` と既存テスト |
| 利用側が同じ判定を使う（共有条件） | 統合確認（controller） | runner の `outside_changes` と dispatch の accept が同じ `blocks_acceptance` を使い、`run_roles`・ループは `outside_changes` だけで判定する | 統合確認の手動確認と全体レビュー |

共有する条件は「受け取りを止める判定」（`blocks_acceptance`）と「古い記録の読み方」で、統合確認で controller が runner・dispatch・run_roles・loop を通して確かめる。

---

### Task 1: 保護集合・`removed`・`blocks_acceptance`

テスト: 要（S）。保護する checkout の変化や監査不能を黙って受け取る損害を防ぐ。

**Files:**
- Modify: `tools/agent_runner/models.py`（`CheckoutAudit`・`BatchResult`）
- Modify: `tools/agent_runner/workspace.py`（`CheckoutSnapshot`・`snapshot_checkouts`・`audit_checkouts`、新しい `_toplevel`・`_registered`・`blocks_acceptance`）
- Test: `tools/agent_runner/tests/test_workspace.py`

**Interfaces:**
- Produces:
  - `CheckoutAudit.kind: Literal["unavailable_before", "unavailable_after", "content_changed", "removed"]`、`CheckoutAudit.protected: bool = True`
  - `BatchResult.unprotected_changes: list[str] = Field(default_factory=list[str])`
  - `CheckoutSnapshot(common_dir: Path | None = None)`、属性 `protected: set[str]`・`common_dir: Path | None`
  - `workspace.blocks_acceptance(finding: CheckoutAudit) -> bool`
  - `workspace._toplevel(repository: Path) -> str | None`、`workspace._registered(common_dir: Path) -> set[str] | None`

- [ ] **Step 1: 失敗するテストを書く**

`test_workspace.py` に次の 4 件を足す（`import shutil` は既存）。`repository` は既存の fixture、`create_worktree` は既存の import。

```python
# Other sessions change and clean up their own worktrees while a run is going (#756). Only the
# checkout given to the run and the main worktree may block it; a checkout that vanished while
# still registered stays unauditable.
@pytest.mark.parametrize(
    ("which", "mutation", "kind", "protected"),
    [
        ("target", "change", "content_changed", True),
        ("main", "change", "content_changed", True),
        ("other", "remove", "removed", False),
        ("other", "vanish", "unavailable_after", False),
    ],
)
def test_audit_protects_only_the_target_and_the_main_worktree(
    repository: Path, tmp_path: Path, which: str, mutation: str, kind: str, protected: bool
) -> None:
    target = create_worktree(repository, "HEAD", tmp_path / "対象 checkout\n改行")
    other = create_worktree(repository, "HEAD", tmp_path / "other session")
    before = snapshot_checkouts(target)
    checkout = {"target": target, "main": repository, "other": other}[which]
    if mutation == "change":
        (checkout / "tracked.txt").write_text("changed by another session\n")
    elif mutation == "remove":
        git(repository, "worktree", "remove", "--force", str(checkout))
    else:
        shutil.rmtree(checkout)
    [finding] = workspace.audit_checkouts(before)
    assert (finding.path, finding.kind, finding.protected) == (str(checkout), kind, protected)
    assert workspace.blocks_acceptance(finding) is (protected or kind == "unavailable_after")
```

- `test_target_given_through_a_symlink_is_protected(repository, tmp_path)`: `target = create_worktree(repository, "HEAD", tmp_path / "feature")`、`link = tmp_path / "link to feature"` を `link.symlink_to(target, target_is_directory=True)` で作り、`snapshot_checkouts(link)` の後に `target / "tracked.txt"` を書き換える。`[finding] = workspace.audit_checkouts(before)`、`(finding.path, finding.protected) == (str(target), True)`、`workspace.blocks_acceptance(finding)` が真
- `test_unidentified_target_protects_every_checkout(repository, tmp_path)`: `git(tmp_path, "clone", "-q", "--bare", str(repository), str(bare))`、`linked = create_worktree(bare, "HEAD", tmp_path / "linked")`、`snapshot_checkouts(bare)` の後に `linked / "tracked.txt"` を書き換える。`(finding.path, finding.kind, finding.protected) == (str(linked), "content_changed", True)`、`blocks_acceptance` が真
- `test_unlisted_registrations_keep_a_vanished_checkout_unauditable(repository, tmp_path, monkeypatch)`: `other = create_worktree(repository, "HEAD", tmp_path / "other session")`、`before = snapshot_checkouts(repository)`、`git(repository, "worktree", "remove", "--force", str(other))`。`original = workspace._git` を控え、引数の先頭 2 つが `("worktree", "list")` のときだけ `WorkspaceError()` を投げ、それ以外は `original` に渡す関数で `workspace._git` を差し替える。`(finding.path, finding.kind, finding.protected) == (str(other), "unavailable_after", False)`、`blocks_acceptance` が真

既存の `test_audit_diagnoses_unavailable_baseline` の期待値の dict に `"protected": False` を足し、その直後に `assert all(workspace.blocks_acceptance(item) for item in diagnostics)` を足す。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_workspace.py -q`
Expected: 新しい 4 件と `test_audit_diagnoses_unavailable_baseline` が FAIL（`blocks_acceptance` が無い／`protected` が無い）。ほかは PASS

- [ ] **Step 3: `models.py` を直す**

`CheckoutAudit` に `removed` と `protected: bool = True`、`BatchResult` に `unprotected_changes` を足す。docstring に Spec の「設計」の `models.py` の内容（古い記録の読み方、`outside_changes` との違い）を書く。`_legacy_unrelated_audit` は残す。

- [ ] **Step 4: `workspace.py` を直す**

Spec の「設計」の `workspace.py` のとおりにする。要点だけ:

- `snapshot_checkouts`: `records` を読んだ後に `result = CheckoutSnapshot(git_common_dir(repository))`、`target = _toplevel(repository)`。`enumerate(records)` の `index == 0`、`target is None`、`os.path.realpath(path) == target` のどれかなら `result.protected.add(path)`。失敗の `CheckoutAudit` に `protected=` を渡す
- `audit_checkouts`: 読めない観測は `unreadable` に集め、ループの後に `snapshot.common_dir` があれば `_registered` を 1 回呼ぶ。結果が `None` でなく、パスが含まれなければ `finding.kind = "removed"`。最後に `sorted(findings, key=lambda finding: finding.path)` を返す
- `require_auditable_checkouts` は変えない

- [ ] **Step 5: 成功を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_models.py -q`
Expected: すべて PASS

- [ ] **Step 6: Commit**

```bash
git add tools/agent_runner/models.py tools/agent_runner/workspace.py tools/agent_runner/tests/test_workspace.py
git commit -m "fix(agent-runner): protect only the given checkout and the main worktree in the audit (#350)"
```

### Task 2: runner の分割と監査の説明

テスト: 要（既存の S のテストの期待値を直す）。runner が分類を結果に正しく分けないと、利用側が誤って受け取る・拒否する。

**Files:**
- Modify: `tools/agent_runner/runner.py:467-474`（`BatchResult` の組み立て）、`runner.py:24-32`（import）
- Modify: `tools/agent_runner/tests/test_checkout_policy.py`（`test_batch_reports_parallel_checkout_edit`）
- Modify: `tools/agent_runner/interfaces.rst:183-184`・`:233-243`
- Modify: `tools/agent_runner/runtimes/cursor.rst:103`

**Interfaces:**
- Consumes: Task 1 の `blocks_acceptance`、`BatchResult.unprotected_changes`
- Produces: `BatchResult.outside_changes` は `blocks_acceptance` が真の観測のパス、`unprotected_changes` は偽の観測のパス

- [ ] **Step 1: 既存テストの期待値を直す**

`test_batch_reports_parallel_checkout_edit` の最後の 2 つの assert を次にする。

```python
    assert batch.outside_changes == []
    assert batch.unprotected_changes == [str(neighbor)]
    assert [(item.path, item.kind, item.protected) for item in batch.checkout_audit] == [
        (str(neighbor), "content_changed", False)
    ]
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_checkout_policy.py -q`
Expected: `test_batch_reports_parallel_checkout_edit` が FAIL（`outside_changes == [neighbor]`）

- [ ] **Step 3: `runner.py` を直す**

`before = require_auditable_checkouts(repository)` はそのまま（Spec の D1）。`BatchResult(...)` を `outside_changes=[f.path for f in checkout_audit if blocks_acceptance(f)]`、`unprotected_changes=[f.path for f in checkout_audit if not blocks_acceptance(f)]` にし、`blocks_acceptance` を import する。

- [ ] **Step 4: 成功を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/tests/test_models.py -q`
Expected: すべて PASS

- [ ] **Step 5: `interfaces.rst` を直す**

`BatchResult` の項目を `schema_version / run_id / state / assignments / results / outside_changes / unprotected_changes / checkout_audit / elapsed_seconds / artifact_dir。` にし、その下に「outside_changes・unprotected_changes・checkout_audit は下の「期限と保持」の監査の結果。」を足す。

「期限と保持」の 233〜243 行の段落（「監査は開始前から…」から「監査は他セッションの登録を自動で回収しない。」まで）を次にする。

```rst
監査は開始前から登録されていた checkout の HEAD・index・tracked ファイル・
非 ignored untracked ファイルの内容を比較する。initialized submodule も含む。
Gitignored 資源、symlink の参照先、Git 外の任意のディレクトリ、実行中に登録された
checkout（runner の試行を含む）は監査範囲外。
外部セッションによる変更と委譲先による変更の因果までは断定しない。

runner は、渡された repository の checkout（対象）と、その repository の main worktree
（``git worktree list`` の先頭）を保護する。repository に自身の checkout が無い
（bare repository など）ときは、登録されたすべての checkout を保護する。
checkout_audit は観測ごとに path / kind / reason / locked / prunable / protected を返す。
kind は次のどれか。

- unavailable_before: 開始前から監査できない
- unavailable_after: 終了後に読めず、登録は残っている（または登録を一覧できない）
- content_changed: 内容が変わった
- removed: 終了後に読めず、登録も無くなった（``git worktree remove`` などで回収された）

outside_changes は、保護する checkout の観測と、どの checkout でも監査できない登録
（unavailable_before・unavailable_after）のパス。unprotected_changes は、保護しない
checkout の content_changed と removed のパスで、多くはほかのセッションが自分の worktree を
変えた・回収したものである。どちらも警告として返し、runner の処理自体は止めない。
issue-to-pr・review-verify・review-fix-planning の受け取り入口は outside_changes があれば
拒否し、unprotected_changes は理由にしない。判定は ``workspace.blocks_acceptance`` の 1 か所にある。
protected の無い古い checkout_audit は保護として読み、unprotected_changes の無い古い結果は
空として読む（古い outside_changes は全件なので、読み直しても受け取りを止める側になる）。
main worktree も保護するので、実行中に親の checkout を動かすと（repo-cleanup-after-merge の
origin/main への追従など）content_changed として受け取りが止まる。実行中は親の checkout を動かさない。
起動前も共通の ``require_auditable_workflow`` と runner が全登録を確認し、
監査不能なら予約・外部担当の起動より前に止める。
消えた登録の所有者の照合・個別 repair / remove は、リポジトリルートの
``docs/agent-runner-checkout-recovery.md`` に記載する。
監査は他セッションの登録を自動で回収しない。
```

- [ ] **Step 6: `cursor.rst` の 1 文を直す**

103 行目を「ほかの checkout の変更は runner が事後に報告するだけで（対象と main worktree の変更と監査できない登録は ``outside_changes`` 、それ以外の checkout の内容の変化・登録ごとの回収は ``unprotected_changes`` ）、任意のパスへの書き込みは防がない。」にする。161・172 行付近の観測の記録は変えない（Spec の D7）。

- [ ] **Step 7: 文書の構造を確かめて Commit**

Run: `bash scripts/check-layout.sh`
Expected: 終了コード 0

```bash
git add tools/agent_runner/runner.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/interfaces.rst tools/agent_runner/runtimes/cursor.rst
git commit -m "fix(agent-runner): report other sessions' checkouts apart from outside_changes (#350)"
```

### Task 2A: 保護を依頼された checkout だけにする（Spec の R8）

テスト: 要（S）。依頼された checkout の変化・監査不能を受け取る損害と、ほかの checkout（main worktree を含む）のせいで起動・受け取りを止めて並列作業を妨げる損害を防ぐ。Task 1・2 の後、Task 3 の前に行う。

**Files:**
- Modify: `tools/agent_runner/workspace.py`（モジュールの docstring、`blocks_acceptance`、`snapshot_checkouts`、`require_auditable_checkouts`）
- Modify: `tools/agent_runner/models.py`（`CheckoutAudit.protected`・`BatchResult.outside_changes`・`unprotected_changes` の docstring だけ）
- Modify: `tools/agent_runner/checkout_policy.py`（モジュールと `require_auditable_workflow` の docstring だけ。コードは変えない）
- Modify: `tools/agent_runner/tests/test_workspace.py`、`tools/agent_runner/tests/test_checkout_policy.py`
- Modify: `tools/agent_runner/interfaces.rst`（Task 2 で書いた監査の段落）、`tools/agent_runner/runtimes/cursor.rst`（Task 2 で直した 1 文）

**Interfaces:**
- Consumes: Task 1 の `CheckoutSnapshot.protected`・`common_dir`、`audit_checkouts`、Task 2 の runner の分割（変えない）
- Produces:
  - `workspace.blocks_acceptance(finding: CheckoutAudit) -> bool` は `finding.protected` を返す
  - `snapshot_checkouts(repository)` の `protected` は、実パスが `_toplevel(repository)` と同じ登録だけ。`_toplevel` が `None`、またはどの登録とも一致しないときは全登録。保護集合を全レコードから先に決めてから指紋を取り、開始前の失敗の `CheckoutAudit.protected` が保護集合と一致するようにする
  - `require_auditable_checkouts(repository)` は、保護する checkout の指紋が `None` のときだけ `CheckoutAuditError` を投げる（findings は保護する checkout の失敗だけ）。保護しない checkout の失敗は snapshot に残して返す。`snapshot_checkouts` の `WorkspaceError` は今までどおり `CheckoutAuditError` にする

- [ ] **Step 1: テストを直す・足す・消す**

`test_workspace.py`:

- `test_audit_protects_only_the_target_and_the_main_worktree` を `test_audit_protects_only_the_target` に改名し、parametrize を次にする。最後の assert は `assert workspace.blocks_acceptance(finding) is protected`。上のコメントを「Only the checkout given to the run may block it; the main worktree and other sessions' checkouts are reported only, even when they vanish (Spec R8).」にする

```python
        ("target", "change", "content_changed", True),
        ("main", "change", "content_changed", False),
        ("other", "remove", "removed", False),
        ("other", "vanish", "unavailable_after", False),
```

- 足す: `test_unmatched_target_protects_every_checkout(repository, tmp_path, monkeypatch)`: `other = create_worktree(repository, "HEAD", tmp_path / "other session")`、`monkeypatch.setattr(workspace, "_toplevel", lambda _: str(tmp_path / "unregistered"))`、`before = snapshot_checkouts(other)`、`(other / "tracked.txt").write_text("changed\n")`、`[finding] = workspace.audit_checkouts(before)`、`(finding.path, finding.protected) == (str(other), True)`、`workspace.blocks_acceptance(finding)` が真
- 消す: `test_unlisted_registrations_keep_a_vanished_checkout_unauditable`（ほかの checkout の `removed` と `unavailable_after` はどちらも報告だけになり、受け取りの判定に関わらない）
- `test_audit_diagnoses_unavailable_baseline`: `diagnostics` の dump の期待値（`"protected": False` を含む）はそのまま。その後を次にする（`try`/`finally` の chmod の戻しは残す）

```python
        assert not any(workspace.blocks_acceptance(item) for item in diagnostics)
        snapshot = workspace.require_auditable_checkouts(repository)
        assert snapshot[str(external)] is None and snapshot.failures[str(external)] == diagnostics[0]
        with pytest.raises(workspace.CheckoutAuditError) as caught:
            workspace.require_auditable_checkouts(external)
        assert caught.value.findings and all(item.protected for item in caught.value.findings)
        assert "SECRET" not in str(caught.value) and "SECRET" not in repr(caught.value.findings)
        assert changed_checkouts(before) == [str(external)]
```

`test_checkout_policy.py`:

- モジュールの docstring を「The requested checkout shares one preflight and post-execution audit boundary; other registrations are reported only (Spec R8). Fake writes model another session's activity.」の趣旨に直す
- `test_unavailable_registration_blocks_work_without_launch_or_repair` を `test_unavailable_neighbor_is_reported_and_unavailable_target_blocks_launch` に改名し、次にする
  - `neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")`、`neighbor.rename(tmp_path / "moved")`
  - `snapshot = require_auditable_workflow(configuration(), "audit", repository, adapter_loader=no_launch)` が例外を投げず、`snapshot[str(neighbor)] is None`
  - `batch = run_workflow(configuration(), "audit", "respond", repository, output_dir=tmp_path / "run", adapter_loader=lambda _: FakeAdapter())` が `state == "success"`、`outside_changes == []`、`unprotected_changes == [str(neighbor)]`、`[(item.path, item.kind, item.protected) for item in batch.checkout_audit] == [(str(neighbor), "unavailable_before", False)]`
  - `pytest.raises(workspace.CheckoutAuditError)` で `require_auditable_workflow(configuration(), "audit", neighbor, adapter_loader=no_launch)`、`pytest.raises(RunnerError)` で `run_workflow(configuration(), "audit", "respond", neighbor, output_dir=tmp_path / "blocked", adapter_loader=no_launch)`、`not (tmp_path / "blocked").exists()`
  - 最後に `str(neighbor) in git(repository, "worktree", "list", "--porcelain")`（登録を repair・prune しない）

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_checkout_policy.py -q`
Expected: `test_audit_protects_only_the_target` の `main`・`vanish` の行、`test_unmatched_target_protects_every_checkout`、`test_audit_diagnoses_unavailable_baseline`、`test_unavailable_neighbor_is_reported_and_unavailable_target_blocks_launch` が FAIL。ほかは PASS

- [ ] **Step 3: `workspace.py`・`models.py`・`checkout_policy.py` を直す**

Produces のとおりにする。docstring は「保護するのは依頼された checkout だけ（特定できなければ全登録）。main worktree とほかの checkout の変化・回収・監査不能は報告だけ。`blocks_acceptance` は `protected`」の趣旨にする。`audit_checkouts`・`_registered`・`_toplevel` と runner は変えない。

- [ ] **Step 4: 成功を確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/tests/test_models.py -q`
Expected: すべて PASS

- [ ] **Step 5: `interfaces.rst` と `cursor.rst` を直す**

`interfaces.rst` の「期限と保持」の監査の段落（Task 2 で置いた「監査は開始前から…」から「監査は他セッションの登録を自動で回収しない。」まで）を次にする。`BatchResult` の項目と注記（Task 2）はそのまま。

```rst
監査は開始前から登録されていた checkout の HEAD・index・tracked ファイル・
非 ignored untracked ファイルの内容を比較する。initialized submodule も含む。
Gitignored 資源、symlink の参照先、Git 外の任意のディレクトリ、実行中に登録された
checkout（runner の試行を含む）は監査範囲外。
外部セッションによる変更と委譲先による変更の因果までは断定しない。

runner は、渡された repository の checkout（対象）だけを保護する。main worktree
（``git worktree list`` の先頭）も、対象でなければ保護しない。対象を特定できない
（bare repository、``--show-toplevel`` が取れない、どの登録とも実パスが一致しない）ときは、
登録されたすべての checkout を保護する。
checkout_audit は観測ごとに path / kind / reason / locked / prunable / protected を返す。
kind は次のどれか。

- unavailable_before: 開始前から監査できない
- unavailable_after: 終了後に読めず、登録は残っている（または登録を一覧できない）
- content_changed: 内容が変わった
- removed: 終了後に読めず、登録も無くなった（``git worktree remove`` などで回収された）

outside_changes は保護する checkout の観測のパス、unprotected_changes は保護しない
checkout の観測（内容の変化・回収・監査不能）のパスである。後者の多くは、ほかのセッションが
自分の worktree や親の checkout を変えた・回収したものである。どちらも警告として返し、
runner の処理自体は止めない。issue-to-pr・review-verify・review-fix-planning の受け取り入口は
outside_changes があれば拒否し、unprotected_changes は理由にしない。
判定は ``workspace.blocks_acceptance`` の 1 か所にある。
protected の無い古い checkout_audit は保護として読み、unprotected_changes の無い古い結果は
空として読む（古い outside_changes は全件なので、読み直しても受け取りを止める側になる）。
起動前は共通の ``require_auditable_workflow`` と runner が登録を確認し、保護する checkout を
監査できないとき、または登録を一覧できないときだけ、予約・外部担当の起動より前に止める。
保護しない checkout を監査できなくても起動し、unavailable_before として unprotected_changes に報告する。
消えた登録の所有者の照合・個別 repair / remove は、リポジトリルートの
``docs/agent-runner-checkout-recovery.md`` に記載する。
監査は他セッションの登録を自動で回収しない。
```

`cursor.rst` の Task 2 で直した 1 文を「ほかの checkout の変更は runner が事後に報告するだけで（対象の変更と監査不能は ``outside_changes`` 、main worktree を含むそれ以外の checkout の内容の変化・回収・監査不能は ``unprotected_changes`` ）、任意のパスへの書き込みは防がない。」にする。

- [ ] **Step 6: 文書の構造を確かめて Commit**

Run: `bash scripts/check-layout.sh`
Expected: 終了コード 0

```bash
git add tools/agent_runner/workspace.py tools/agent_runner/models.py tools/agent_runner/checkout_policy.py tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/interfaces.rst tools/agent_runner/runtimes/cursor.rst
git commit -m "fix(agent-runner): protect only the requested checkout and report the rest (#350)"
```

### Task 3: review-verify の dispatch

テスト: 要（S）。古い記録を保護しない側に読む損害と、修正の worktree を保護できない損害を防ぐ。通る例を 1 件置く。

**Files:**
- Modify: `.agents/skills/review-verify/scripts/dispatch.py`（import、新しい定数 `REPOSITORY_NOT_AT_TO`、`dispatch()` の 300〜307 行、`REQUEST_ERRORS`、`check_batch`、`main` の出力）
- Modify: `.agents/skills/review-verify/references/fix-check.md:9`・`:36`・`:56`
- Test: `.agents/skills/review-verify/tests/test_dispatch.py`

**Interfaces:**
- Consumes: Task 2A の `blocks_acceptance`（`finding.protected`）、Task 2 の `BatchResult.unprotected_changes`
- Produces: `dispatch` の出力の JSON 行に `unprotected_changes`。`REPOSITORY_NOT_AT_TO` は `"repository must be the checkout whose HEAD is to: the worktree holding the fixes, which is the only checkout the runner protects"`

- [ ] **Step 1: 失敗するテストを書く**

`test_dispatch.py` に 3 件を足し、`test_accept_does_not_attribute_a_disappeared_checkout_to_content_changes` と `test_fix_check_environment_preflight_does_not_launch` を消す（Spec の R8。ほかの checkout の消失・監査不能は報告だけになる。通る例は下の `another_sessions_worktree` が代表し、依頼された checkout の監査不能で起動しない守りは Task 2A の `test_checkout_policy.py` にある）。補助関数（`run_external`・`accept`・`written`・`main_argv`・`loader_for`・`PayloadAdapter`・`config`・`git`）は既存のものを使う。

- `test_accept_counts_an_old_record_without_protection_as_blocking(dispatch, scenario, tmp_path)`: `run_dir = run_external(dispatch, scenario, tmp_path, scenario.payload())`、`dispatch.json` の `batch.checkout_audit` を `[{"path": str(tmp_path / "other session"), "kind": "content_changed", "reason": "content_changed", "locked": False, "prunable": False}]` に書き換える。`accept(dispatch, run_dir) == 1`、`written(scenario.review_dir) == []`
- `test_another_sessions_worktree_does_not_block_accept(dispatch, scenario, tmp_path, capsys)`: `other = create_worktree(scenario.root, "HEAD", tmp_path / "other session")`。`PayloadAdapter` を継承し、`collect` で `(other / "tool.py").write_text("another session\n")` してから親の `collect` を返す adapter を使う。payload の `verified.skill` は `run_external` と同じく `dispatch.SKILL` の sha256 にする。`dispatch.main(main_argv(tmp_path, scenario.request, "probe"), adapter_loader=...)` が 0、出力の `outside_changes == []`、`unprotected_changes == [str(other)]`、`accept(dispatch, tmp_path / "main-run") == 0`
- `test_repository_whose_head_is_not_to_is_refused(dispatch, scenario, tmp_path, capsys)`: `base_checkout = create_worktree(scenario.root, scenario.base, tmp_path / "base checkout")`、`request = {**scenario.request, "repository": str(base_checkout)}`。`pytest.raises(ValueError, match="HEAD is to")` で `dispatch.dispatch(config("probe"), request, tmp_path / "refused", adapter_loader=loader)`、`not (tmp_path / "refused").exists()`。`dispatch.main(main_argv(tmp_path, request, "probe"), adapter_loader=loader) == 2`、stderr に `HEAD is to`、`not (tmp_path / "main-run").exists()`

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/skills/review-verify/tests/test_dispatch.py -q -k "old_record_without_protection or another_sessions_worktree or head_is_not_to"`
Expected: `another_sessions_worktree` と `head_is_not_to` が FAIL。`old_record_without_protection` は今の実装（`if diagnostics` で全部を拒否する）でも PASS する。このテストは、通る例の `another_sessions_worktree` と組にして、全部を拒否する実装を除く

- [ ] **Step 3: `dispatch.py` を直す**

Spec の「設計」の `dispatch.py` のとおり（`check_batch` の監査不能の検査も `blocks_acceptance` が真の観測だけにする。R8）。`head` の取得は `from`/`to` の解決と同じ `try` の中に置き、`WorkspaceError` は今の `"repository/from/to cannot be resolved"` のままにする。`check_batch` の docstring に「保護しない checkout の内容の変化・登録ごとの回収は理由にしない。判定は runner と同じ `blocks_acceptance`」を書く。

- [ ] **Step 4: 成功を確かめる**

Run: `uv run pytest .agents/skills/review-verify/tests/test_dispatch.py -q`
Expected: すべて PASS

- [ ] **Step 5: `references/fix-check.md` を直す**

- 9 行目の `repository` の行: 「`to` を HEAD に持つ checkout（修正を commit した worktree）の絶対パス。from も読める同じ repository のもの。HEAD が `to` でなければ dispatch は起動の前に終了コード 2 で止まる。runner が保護するのはこの checkout だけ（main worktree を含むほかの checkout の変化・回収・監査不能は `unprotected_changes` に報告するだけ）」
- 36 行目の出力の項目に `unprotected_changes` を足し、「`outside_changes` は runner が保護する checkout（request の `repository` の checkout）の変化・削除・監査不能。`unprotected_changes` はそれ以外の checkout（main worktree を含む）の内容の変化・登録ごとの回収・監査不能（多くはほかのセッションの worktree や親の checkout）で、終了コードにも受け取りにも影響しない（`tools/agent_runner/interfaces.rst`）」を足す
- 56 行目の「開始前から登録されていた checkout に変更がある（`outside_changes`）」を「runner が保護する checkout が変わった・消えた・監査できない（`outside_changes`・`checkout_audit` の `protected` な観測。`unprotected_changes` は理由にしない）」にする

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/review-verify/scripts/dispatch.py .agents/skills/review-verify/references/fix-check.md .agents/skills/review-verify/tests/test_dispatch.py
git commit -m "fix(review-verify): accept fix-checks despite other sessions' worktrees and require the fix worktree (#350)"
```

### Task 4: review-fix-planning の run_roles

テスト: 要（S）。修正の worktree を保護できない損害と、拒否しても self-review の 1 回枠を消費する損害を防ぐ。通る例を同じテストに置く。

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/run_roles.py:313-319`（HEAD の検査）、`:498-504`（出力）
- Modify: `.agents/skills/review-fix-planning/references/execution.md:25`・`:65`（`repository` の行）
- Test: `.agents/skills/review-fix-planning/tests/test_run_roles.py`

**Interfaces:**
- Consumes: Task 2 の `BatchResult.unprotected_changes`
- Produces: `run_roles` の出力の JSON に `unprotected_changes`。HEAD の誤りは `RoleInputError("repository must be the checkout whose HEAD is revision: the worktree holding the fixes, which is the only checkout the runner protects")`

- [ ] **Step 1: 失敗するテストを書く**

`test_run_roles.py` に補助関数 `fix_worktree(inputs, tmp_path) -> Path` を足す: request の `repository` を `git checkout -q --detach <source_head>` で source_head に戻し、`git worktree add -q --detach <tmp_path / "修正の worktree"> <revision>` で修正の worktree を作って返す。

`test_repository_whose_head_is_not_revision_is_refused(inputs, tmp_path)`（self-review だけ）:

- `request, planning, fix_input = inputs`、`worktree = fix_worktree(inputs, tmp_path)`
- `pytest.raises(mod.RoleInputError, match="HEAD is revision")` で `mod.run(config(), "self-review", request, tmp_path / "refused", planning_file=planning, fix_input=fix_input)`
- `not (tmp_path / "refused").exists()`、`json.loads(planning.read_text())["activities"] == []`
- `request["repository"] = fix_input["repository"] = str(worktree)` にして同じ呼び出し（出力先 `tmp_path / "run"`、`adapter_loader=FakeAdapter()`）が `batch.state == "self"` を返す

`config()` は全担当が `self` なので、`parent` fixture は要らない（既存の `test_second_review_is_refused_even_when_all_assignments_are_self` と同じ）。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q -k head_is_not_revision`
Expected: FAIL（`RoleInputError` が出ない）

- [ ] **Step 3: `run_roles.py` を直す**

Spec の「設計」の `run_roles.py` のとおり。`head = resolve_revision(repository)` を既存の `try` の中に置き、`except WorkspaceError` の後、`output_dir` の検査の前で比べる。出力に `"unprotected_changes": batch.unprotected_changes` を足す。終了コードの判定（`not batch.outside_changes`）は変えない。

- [ ] **Step 4: 成功を確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q`
Expected: すべて PASS

- [ ] **Step 5: `execution.md` を直す**

25 行目と 65 行目の `repository` の値に「（HEAD が `revision` と同じ checkout。違えば `run_roles` は起動・予約の前に終了コード 2 で止まる。runner が保護するのはこの checkout だけで、ほかの checkout（親の main worktree を含む）の変化・回収・監査不能は `unprotected_changes` に報告するだけ）」を足す。`run_roles` の出力の項目を挙げる文があれば `unprotected_changes` を足し、「ほかの checkout の変化・回収（`unprotected_changes`）は終了コードに影響しない」を書く。

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/review-fix-planning/scripts/run_roles.py .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-fix-planning/tests/test_run_roles.py
git commit -m "fix(review-fix-planning): require the fix worktree as the role repository and report unprotected changes (#350)"
```

### Task 5: pr-review-fix-loop の記録

テスト: 不要（Spec の D11）。`_review_batch` は BatchResult 全体を `review-result.json`（`result_file`）に保存するので、`BatchInfo` に項目が無くても記録は消えない。項目の有無だけを見るテストは S に当たらない。代わりに既存テストの回帰と、一時的な確認（コミットしない）で確かめる。

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py:318-323`（`BatchInfo`）、`:2136-2142`（`_review_batch`）、`:2215-2224`（`review` の出力）

**Interfaces:**
- Consumes: Task 2 の `BatchResult.unprotected_changes`
- Produces: `BatchInfo.unprotected_changes: list[str] = Field(default_factory=list[str])`、`review` の出力の `unprotected_changes`

- [ ] **Step 1: `loop.py` を直す**

`BatchInfo` に `unprotected_changes` を足し（コメント「runner が保護しない checkout の変化・回収。警告だけ。古い記録は空」）、`_review_batch` と `review` の出力に `batch.unprotected_changes` を入れる。Herdr 節・reconcile・診断は触らない。

- [ ] **Step 2: 既存テストの回帰を確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_review.py .agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py -q`
Expected: すべて PASS

- [ ] **Step 3: 一時的な確認**

AW の `test_review_reports_other_sessions_worktrees_apart_from_outside_changes`（`/tmp/agent-ws-cmp.*/agent-workspace` が無ければ、`env.parent` に linked worktree を足し、偽のレビュアーの `collect` の前にそれを書き換える adapter で `loop.review` を呼ぶ形）と同じ確認を、`PARENT_ROOT/tmp/agents/` のセッションディレクトリに置いた一時的なテストファイルで実行する。期待: `reviewed["outside_changes"] == []`、`reviewed["unprotected_changes"] == [str(other)]`、`cycle-1.json` の `review.batch.unprotected_changes == [str(other)]`。確認後にそのファイルを消す（worktree の中に置かない）

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/pr-review-fix-loop/scripts/loop.py
git commit -m "fix(pr-review-fix-loop): record other sessions' checkouts apart from outside_changes (#350)"
```

### Task 6: 範囲外の食い違う文（coordinator の承認があるときだけ）

テスト: 不要（文書の文言は F）。代わりに `git diff` で変えた文だけであることを確かめる。

R8 の後に行う場合は、下の文面の「対象と main worktree」を「対象（依頼された checkout）」に、「監査できない登録」を「対象の監査不能」に読み替える。

**前提:** #349 の実行マップで該当ファイルが #350 の所有に移っている、または #349 の所有の移動の提案（planning のセッションが投稿したコメント）に coordinator（利用者、または利用者が指名したセッション）の承認がある。実装担当は返事を待たない。どちらも無ければこの Task は行わず、PR の本文の「残る食い違い」に下の 4 か所を書き、#349 に「承認が無いので #350 では直さなかった」とコメントする。一部だけ承認されたときは、承認されたファイルだけを直す。

**Files（承認されたものだけ）:**
- `.agents/monitoring-runtimes.md:69`: 「既存の checkout の外部の変更のうち、runner が保護する checkout（対象と main worktree）の変化と監査できない登録は `outside_changes`、それ以外の checkout の変化・回収は `unprotected_changes` として報告されるが、どちらも他のセッションの変更との因果は断定しない。」
- `.agents/skills/pr-review-fix-loop/references/records.md:84`（`review.batch` の行）: `outside_changes` の後に「（runner が保護する checkout の変化と監査できない登録）・`unprotected_changes`（ほかの checkout の変化・回収。多くはほかのセッションの worktree。古い記録には無い）」
- `.devcontainer/README.md:927` 付近: 「runner が `outside_changes` として事後に報告する」を「runner が事後に報告する（依頼の `repository` の checkout と main worktree の変更、監査できない登録は `outside_changes`、それ以外の checkout の内容の変化・登録ごとの回収は `unprotected_changes`）」にする
- `docs/agent-runner-checkout-recovery.md:3`: 「隔離を保証できない担当では…停止しているときに行う。隔離した担当で…にある。」を「runner は依頼された checkout と main worktree を保護し、その変化と監査できない登録で成果の受け取りを止める。ほかの checkout の内容の変化と登録ごとの回収は `unprotected_changes` として報告するだけで、受け取りを止めない（[共通インターフェース](../tools/agent_runner/interfaces.rst)）。書き込みを伴う依頼で、ほかのセッションの worktree への書き込みも防ぎたいときは、そのリポジトリのほかのセッションが停止しているときに行う。」にする

- [ ] **Step 1: 前提を確かめる**（#349 の本文と全コメントを `gh api --paginate` で読む）
- [ ] **Step 2: 承認された文だけを直す**
- [ ] **Step 3: `git diff --stat` と `git diff` で、変えたのが上の文だけであることを確かめる。`bash scripts/check-layout.sh` が終了コード 0**
- [ ] **Step 4: Commit**（承認されたファイルだけを `git add` する。メッセージ `docs: describe unprotected_changes where outside_changes was documented (#350)`）

---

## 統合確認・公開（controller）

1. 回帰の確認（同時に走らせない。#349 の「同時に実行しない検証資源」）:
   - `uv run pytest tools/agent_runner/tests/test_workspace.py tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_checkout_policy.py tools/agent_runner/tests/test_models.py`
   - `uv run pytest .agents/skills/review-verify/tests/test_dispatch.py .agents/skills/review-fix-planning/tests/test_run_roles.py .agents/skills/pr-review-fix-loop/tests/test_loop_review.py .agents/skills/issue-to-pr/tests/test_implement_task_run.py`
   - `uv run pytest tools .agents/skills/pr-review/tests`（adapter・version 8・`review_dir`・#212 の診断・merged の 3 値・`--spec-commit` の退行確認）
   - `bash scripts/check-layout.sh`
   - 期待: すべて終了コード 0
2. 一時的な確認（コミットしない。scratchpad か `tmp/agents/` のセッションディレクトリに置く）:
   - 変更前の形の `dispatch.json`（`batch` に `unprotected_changes` が無い）を accept して、`KeyError` のトレースバックにならず、通常の判定（0 か 1）で終わること
   - 手動: `T="$(mktemp -d)"` の中に一時的な Git と linked worktree を 2 つ作り、一方を `run_workflow` の `repository`、他方を偽の adapter の `collect` で変える。`outside_changes == []`、`unprotected_changes == [<他方>]` を確かめ、`rm -rf -- "${T:?}"` で片付ける
3. `git diff 690001b6 HEAD --stat` で、所有ファイル（Task 6 は承認分だけ）以外を変えていないことを確かめる
4. Spec・Plan の状態は `draft` のまま（内容の承認を得たら別に記録する）。完了記録に、実行した検証のコマンド・終了コード・時間を書く
5. 公開は実行タスクの指示に従う。PR を作るときは base `main`、本文は `Refs #350`（`Closes` を使わない。説明の文にも `Closes #350` を書かない）、Task 6 を行わなかったときは「残る食い違い」を書く。push の前に `bash scripts/scan-before-push.sh` を通す

## 実行方式

実行タスクが決める。推奨は superpowers:subagent-driven-development（Task 1〜2 の API を Task 3〜5 が使い、受け取りの判定を誤ると気付けない損害になるので、Task ごとに独立したレビューを挟む）。issue-to-pr で実行する場合は、そのスキルの手順に従う。

issue-to-pr の run（2026-11-08T16:24Z〜）では、`implement_task.py check` が `self: false` を返したので、subagent-driven-development の形で、Task 1〜5 を 1 つずつ順に `implement_task.py run` で runner の担当 `claude-code_sonnet_default` に依頼する（並行しない）。依頼ごとの `RUN_DIR` は `implement_task.py` 用のセッションディレクトリの下に作り、ledger は `tmp/agents/issue-350.7f5d70sx/sdd/2026-11-09-issue-350-checkout-audit/progress.md` に置く。Task のレビューはこのセッションのサブエージェント（Agent ツール）が、Task の brief と同じ受け入れ基準を受け取って行う。指摘の修正も同じ担当に新しい依頼として出す。最後にブランチ全体のレビューを 1 回行う。Task 6 は行わない（Spec の R4）。

2026-11-08T17:16Z に Task 3 の依頼が `failed`（`response_failed`）で止まった後、利用者の指示で設計を変え（Spec の R8）、run を再開した（R9）。Task 2A を Task 3 の前に足し、Task 3 は同じ担当に依頼し直す。依頼には「バックグラウンドのコマンドを使わない（同期で実行し、最後の応答を結果の JSON にする）」を足す。

## 実行予算

- 全体の能動時間: 390 分。根拠: 実装の 150 分（Task 5 件、移植元のコードとテストがあり、AW #756 の 4 commit の差分は約 500 行）に、`--merge` のループの 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 30 分））と予備 15 分を足した
- phase の目安: 準備 15 分、Task 1〜2 で 45 分、Task 2A で 20 分（R8 で追加。予算の範囲で吸収する）、Task 3〜5 で 50 分、統合確認 25 分、PR 15 分、ループ 225 分（1 サイクルで修正不要なら 75 分）
- worker: 各 Task の runner の担当は `implement` の役割の期限 90 分（runner が強制する）、予約枠 1。統合確認の `uv run pytest tools .agents/skills/pr-review/tests` は絶対期限 20 分
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。安全の失敗（所有ファイル以外の編集、実リポジトリ・実 HOME への書き込み、有料の runner の起動）は再試行せず全体停止
- checkpoint: Task 2 の後（API の確定）、予算の 50%（75 分）と 100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補:
  - 縮小: Task 6 を行わず、PR の本文に残る食い違いとして書く
  - 切り出し: Task 5（ループの記録）を後続の `loop-reconcile`（#356）に回す提案を #349 にコメントする（利用者の許可が要る）
  - 方法変更: subagent-driven-development の worker が同じ失敗を繰り返したら、controller が executing-plans で直接行う。ただし issue-to-pr の run で runner の担当に依頼しているときは、失敗を理由にこのセッションが実装を引き取らない（issue-to-pr の 4 章）。止まって報告し、担当を変えるかは利用者が決める

## contingency（代替策）

- 最初の RED で前提が違うと分かったとき（例: CRW の `git worktree list` が symlink のパスをそのまま登録する、`_git` の差し替えが `git_common_dir` にも当たる）は、Spec の意味（保護する checkout の判定、一覧の失敗で止める）を保つ最小の修正をして、ledger に記録して続ける。意味が変わる場合は利用者の裁定を待つ
- 既存テストが Task 1〜2 の後に失敗したとき（ほかの checkout の変化を `outside_changes` に期待するもの）: 期待が「保護しない checkout の変化で止める」なら Spec の決定に沿って期待値を直し、ledger に記録する。所有ファイル以外のテスト（例 `issue-to-pr/tests/test_implement_task_run.py`）なら直さずに止め、#349 に所有の移動を提案する
- `origin/main` が進み、所有ファイルに別の変更が入っていたとき: rebase してから Plan の行番号を読み替える。設計の前提（preflight・`checkout_policy`）が変わっていたら止めて報告する
- Task 6 の承認が得られないとき: 縮小の候補のとおり、PR の本文に残す
- 既存の停止条件・安全の境界（preflight、`dsh_removed`、実 API を使わない）は、どの代替策でも変えない

## 完了記録

（実行タスクが、実行した検証の結果・時間・公開の状態を書く）
