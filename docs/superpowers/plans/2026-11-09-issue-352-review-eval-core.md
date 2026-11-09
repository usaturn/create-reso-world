# Issue #352 review-eval の基盤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の承認は記録していない。実行許可は Spec の「管理・実行許可」のとおり）

**Goal:** AW `0eea76aa` の `tools/review_eval` を CRW に移し、既定で無効の収集の土台（設定・store・capture・inventory・ledger・packets・CLI・docs）を作る。

**Architecture:** AW のモジュールを基準にし、AW 固有の 5 か所（`projects.toml` の照合、設定パス、hook の起動、旧配置、テスト補助）だけを変える。4 経路の helper には接続しない（#357）。

**Tech Stack:** Python 3.14、pydantic 2、pytest（root の `pyproject.toml`・`uv.lock`）、gitleaks（既定の scanner。テストでは偽の scanner）

**Spec:** `docs/superpowers/specs/2026-11-09-issue-352-review-eval-core-design.md`

## Global Constraints

- 変更してよいのは `tools/review_eval/**`（新規）と `README.md` の「構成」の `tools/` の行だけ。`pyproject.toml`・`.gitignore`・`tools/test_support/`・4 経路の helper は変えない
- 移植元は AW `0eea76aa`。このホストでは `/workspaces/reso-world/tmp/agents/issue-352.83snyw06/aw-src/` に取得済み（`tools/review_eval/**`・`tools/test_support/review_eval.py`・`review_eval_ledger.py`・`plugin.py`。tree の blob SHA と一致を確認済み）。以下 `AW=/workspaces/reso-world/tmp/agents/issue-352.83snyw06/aw-src/tools`
- 「AW のまま」と書いたファイルは `cp` で写し、内容を変えない（`cmp` で一致すること）
- 設定パスは `REVIEW_EVAL_CONFIG`（空文字は明示の無効）、未設定は `$XDG_CONFIG_HOME/create-reso-world/review-eval.toml`（XDG が絶対パスのときだけ）、それ以外は `$HOME/.config/create-reso-world/review-eval.toml`
- 旧配置は `reviews/#<N>-*` と `reviews/old/#<N>-*`。`external/*/reviews` は範囲外（`out_of_scope` の `outside_reviews`）
- テストは fake の記録・fake の Git・fake の scanner だけを使う。実 PR・実データ・実 store・実 `~/.config`・ネットワーク・実 gitleaks を使わない
- テストの実行は `uv run --locked pytest <パス>`（feature worktree の root で）。Python は uv で実行し、`python3` を直接使わない
- テストは AGENTS.md の「テストの採用基準」の S だけ。各 Task のテストの要否と理由は Task に書く

## Review Focus

- 設定ファイルが TOML として壊れている: `collect` は `failed`（`config: 設定ファイルを TOML として読めない`）を返し、store に何も書かない。`status`・`config check` は終了コード 2（Task 6 の手動の確認）
- `store` が `workspace_root/reviews` の中: 設定の誤りで収集しない（Task 1 の `test_store_inside_reviews_is_rejected`）
- `REVIEW_EVAL_CONFIG=""` と相対の `XDG_CONFIG_HOME`: 前者は無効、後者は無視して `$HOME/.config` を使う（Task 1 の `test_config_path_honours_explicit_disable_and_ignores_relative_xdg`）
- `reviews/old/<repo>/#<N>-*`（3 階層）: owner `old` の新配置として扱い、旧配置と混同しない（Task 2 の `test_legacy_and_external_review_dirs_are_not_captured` の正しく通る例）
- review_dir を相対パスや末尾の `/` 付きで渡す: `os.path.normpath` で同じ場所として扱う（AW のまま。Task 6 の手動の確認）

---

## 受け入れ基準

### 動作環境

- Dev Container（Ubuntu 26.04、CPython 3.14.4、uv）。feature worktree `/workspaces/reso-world/.worktrees/issue-352-review-eval-core`、または runner の担当の worktree。`AGENT_RUNNER_DEPTH=1` の中でもテストが通る（`outside_runner` fixture）
- `REVIEW_EVAL_CONFIG` は `tools/review_eval/tests/conftest.py` が各テストの前に空文字にする。収集を有効にするテストだけが `monkeypatch.setenv` で `tmp_path` の設定に向ける

### 実入力

- review_dir: `<tmp>/workspace/reviews/usaturn/alpha/#5-feat/`（新配置）、`<tmp>/workspace/reviews/old/#5-feat/`・`<tmp>/workspace/reviews/#3-old/`（旧配置）、`<tmp>/workspace/external/alpha/reviews/#5-feat/`（範囲外）
- 記録: 日本語と複数行を含む Markdown（`# レビュー\n\n## Medium\n\n### M-1 指摘\n\n<本文>\n`）、`review-findings/v2` の candidates の JSON（`pr.repository`・`pr.number`・40 桁の `reviewed_head`）、`pr-review-fix-loop/v1` の cycle の JSON、`@pr-comment/round-1/record.json` の仮想記録
- 秘密: 実行時に組み立てた `ghp_` + 36 文字の英数字（ファイルに書かない）

### 防御範囲

- 対象: `sources` に書いた repo（未登録でもよい）の `reviews/<owner>/<repo>/#<N>-<branch>/` の許可パターン、`enabled = true`・承認の記録・`store init` が揃ったとき
- 対象外（何も書かない）: 設定ファイルが無い、`enabled = false`、`REVIEW_EVAL_CONFIG=""`、runner の子、`sources` に無い repo、旧配置（failure 1 件だけ）、`external/*/reviews`、symlink、`max_artifact_bytes`・`max_store_bytes` の超過（failure だけ）、秘密の検出（本文なしの observation と failure だけ）、文書の `pr` と場所の食い違い（failure だけ）
- 設定の誤り（収集しない）: `enabled = true` で `approved_by`・`approved_on`・`sources` のどれかが無い、`store` が `workspace_root/reviews` の中、`repo` が `<owner>/<repo>` の形でない、`since > until`

## 要件と Task の対応

| Spec の条件 | Task | 確かめ方 |
| --- | --- | --- |
| 設定が無い・`enabled = false` で何も書かない | 2 | `test_collect_writes_nothing_unless_enabled` |
| 承認・sources の欠落は設定エラーで収集しない | 2 | `test_enabled_config_without_approval_or_sources_collects_nothing` |
| store 未初期化で収集しない、store を作らない | 2 | `test_collect_failure_is_reported_without_raising`（AW＋store を作らない確認） |
| store 0700・0600、上書きしない | 1 | `test_store_is_private_and_files_are_owner_only`、`test_existing_blob_with_wrong_bytes_is_not_overwritten` |
| 上限の超過で保存せず理由を残す | 2 | `test_capacity_limit_holds_without_deleting`、`test_artifact_over_limit_is_not_stored_and_reason_is_recorded` |
| 秘密の検出で保存せず、値を出さない | 2 | `test_secret_body_is_withheld_and_never_printed`（偽の scanner） |
| sources は明示の許可リスト、未登録 repo も対象 | 2 | `test_sources_allowlist_decides_scope_without_registration` |
| `reviews/old`・`external/*/reviews` の扱い | 2・4 | `test_legacy_and_external_review_dirs_are_not_captured`、`test_reconcile_counts_legacy_layouts_without_reading_them` |
| inventory・reconcile・ledger・packets が fake だけで動く | 3・4 | test_ledger・test_packets・test_reconcile |
| `status`・`config check` の設定なしの挙動 | 6 | 手動（L のためテストにしない） |
| 既定の gitleaks の argv | 6 | 手動（実 gitleaks。コミットしない） |
| 退行なし | 6 | `uv run --locked pytest tools`、`bash scripts/check-layout.sh` |

共有する条件: 旧配置の規則（Task 2 の `LEGACY_PARENT`・`is_legacy` と、Task 4 の `_legacy_dirs`）、設定パスと明示の無効（Task 1 の `shim.config_path`・`conftest.py` と、Task 4 の CLI）、`sources` の許可リスト（Task 1 の検証と Task 2 の `source_for`）。統合担当は Task 6（controller）で、Task 6 の 1・3 と各 Task のレビューで、同じ規則を使っていることを確かめる。

---

### Task 1: 基盤モジュール・設定・store

**Files:**
- Create（AW のまま `cp`）: `tools/review_eval/__init__.py`・`canonical.py`・`models.py`・`formats.py`・`scanner.py`・`store.py`
- Create（AW を写して変更）: `tools/review_eval/config.py`・`tools/review_eval/shim.py`
- Create: `tools/review_eval/tests/conftest.py`・`tools/review_eval/tests/support.py`・`tools/review_eval/tests/test_store.py`・`tools/review_eval/tests/test_config.py`

**Interfaces:**
- Produces: `config.Config`・`Source`・`Route`・`ROUTES`・`ConfigError`・`load_config(path) -> Config`・`load_active(environ=None) -> Config | None`（`check_registered` は無い）。`shim.config_path(environ=None) -> Path | None`・`enabled_flag(path) -> bool | None`・`enabled_config(environ=None)`・`in_runner_child(environ=None) -> bool`・`run_hook(*, tool_root, route, event, review_dir=None, files=(), records=(), repository=None, pr=None, context=None, timeout=120.0, environ=None) -> None`。`store.Store`・`StoreError`（AW のまま）
- Produces（テスト補助 `tools/review_eval/tests/support.py`）: `FAKE_SCANNER: list[str]`・`FLAGGING_SCANNER: list[str]`・`write_collection_config(path, *, store, workspace_root, repos, routes=ROUTES, scanner=FAKE_SCANNER, max_store_bytes=64 * 1024 * 1024, **overrides) -> Path`・`make_observation(sha256, size, *, repository="o/r", pr=1, review_dir="#1-b", path="model.md", observed_at="2026-10-30T00:00:00Z") -> Observation`・`put_revisions_worker(store_root: str, revisions) -> list[bool]`・`append_times_worker(store_root: str, who: str, count: int) -> list[int]`

テストの要否: 要。store の権限（秘密の漏れ）・上書きしないこと・並行の put（競合）・全 revision の復元（記録の消失）・`store` を `reviews` の中に置かないこと（後片付けでの消失）・設定パスの明示の無効と相対 XDG（環境の隔離）は、壊れてもエラーにならない S である。

- [ ] **Step 1: AW のままのファイルを写す**

```bash
AW=/workspaces/reso-world/tmp/agents/issue-352.83snyw06/aw-src/tools
mkdir -p tools/review_eval/tests
for f in __init__.py canonical.py models.py formats.py scanner.py store.py config.py shim.py; do cp "$AW/review_eval/$f" "tools/review_eval/$f"; done
```

- [ ] **Step 2: `config.py` を CRW に合わせる**

  1. `from tools.workspace import WorkspaceError, load_registry` の行を消し、`import re` を `import os` の次に足す
  2. `ROUTES` の定義の後に足す:

     ```python
     # sources の repo の形（capture の review_dir の owner・repo と同じ規則）。`.` 始まりの repo は reconcile が走査しないので置けない
     _OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
     _REPO = re.compile(r"[A-Za-z0-9._-]+")
     ```

  3. `Source._unique_routes` を次の `_validate` に置き換える（メッセージに値を含めない）:

     ```python
     @model_validator(mode="after")
     def _validate(self) -> Self:
         owner, separator, name = self.repo.partition("/")
         if not separator or not _OWNER.fullmatch(owner) or not _REPO.fullmatch(name) or name.startswith("."):
             raise ValueError("repo は <owner>/<repo> の形にする")
         if len(set(self.routes)) != len(self.routes):
             raise ValueError("routes が重複している")
         if self.since is not None and self.until is not None and self.since > self.until:
             raise ValueError("since が until より後になっている")
         return self
     ```

  4. `check_registered` 関数を消す。`load_active` の `check_registered(config)` の行を消す（`enabled` でなければ None、そうでなければ config を返す）。`load_active` の docstring は「有効な設定だけを返す。ファイルが無い・無効なら None。有効なのに誤りがあれば ConfigError。sources は明示の許可リストで、登録（projects.toml など）は照合しない。」にする

- [ ] **Step 3: `shim.py` を CRW に合わせる**

  1. `config_path` の既定を次にする（`explicit` の扱いは AW のまま）:

     ```python
     xdg = env.get("XDG_CONFIG_HOME", "")
     base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path(env.get("HOME") or str(Path.home())) / ".config"
     return base / "create-reso-world" / "review-eval.toml"
     ```

  2. `run_hook` の argv の `str(tool_root / "tools/devenv")` を `str(tool_root)` にする
  3. `run_hook` の docstring の 1 行目の後に「`tool_root` は create-reso-world の親 checkout の root で、root の pyproject.toml・uv.lock を使う（`uv run --project <tool_root> --locked`）。」を足す

- [ ] **Step 4: テストの隔離と補助を書く**

`tools/review_eval/tests/conftest.py`:

```python
"""review_eval のテストの隔離: 利用者の設定（~/.config の review-eval.toml）を読ませない。

各テストの前に REVIEW_EVAL_CONFIG を空文字（明示的に無効）にする。収集を有効にして確かめるテストは、
テストの中で monkeypatch.setenv で tmp_path の設定に上書きする。このディレクトリのテストだけに効く。
"""

import pytest


@pytest.fixture(autouse=True)
def _no_user_review_eval_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
```

`tools/review_eval/tests/support.py`: `$AW/test_support/review_eval.py` を写し、次を変える。

  1. docstring を「review-eval のテスト補助: 一時の設定・observation の作成と、spawn 用の worker。」にする
  2. `import subprocess` と `from tools.test_support.registry import write_registry` と `write_projects_toml` 関数を消す
  3. `FAKE_SCANNER` の後に足す（gitleaks の JSON レポートの形で、内容に `ghp_` を含むファイルを報告する偽の scanner。`python -c` の `sys.argv[1]` が source、`[2]` が report）:

     ```python
     _FLAGGING_CODE = (
         "import json, pathlib, sys\n"
         "source, report = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])\n"
         "found = [{'File': str(p)} for p in sorted(source.iterdir()) if b'ghp_' in p.read_bytes()]\n"
         "report.write_text(json.dumps(found))\n"
         "raise SystemExit(99 if found else 0)\n"
     )
     FLAGGING_SCANNER: list[str] = [sys.executable, "-c", _FLAGGING_CODE, "{source}", "{report}"]
     ```

  4. `put_revisions_worker`・`append_times_worker` は AW のまま（`append_times_worker` の `tools.review_eval.ledger` は関数の中の import のままにする。Task 3 で作る）

- [ ] **Step 5: テストを書く**

`tools/review_eval/tests/test_store.py`: `$AW/review_eval/tests/test_store.py` を写し、`from tools.test_support.review_eval import ...` を `from tools.review_eval.tests.support import make_observation, put_revisions_worker` にする。`import stat` を足し、次のテストを足す。

```python
def test_store_is_private_and_files_are_owner_only(tmp_path: Path) -> None:
    store = Store.init(tmp_path / "store")
    data = REVISIONS[0]
    sha = store.put_blob(data)
    assert store.put_observation(make_observation(sha, len(data)))

    paths = [store.root, *store.root.rglob("*")]
    assert any(path.is_file() for path in paths)
    for path in paths:
        mode = stat.S_IMODE(path.lstat().st_mode)
        assert mode == (0o700 if path.is_dir() else 0o600), (path, oct(mode))
```

`tools/review_eval/tests/test_config.py`:

```python
"""設定の読み込み: 明示の無効・相対の XDG と、store を reviews の中に置かないこと。"""

from pathlib import Path

import pytest

from tools.review_eval import shim
from tools.review_eval.config import ConfigError, load_config
from tools.review_eval.tests.support import write_collection_config


def test_config_path_honours_explicit_disable_and_ignores_relative_xdg(tmp_path: Path) -> None:
    home = str(tmp_path / "home")
    assert shim.config_path({"REVIEW_EVAL_CONFIG": "", "HOME": home}) is None
    assert shim.config_path({"XDG_CONFIG_HOME": "relative", "HOME": home}) == (
        tmp_path / "home" / ".config" / "create-reso-world" / "review-eval.toml"
    )
    xdg = tmp_path / "xdg"
    assert shim.config_path({"XDG_CONFIG_HOME": str(xdg), "HOME": home}) == (
        xdg / "create-reso-world" / "review-eval.toml"
    )


def test_store_inside_reviews_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    outside = write_collection_config(
        tmp_path / "ok.toml", store=tmp_path / "store", workspace_root=root, repos=("usaturn/alpha",)
    )
    assert load_config(outside).store == tmp_path / "store"
    inside = write_collection_config(
        tmp_path / "ng.toml", store=root / "reviews" / "store", workspace_root=root, repos=("usaturn/alpha",)
    )
    with pytest.raises(ConfigError):
        load_config(inside)
```

- [ ] **Step 6: テストを実行する**

Run: `uv run --locked pytest tools/review_eval/tests -q`
Expected: 6 passed（store 4・config 2）

- [ ] **Step 7: 写したファイルが AW と一致することを確かめる**

Run: `for f in __init__.py canonical.py models.py formats.py scanner.py store.py; do cmp "$AW/review_eval/$f" "tools/review_eval/$f" || echo "DIFF $f"; done`
Expected: 出力なし

- [ ] **Step 8: Commit**

```bash
git add tools/review_eval
git commit -m "feat(review-eval): add the config, store and scanner core (#352)"
```

### Task 2: capture（収集）

**Files:**
- Create（AW を写して変更）: `tools/review_eval/capture.py`
- Create（AW を写して変更）: `tools/review_eval/tests/test_capture.py`

**Interfaces:**
- Consumes: Task 1 の `config`・`store`・`scanner`・`formats`・`models`・`shim`・テスト補助
- Produces: `capture.collect(*, route, event, review_dir, files=(), records=(), repository=None, pr=None, context=None, trigger="save", sweep=True, verify_loop_run=None, config_path=None, environ=None, allow_runner_child=False, deadline=None) -> CollectionReport`（AW と同じ）、`VirtualRecord`・`CollectionReport`・`CaptureError`・`QUIET_STATUSES`・`REVIEW_DIR_NAME`・`classify`・`identify_review_dir`・`read_once`・`sweep_paths`・`in_period`・`failure_key`・`valid_virtual_path`、新しく `LEGACY_PARENT = "old"`・`is_legacy(parts: tuple[str, ...]) -> bool`

テストの要否: 要。無効時・承認の欠落・store 未初期化・runner の子で書かないこと（無断の収集）、sources の許可リスト（別 repo の取り違え）、旧配置と範囲外（誤った場所の収集）、symlink（パスの脱出）、秘密（漏れ）、上限・sweep・上書き前の版・scan の回復（記録の消失）は、どれも壊れてもエラーにならない S である。

- [ ] **Step 1: `capture.py` を写して CRW に合わせる**

```bash
cp "$AW/review_eval/capture.py" tools/review_eval/capture.py
```

  1. `from tools.review_eval.config import Config, ConfigError, Route, Source, check_registered, load_config` を `from tools.review_eval.config import Config, ConfigError, Route, Source, load_config` にする
  2. `REVIEW_DIR_NAME = ...` の次に足す:

     ```python
     # CRW が旧配置（reviews/#<N>-*）を移した場所。reviews/old/<repo>/#<N>-* の 3 階層は owner が old の新配置
     LEGACY_PARENT = "old"


     def is_legacy(parts: tuple[str, ...]) -> bool:
         """reviews からの相対パスの要素が旧配置（`#<N>-*` か `old/#<N>-*`）か。"""
         if len(parts) == 1:
             return REVIEW_DIR_NAME.fullmatch(parts[0]) is not None
         return len(parts) == 2 and parts[0] == LEGACY_PARENT and REVIEW_DIR_NAME.fullmatch(parts[1]) is not None
     ```

  3. `identify_review_dir` の `if len(parts) == 1 and REVIEW_DIR_NAME.fullmatch(parts[0]):` を `if is_legacy(parts):` にし、メッセージを `"旧配置（reviews/#<N>-*・reviews/old/#<N>-*）"` にする
  4. `_hold_legacy` の `reason` を `"旧配置（reviews/#<N>-*・reviews/old/#<N>-*）は自動で取らない。README の手順で扱う"` にする
  5. `_collect` の `check_registered(config)` の行を消す（`load_config(path)` だけを try に残す）

- [ ] **Step 2: `test_capture.py` を写して CRW に合わせる**

```bash
cp "$AW/review_eval/tests/test_capture.py" tools/review_eval/tests/test_capture.py
```

  1. `from tools.test_support.review_eval import FAKE_SCANNER, write_collection_config, write_projects_toml` を `from tools.review_eval.tests.support import FAKE_SCANNER, FLAGGING_SCANNER, write_collection_config` にする
  2. `_workspace` の `write_projects_toml(root, repos)` の行を消す
  3. `test_secret_body_is_withheld_and_never_printed` の `_workspace(tmp_path, monkeypatch, scanner=None)` を `_workspace(tmp_path, monkeypatch, scanner=FLAGGING_SCANNER)` にする
  4. `test_collect_failure_is_reported_without_raising` の最後に `assert not ws.store.root.exists()` を足す（未初期化の store を作らない）

- [ ] **Step 3: CRW 固有のテストを足す（`test_capture.py` の末尾）**

```python
@pytest.mark.parametrize("state", ["missing", "disabled"])
def test_collect_writes_nothing_unless_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    ws = _workspace(tmp_path, monkeypatch)
    config = tmp_path / "review-eval.toml"
    if state == "missing":
        config.unlink()
    else:
        write_collection_config(
            config, store=ws.store.root, workspace_root=ws.root, repos=("usaturn/alpha",), enabled=False
        )
    review = ws.review_dir / "claude-opus-5-5.md"
    review.write_bytes(_review_markdown("無効のときの本文\n2 行目"))
    before = sorted(path.relative_to(ws.store.root) for path in ws.store.root.rglob("*"))

    report = collect(route="pr-review", event="complete", review_dir=ws.review_dir, files=[review])

    assert report.status == "disabled"
    assert sorted(path.relative_to(ws.store.root) for path in ws.store.root.rglob("*")) == before


@pytest.mark.parametrize("missing", ["approved_by", "approved_on", "sources"])
def test_enabled_config_without_approval_or_sources_collects_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    ws = _workspace(tmp_path, monkeypatch)
    config = tmp_path / "review-eval.toml"
    if missing == "sources":
        write_collection_config(config, store=ws.store.root, workspace_root=ws.root, repos=())
    else:
        lines = config.read_text(encoding="utf-8").splitlines()
        config.write_text("\n".join(line for line in lines if not line.startswith(f"{missing} =")) + "\n", encoding="utf-8")
    review = ws.review_dir / "claude-opus-5-5.md"
    review.write_bytes(_review_markdown("承認の無い設定"))

    report = collect(route="pr-review", event="complete", review_dir=ws.review_dir, files=[review])

    assert report.status == "failed"
    assert ws.store.observations() == []
    assert ws.store.failures() == []


def test_sources_allowlist_decides_scope_without_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _workspace(tmp_path, monkeypatch, repos=("someone/unregistered",))
    listed = ws.root / "reviews" / "someone" / "unregistered" / "#7-feat"
    listed.mkdir(parents=True)
    (listed / "model.md").write_bytes(_review_markdown("sources に書いた repo"))
    (ws.review_dir / "model.md").write_bytes(_review_markdown("sources に無い repo"))

    assert collect(route="pr-review", event="complete", review_dir=listed).status == "captured"
    assert collect(route="pr-review", event="complete", review_dir=ws.review_dir).status == "out_of_scope"

    assert [(o.repository, o.pr, o.path) for o in ws.store.observations()] == [
        ("someone/unregistered", 7, "model.md")
    ]


def test_legacy_and_external_review_dirs_are_not_captured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _workspace(tmp_path, monkeypatch, repos=("usaturn/alpha", "old/alpha"))
    legacy = ws.root / "reviews" / "old" / "#5-feat"
    external = ws.root / "external" / "alpha" / "reviews" / "#5-feat"
    owner_old = ws.root / "reviews" / "old" / "alpha" / "#6-feat"
    for directory in (legacy, external, owner_old):
        directory.mkdir(parents=True)
        (directory / "model.md").write_bytes(_review_markdown("旧配置か範囲外の本文"))

    legacy_report = collect(route="pr-review", event="complete", review_dir=legacy)
    external_report = collect(route="pr-review", event="complete", review_dir=external)
    owner_report = collect(route="pr-review", event="complete", review_dir=owner_old)

    assert (legacy_report.status, legacy_report.failures) == ("held", ["legacy_layout"])
    assert (external_report.status, external_report.message) == ("out_of_scope", "outside_reviews")
    assert owner_report.status == "captured"
    assert [(o.repository, o.pr, o.review_dir) for o in ws.store.observations()] == [
        ("old/alpha", 6, "reviews/old/alpha/#6-feat")
    ]
    assert [(f.kind, f.review_dir, f.pr) for _, f, pending in ws.store.failures() if pending] == [
        ("legacy_layout", "reviews/old/#5-feat", 5)
    ]


def test_artifact_over_limit_is_not_stored_and_reason_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _workspace(tmp_path, monkeypatch)
    write_collection_config(
        tmp_path / "review-eval.toml",
        store=ws.store.root,
        workspace_root=ws.root,
        repos=("usaturn/alpha",),
        max_artifact_bytes=64,
    )
    review = ws.review_dir / "model.md"
    review.write_bytes(_review_markdown("大きい本文。" + "あ" * 40))

    report = collect(route="pr-review", event="complete", review_dir=ws.review_dir, files=[review])

    assert report.failures == ["too_large"]
    assert ws.store.observations() == []
    assert ws.store.blob_bytes_total() == 0
    (failure,) = [f for _, f, pending in ws.store.failures() if pending]
    assert (failure.kind, failure.path) == ("too_large", "model.md")
    assert "max_artifact_bytes" in failure.reason
```

- [ ] **Step 4: テストを実行する**

Run: `uv run --locked pytest tools/review_eval/tests -q`
Expected: 23 passed（Task 1 の 6、capture の AW 9 と CRW 8）。`test_document_for_same_number_in_another_repo_is_not_captured` は 1.1 秒待つ（AW のまま）

- [ ] **Step 5: Commit**

```bash
git add tools/review_eval/capture.py tools/review_eval/tests/test_capture.py
git commit -m "feat(review-eval): add capture with CRW legacy layouts and an allowlist of sources (#352)"
```

### Task 3: 確認待ち台帳と packet

**Files:**
- Create（AW のまま `cp`）: `tools/review_eval/ledger.py`・`ledger_ops.py`・`ledger_state.py`・`packets.py`
- Create（AW を写して変更）: `tools/review_eval/tests/ledger_support.py`・`test_ledger.py`・`test_packets.py`

**Interfaces:**
- Consumes: Task 1・2（`capture.collect`、`store.Store`、`support.write_collection_config`・`append_times_worker`）
- Produces: `ledger.Ledger`・`LedgerError`・`Label`・`LABELS`・`new_id`、`ledger_ops` の `CANDIDATE_STATUSES`・`EXPOSURE_KINDS`・`RELATIONS`・`ROLES`・`SCOPES`・`SPLITS`・`STAGES`・`GOLD_ROLES`・`Answer`・`Role`、`packets.export_packet`・`import_answers`（AW のまま）

テストの要否: 要。正解・管理用の情報の混入、正解担当の evaluator 化、stale な回答の取り込み、露出した系列の held-out、並行の追記の取りこぼしは、壊れても誤っているがもっともらしい評価データが残る S である（AW の 6 件をそのまま移す）。

- [ ] **Step 1: AW のままのファイルを写す**

```bash
for f in ledger.py ledger_ops.py ledger_state.py packets.py; do cp "$AW/review_eval/$f" "tools/review_eval/$f"; done
cp "$AW/test_support/review_eval_ledger.py" tools/review_eval/tests/ledger_support.py
cp "$AW/review_eval/tests/test_ledger.py" "$AW/review_eval/tests/test_packets.py" tools/review_eval/tests/
```

- [ ] **Step 2: テストの import と設定の書き方を直す**

  1. `ledger_support.py`: `from tools.test_support.review_eval import write_collection_config, write_projects_toml` を `from tools.review_eval.tests.support import write_collection_config` にし、`setup` の `write_projects_toml(root, REPOS)` の行を消す
  2. `test_ledger.py`: `from tools.test_support.review_eval import append_times_worker` を `from tools.review_eval.tests.support import append_times_worker`、`from tools.test_support.review_eval_ledger import (` を `from tools.review_eval.tests.ledger_support import (` にする
  3. `test_packets.py`: `from tools.test_support.review_eval_ledger import ...` を `from tools.review_eval.tests.ledger_support import ...` にする

- [ ] **Step 3: テストを実行する**

Run: `uv run --locked pytest tools/review_eval/tests -q`
Expected: 29 passed

- [ ] **Step 4: 写したファイルが AW と一致することを確かめる**

Run: `for f in ledger.py ledger_ops.py ledger_state.py packets.py; do cmp "$AW/review_eval/$f" "tools/review_eval/$f" || echo "DIFF $f"; done`
Expected: 出力なし

- [ ] **Step 5: Commit**

```bash
git add tools/review_eval
git commit -m "feat(review-eval): add the review ledger and packets (#352)"
```

### Task 4: inventory・reconcile・CLI

**Files:**
- Create（AW を写して変更）: `tools/review_eval/inventory.py`・`tools/review_eval/cli.py`
- Create（AW のまま `cp`）: `tools/review_eval/__main__.py`
- Create（AW を写して変更）: `tools/review_eval/tests/test_reconcile.py`

**Interfaces:**
- Consumes: Task 1〜3 のすべて、Task 2 の `LEGACY_PARENT`
- Produces: `inventory.inventory(store, repository, pr) -> dict`・`reconcile(store, config, *, repository, apply, config_path=None) -> dict`・`review_dirs(config, repository, pr=None) -> list[Path] | None`・`check_loop_run`・`record_failures`・`loop_references`（AW と同じ）。`cli.main(argv=None) -> int` と `python -m tools.review_eval` のサブコマンド（`config check`・`store init`・`status`・`verify`・`restore`・`failures ack`・`hook`・`ingest`・`inventory`・`reconcile`・`ledger ...`・`packet export|import`。AW と同じ）

テストの要否: 要。失われた loop の版の検出と `--apply` の取り込み（記録の消失）と、旧配置の計数（誤った場所の取り込み・数え漏れ）は S である。CLI の終了コードと JSON の表示はエラーの経路か表示なので L とし、Task 6 で手動で確かめる。

- [ ] **Step 1: ファイルを写して CRW に合わせる**

```bash
cp "$AW/review_eval/inventory.py" "$AW/review_eval/cli.py" "$AW/review_eval/__main__.py" tools/review_eval/
cp "$AW/review_eval/tests/test_reconcile.py" tools/review_eval/tests/test_reconcile.py
```

  1. `inventory.py`: capture からの import に `LEGACY_PARENT` を足し、`_legacy_dirs` を次にする:

     ```python
     def _legacy_dirs(config: Config) -> int:
         """旧配置（`reviews/#<N>-*` と `reviews/old/#<N>-*`。symlink を除く）の件数。external/*/reviews は数えない。"""
         reviews = config.workspace_root / "reviews"
         count = 0
         for parent in (reviews, reviews / LEGACY_PARENT):
             try:
                 entries = list(parent.iterdir()) if parent.is_dir() and not parent.is_symlink() else []
             except OSError:
                 continue
             count += sum(1 for entry in entries if REVIEW_DIR_NAME.fullmatch(entry.name) and not entry.is_symlink())
         return count
     ```

  2. `cli.py`: config からの import の `check_registered` を消し、`_config_check` の `if config.enabled:` と `check_registered(config)` の 2 行を消す（`load_config(path)` だけを try に残す）
  3. `test_reconcile.py`: `from tools.test_support.review_eval import write_collection_config, write_projects_toml` を `from tools.review_eval.tests.support import write_collection_config` にし、`write_projects_toml(root, [REPOSITORY])` の行を消す

- [ ] **Step 2: 旧配置の計数のテストを足す（`test_reconcile.py` の末尾）**

```python
def test_reconcile_counts_legacy_layouts_without_reading_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "workspace"
    current = root / "reviews" / "usaturn" / "alpha" / "#5-feat"
    legacy = (root / "reviews" / "#3-old", root / "reviews" / "old" / "#4-old")
    external = root / "external" / "alpha" / "reviews" / "#5-old"
    for directory in (current, *legacy, external):
        directory.mkdir(parents=True)
        (directory / "claude-opus-5-5.md").write_bytes(_review_markdown(f"{directory.name} の本文\n2 行目"))
    store = Store.init(tmp_path / "store")
    config = write_collection_config(
        tmp_path / "review-eval.toml", store=store.root, workspace_root=root, repos=[REPOSITORY]
    )
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", str(config))

    assert main(["reconcile", "--repo", REPOSITORY]) == 1
    report = json.loads(capsys.readouterr().out)

    assert report["counts"]["legacy_layout"] == 2
    assert [item["review_dir"] for item in report["unobserved"]] == ["reviews/usaturn/alpha/#5-feat"]
    assert store.observations() == []
```

- [ ] **Step 3: テストを実行する**

Run: `uv run --locked pytest tools/review_eval/tests -q`
Expected: 31 passed

- [ ] **Step 4: CLI が起動することを確かめる**

Run: `env REVIEW_EVAL_CONFIG="$(mktemp -d)/none.toml" uv run --locked python -m tools.review_eval status; echo "exit=$?"`
Expected: `{"enabled": false}` と `exit=0`

- [ ] **Step 5: `__main__.py` が AW と一致することを確かめる**

Run: `cmp "$AW/review_eval/__main__.py" tools/review_eval/__main__.py && echo same`
Expected: `same`

- [ ] **Step 6: Commit**

```bash
git add tools/review_eval
git commit -m "feat(review-eval): add inventory, reconcile and the CLI (#352)"
```

### Task 5: 運用手順と対応表

**Files:**
- Create（AW を写して変更）: `tools/review_eval/README.rst`・`tools/review_eval/sources.rst`
- Modify: `README.md`（「構成」の `tools/` の 2 行目）

**Interfaces:**
- Consumes: Task 1〜4 の実装（CLI のサブコマンド・設定の項目・failure の kind・旧配置の規則）

テストの要否: 不要（文書。固定文言のテストは F）。代わりに、RST の構文の検査（rstcheck）、`git diff` の確認、文書に書いたパス・関数名・コマンドが CRW に実在することの grep で確かめる。

- [ ] **Step 1: 写す**

```bash
cp "$AW/review_eval/README.rst" "$AW/review_eval/sources.rst" tools/review_eval/
```

- [ ] **Step 2: `README.rst` を CRW に合わせる**

次の値・文をすべて直す。ほかの節（failure の表、台帳の手順、収集担当向けの注意など）の内容は、下の項目に関係する語句だけを直す。

  1. 概要の「このPRは仕組みだけを作る。…」を「この版（#352）は収集の仕組みだけを作る。4 経路の保存点への接続は #357（review-eval-hooks）が行う。実データの収集を有効にすることと、過去の記録の調査は、この版の範囲に入れない。」にする
  2. 前提条件: 「create-reso-world の親 checkout（`PARENT_ROOT`。例 `/workspaces/reso-world`）の root から実行する。root の `pyproject.toml` と `uv.lock` を使う」「`reviews/` だけを読む。`projects.toml` などの登録は使わない」「秘密検査に gitleaks を使う（既定）。`.devcontainer/install_gitleaks.bash` が入れる版を使う」にする
  3. コマンドの形を `uv run --locked python -m tools.review_eval <サブコマンド> ...` にする
  4. 設定パスを `${XDG_CONFIG_HOME}/create-reso-world/review-eval.toml`（`XDG_CONFIG_HOME` が絶対パスのとき。それ以外は `$HOME/.config/create-reso-world/review-eval.toml`）にする
  5. store の推奨の例を `/home/vscode/review-eval/collected` にし、「リポジトリの中に置くときは git の追跡対象外の私有の場所にする」と足す。設定例の `store` をその値、`workspace_root` を `/workspaces/reso-world`、`[[sources]]` の `repo` を `usaturn/create-reso-world` にする
  6. `sources` の説明を「明示の許可リストである。`projects.toml`・`external-tools.toml` の登録は照合しないので、未登録の repo も書けば対象になる。書かない限り収集の対象は広がらない。`repo` は `<owner>/<repo>` の形（`.` 始まりの repo は書けない）、`since` は `until` 以前にする。誤りは設定の誤りになる」にする
  7. 「初期化、起動、停止」の手順 4 を「`enabled = true` にする。4 経路の保存点への接続（#357）の後は、保存点から自動で収集する。この版では `ingest`・`reconcile --apply` の手動の経路だけが収集する。」にする
  8. 「自動取得の接続点」の冒頭を「この節は、#357 で接続する予定の保存点である。この版の helper は `capture.collect` を呼ばない。」にし、「SKILL.md の文面は変えていない」は「接続の後も SKILL.md の文面は変えない予定である」にする
  9. 旧配置: failure の表の `legacy_layout` を「旧配置（`reviews/#<N>-*` と `reviews/old/#<N>-*`）。自動では取らず保留する（次の節）」、「旧形式、旧配置の制約」の旧配置の行を同じ 2 つの配置にし、`public/reviews/` の行を「`external/*/reviews/`（resoloop などの checkout の中の旧配置）は `workspace_root/reviews` の外にあるため範囲外である。取り込まず、`reconcile` も数えない。`reviews/old/<repo>/#<N>-*`（3 階層）は owner が `old` の新配置として扱う」にする
  10. 「収集担当向けの注意」の「保存先は `private/` などの私有の場所に置く。テストと fixture は `private/` に書かない」を「保存先はリポジトリの外か、git の追跡対象外の私有の場所に置く。テストと fixture は実の保存先に書かない」に、「このPRには含まれない」を「この版には含まれない」にする
  11. 「経路・保存点を足す手順」の 2 の例（`review_findings.py` と `upsert_pr_comment.py`）は「#357 で接続する予定」と書く
  12. 「テストの隔離」を次の内容にする: テストは保存先と設定を `tmp_path` に置き、`monkeypatch.setenv("REVIEW_EVAL_CONFIG", <一時の設定>)` で向ける。実の保存先と実の `~/.config` は読まない・書かない。`tools/review_eval/tests/conftest.py` が各テストの前に `REVIEW_EVAL_CONFIG` を空文字にする（このディレクトリのテストだけ。他の helper のテストが収集を呼ぶようになったら、全体の隔離が要る。#357）。補助関数は `tools/review_eval/tests/support.py`・`ledger_support.py`。検証は feature worktree の root で `uv run --locked pytest tools/review_eval/tests` と、README.md の「テスト」の各コマンド
  13. AW の Spec の節番号（「Spec 4.5」など）が残る箇所は、Spec を `docs/superpowers/specs/2026-11-09-issue-352-review-eval-core-design.md` と書くか、節番号を外す
  14. CRW の RST の規則（`.agents/skills/rst-writer/references/profiles/create-reso-world.md`）に合わせる: Sphinx の role（`:ref:` など）を使わない。同じファイルの節への参照は docutils の名前付き参照（`` `表示名 <review_eval_readme_legacy_>`_ ``。ラベル `.. _review_eval_readme_legacy:` はそのまま残す）、別のファイルはリポジトリのルート基準のパスを本文に書く（例: `tools/review_eval/sources.rst` の「復元できないもの（分類 5）」）。最終行に装飾なしの「以上」を置く。句点「。」の直後で改行する

- [ ] **Step 3: `sources.rst` を CRW の helper で確かめた内容に直す**

  1. 各節・各行が名前を挙げる CRW のファイルと関数（`review_run.py`・`review_run_record.py`・`pr_review_workspace.py` の `save`・`atomic_copy`、`loop.py`、`upsert_pr_comment.py`、`finalize.py`、`run_roles.py`、`review_findings.py`、`dispatch.py`、`review_records.py`、`review_target.py`）を `grep -n` で開き、書き手・保存時点・保存場所・保持条件が CRW の実装と合うかを確かめる。合わないものは CRW の実装に合わせて書き直す。確かめられなかった項目は「不明」と書く
  2. AW の収集の接続（`review_run.collect_outputs` など、CRW に無い関数）と「改修要否と理由」の列は、今あるものとして書かない。「#357 で接続する予定」と書き、列の「要。…」は「#357 で…」の形にする
  3. 「SKILL.md を変えない理由」の「このPRでは」を「#357 の設計では」にし、今は接続が無いことを足す
  4. 「旧配置（`reviews/#<N>-*`）」と `public/reviews/` を、README.rst の 9 と同じ扱い（`reviews/old/#<N>-*` を足し、`external/*/reviews/` は範囲外）にする
  5. README.rst の 14 と同じ RST の規則に合わせる（`:ref:` を名前付き参照か別ファイルのパスにし、最終行に「以上」）
  6. 確かめた結果（直した行、「不明」にした行）を作業報告の `concerns` に列挙する

- [ ] **Step 4: `README.md` の「構成」に足す**

`│                              devenv_migration（pi の設定の移行のテスト）、test_support（共有のテストの fixture）` の行の末尾の `）` の後に `、` を足し、次の行に `│                              review_eval（レビュー記録の私有の保存先への収集。既定は無効。tools/review_eval/README.rst）` を足す

- [ ] **Step 5: 検査する**

Run: `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$PWD/tools/review_eval/README.rst" "$PWD/tools/review_eval/sources.rst"; grep -n ":ref:\|agent-workspace\|devenv\|projects.toml に登録\|public/reviews\|verify-devenv\|private/review-eval\|このPR" tools/review_eval/README.rst tools/review_eval/sources.rst`
Expected: rstcheck が終了コード 0 で `Success! No issues detected.`。grep の出力は無い（`projects.toml` を「照合しない」と説明する行だけは残ってよい）

- [ ] **Step 6: Commit**

```bash
git add tools/review_eval/README.rst tools/review_eval/sources.rst README.md
git commit -m "docs(review-eval): add the CRW operating guide and the route mapping (#352)"
```

### Task 6: 統合の検証（controller が実行する。コードを変えない）

テストの要否: 不要（統合の確認）。下の手動の確認はコミットしない。

- [ ] **Step 1: review_eval と tools 全体のテスト**

Run: `uv run --locked pytest tools/review_eval/tests -q` → 31 passed。`uv run --locked pytest tools -q` → failed 0
- [ ] **Step 2: レイアウトの検査**

Run: `bash scripts/check-layout.sh` → 終了コード 0（追跡対象外のローカルワールドだけの失敗は、main でも同じことを確かめて報告する）
- [ ] **Step 3: 設定なしの CLI（隔離: 一時の HOME・存在しない設定、`GIT_*` を除く）**

`status` が `{"enabled": false}` で 0、`config check` が `enabled: false` の JSON で 0、一時の HOME に何も作られないこと。壊れた TOML の設定で `status`・`config check` が 2、`collect` が `failed` で store に何も書かないこと。相対パス・末尾の `/` の review_dir を `ingest` で渡して同じ observation になること
- [ ] **Step 4: 実 gitleaks での既定の argv**

一時の workspace・store・設定（`secret_scanner` を書かない）で、実行時に組み立てた `ghp_` のトークンを含む Markdown と含まない Markdown を `ingest` し、前者が `withheld_secret`、後者が `stored` で、store・標準出力・標準エラーにトークンが無いこと
- [ ] **Step 5: 範囲の確認**

Run: `git diff --stat "$CODE_BASE_SHA"...HEAD` → 変更は `tools/review_eval/**`・`README.md`・Spec・Plan だけ

## 実行方式

`implement_task.py check` の `self` が false（`--implement pi_opencode-go_deepseek4-flash_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task 1〜5 を 1 つずつ順に runner の担当へ依頼する（`superpowers:subagent-driven-development` の形）。Task は前の Task のモジュールに依存するので並行しない。各 Task の取り込み後に controller が関連テストを実行し、Task のレビュー（Plan・受け入れ基準との照合、AW との差分の確認）を行う。Task 6 は controller が実行する（検証だけ）。

## 実行予算

- 全体: 能動時間 480 分（ledger `tmp/agents/issue-352.83snyw06/budget.jsonl`、2026-11-09T07:10Z 開始。予約・調査・Spec の約 20 分は ledger の前）。根拠: 5 Task（runner の担当、1 Task 20〜50 分）と、PR 修正ループの最大 3 サイクル
- phase の目安: Plan 20 分、実装 5 Task 計 180 分、統合の検証・PR 40 分、ループ 1 サイクル 75 分（レビュー 45 分＋計画・修正 30 分）×最大 3
- worker: runner の `implement` の期限 90 分（runner の既定）。無進捗の打ち切りは runner に任せる
- 再試行の上限: 同じ失敗（signature）は 1 回まで。`retry`（BLOCKED・NEEDS_CONTEXT）・`rejected`（`outside_changes`）とも Task ごとに 1 回。Task のレビューの指摘の修正の依頼は Task ごとに 2 回まで
- checkpoint: 各 Task の取り込み後、PR の作成後、ループの各サイクルの後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) Task 5 の `sources.rst` の確認が足りなければ、確かめた行だけを残し、ほかを「不明」にする。(2) 予算が足りなければ Task 5 の README.rst の直しを Step 2 の 1〜9 に絞る。(3) Task 3 の spawn の並行テストが runner の担当の環境だけで落ちるなら、controller の実行で確かめて ledger に記録する

## contingency（代替策）

- runner の `failed`・上限に達した `retry`・`rejected`: その Task で止まり、利用者に担当の変更を委ねる（controller は `self` で引き取らない）
- AW のコードが CRW の依存（pydantic・pytest の版）で動かない: 仕様の意味を保つ最小の修正を ledger に記録して続ける。意味が変わる修正は利用者の裁定を待つ
- Task のテストの件数が Plan と違う: 移したテストの欠落・重複を調べる。AW の 19 件と CRW の 12 件（Task 1 の 3 件、Task 2 の 8 件、Task 4 の 1 件）がそろえば件数の差は数え方の誤りとして Plan を直す
- 実 gitleaks（Task 6 の 4）で既定の argv が動かない（`scan_failed`）: CRW の gitleaks の版で `dir` の引数を確かめ、`scanner.DEFAULT_SCANNER` を最小に直す（Task 1 のファイルの変更として runner の担当に依頼する）。直せなければ持ち越しとして PR に書く
- base が動いた: issue-to-pr の `recheck_bases` の規則で止まる

## 完了

（実行の後に記録する）
