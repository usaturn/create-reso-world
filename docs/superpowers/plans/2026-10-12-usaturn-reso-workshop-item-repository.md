# usaturn/reso-workshop: アイテムの器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## 管理・実行許可

- 文書管理: `usaturn/create-reso-world`（ブランチ `docs/reso-workshop`）
- コード対象: 新しく作る `usaturn/reso-workshop`（非公開、未作成）。`CODE_ROOT=/workspaces/reso-world/worlds/reso-workshop`（Task 1 で作る。ブランチ `main`）
- 検証した基準: create-reso-world `4d518a963dfc2301d528c748e7387de04a7e1594`、ResoLoop `0.1.0-preview.17.fork`（`external/resoloop` `84c7932`）、uv `0.12.24`
- 状態: completed（2026-10-12 19:16 JST。結果は末尾の「結果」）
- 関連 Spec: `docs/superpowers/specs/2026-10-12-usaturn-reso-workshop-item-repository-design.md`（承認 `a1dc8707df5310790af82501da611fec6d0eaa46`、記録 `4b4d7e0`）
- 実行許可: 2026-10-12 に利用者が「プランを作ったらそのまま実行してください。サブエージェントモードで。」と指示した。この Plan は subagent-driven-development でそのまま実行する。Plan の内容そのものへの個別の承認は受けていない。GitHub のリポジトリ作成と push（Task 9）は、Spec の決まりどおり実行の直前に利用者へ確認する
- 着手: 2026-10-12 18:25 JST

**Goal:** `worlds/reso-workshop/` に、アイテムを雛形から作り（`workshop new`）、工房へ反映・検査・記録し（`workshop deploy`）、インベントリへの保存を記録する（`workshop saved`）器のリポジトリを作り、GitHub の非公開リポジトリへ push する。

**Architecture:** ResoLoop の世界のプロジェクト（`scripts/new-world.sh` で作る）に、独自の Git を持たせる。アイテムごとに `items/<名前>/` を置き、所有キー `workshop-<名前>` と state を分ける。CLI は標準ライブラリだけの小さな Python パッケージ（`tools/workshop/`）で、resoloop を subprocess で呼ぶ。

**Tech Stack:** Python 3.12 以上（uv、`uv_build`）、pytest、ResoLoop CLI、git、gh

**Spec:** `docs/superpowers/specs/2026-10-12-usaturn-reso-workshop-item-repository-design.md`（create-reso-world）

## Global Constraints

- 作業は `CODE_ROOT=/workspaces/reso-world/worlds/reso-workshop` で行い、その `main` にコミットする。push はしない（Task 9 で利用者の確認後に controller が行う）
- create-reso-world のファイル（`scripts/`・`templates/`・`AGENTS.md` など）は変えない
- Python は `uv run ...` で実行する。`python3` コマンドは使わない
- 実行時の依存は標準ライブラリだけ（`tomllib`・`json`・`argparse`・`subprocess`・`dataclasses`）。開発の依存は `pytest` だけ。`requires-python = ">=3.12"`
- 利用者に見せる文言とコメントは日本語で簡潔に書く。「正本」「着地」「契約」「原子的」「製品」は使わない
- アイテムの名前: `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` に合う 40 文字以内。所有キーは `workshop-<名前>`
- ルートスロット: key は `root`、名前は `<display_name> v<version>`、親は `Root`
- state: `.resoloop/state/workshop-<名前>.json`、ProtoFlux の配置の state: `.resoloop/flux-state/workshop-<名前>.json`
- 区画 n の位置: X = ((n − 1) mod 8) × 1.5、Y = 1.0、Z = 2.0 + floor((n − 1) / 8) × 1.5
- 大きなファイル: 52,428,800 バイト（50 MiB）を「超える」もの
- 終了コード: 0 成功、1 検査や手順の失敗、2 使い方の誤り
- `git clean` は使わない。シェル変数を使う `rm` は `rm -rf -- "${VAR:?}/..."` の形にする
- Task 1〜7 では Resonite に接続しない
- テストは create-reso-world の「テストの採用基準」に従う。文書の文言を照合するテストは書かない

## Review Focus

- 表示名に `"`・`\`・改行・日本語・DEL（U+007F）が入る → `item.toml` と `deploys.toml` が tomllib で読み戻せ、値が変わらない（Task 3・Task 5 のテスト）
- `items/` に隠しディレクトリ・ファイル・`item.toml` の無いディレクトリ・名前の規則に合わないディレクトリがある → `list` と `check` が落ちず、問題として報告する（Task 2・Task 5 のテスト）
- resoloop の `diff` が接続できずに 0 以外で終わる、または JSON でない出力を返す → deploy は差分の段階で止まり、記録しない（Task 6 のテスト）
- `deploys.toml` が壊れている（TOML の誤り・型の違い） → `check`・`list`・`saved` がトレースバックを出さずに 1 で終える（Task 3・Task 5 のテスト）
- アイテムのディレクトリ（`items/<名前>/`）を cwd にして実行する → リポジトリのルートを見つけて動く（Task 2・Task 5 のテスト）

## ファイルの構成

| ファイル | 役割 | Task |
| --- | --- | --- |
| `.gitignore`・`pyproject.toml`・`AGENTS.md`（固有の節）・`items/.gitkeep` | 骨組みと規約 | 1 |
| `templates/item/manifest.json`・`templates/item/flux/{Main.pg,protograph.toml,.gitignore}` | アイテムの雛形 | 1 |
| `tools/workshop/__init__.py`・`tools/workshop/errors.py` | パッケージと例外 | 1 |
| `tools/workshop/items.py`・`tests/conftest.py`・`tests/test_items.py` | 名前・`item.toml`・区画・マニフェスト | 2 |
| `tools/workshop/ledger.py`・`tests/test_ledger.py` | `deploys.toml` と保存の条件 | 3 |
| `tools/workshop/gitstate.py`・`tests/test_gitstate.py` | コミット・未コミットの判定・大きなファイル | 4 |
| `tools/workshop/scaffold.py`・`tools/workshop/checks.py`・`tools/workshop/cli.py`・`tests/test_cli.py` | `new`・`list`・`check`・`saved` | 5 |
| `tools/workshop/deploy.py`・`tools/workshop/cli.py`（追加）・`tests/test_deploy.py` | `deploy` | 6 |
| `README.md` | 使い方と clone したあとの手順 | 7 |

---

### Task 1: 骨組み（プロジェクトの作成・Git・雛形・規約）

**テストの要否:** 不要。設定・雛形・規約だけで、実行して確かめるロジックが無い。代わりに Step 8 のコマンドで確かめる。

**Files:**
- Create（スクリプトで）: `/workspaces/reso-world/worlds/reso-workshop/`
- Delete: `content/`、`flux/`（`resoloop init` が作る。工房では使わない）
- Create: `.gitignore`、`items/.gitkeep`、`templates/item/manifest.json`、`templates/item/flux/Main.pg`、`templates/item/flux/protograph.toml`、`templates/item/flux/.gitignore`、`tools/workshop/__init__.py`、`tools/workshop/errors.py`
- Modify: `pyproject.toml`、`AGENTS.md`（`## このプロジェクト固有` の節）

**Interfaces:**
- Produces: パッケージ `workshop`（`tools/workshop/`）、`workshop.errors.WorkshopError(message: str, exit_code: int = 1)`、コンソールスクリプト `workshop = "workshop.cli:main"`（`cli.py` は Task 5 で作る）、pytest の設定（`testpaths = ["tests", "items"]`、`--import-mode=importlib`）

- [ ] **Step 1: プロジェクトを作る**

```bash
cd /workspaces/reso-world && bash scripts/new-world.sh reso-workshop
```

Expected: 最後に `DONE: reso-workshop`。`worlds/reso-workshop/` に `.resoloop.json`・`AGENTS.md`・`CLAUDE.md`・`pyproject.toml`・`uv.lock`・`.agents/skills/`・`.claude/skills/`・`.pi`（symlink）ができる。

- [ ] **Step 2: 使わない生成物を消し、Git を始める**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && rm -rf -- content flux && git init -q -b main && git status --short | head
```

- [ ] **Step 3: `.gitignore` を書く**

`/workspaces/reso-world/worlds/reso-workshop/.gitignore`:

```gitignore
# 生成物・実機のセッションに結び付くファイル・環境ごとに作り直すものは入れない（Spec 4 章）
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
build/
artifacts/
.resoloop/
items/*/manifest.rendered.json
# リポジトリの外を指す symlink。clone したあとに scripts/new-world.sh --apply reso-workshop で作り直す（Spec D-7）
/.pi
/.claude/settings.json
/.agents/sp-*.md
```

- [ ] **Step 4: `pyproject.toml` を書き換える**

`/workspaces/reso-world/worlds/reso-workshop/pyproject.toml` の全体:

```toml
[project]
name = "reso-workshop"
version = "0.1.0"
description = "Resonite items built with resoloop and Blender, deployed to a workshop world"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
workshop = "workshop.cli:main"

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "workshop"
module-root = "tools"

[tool.pytest.ini_options]
testpaths = ["tests", "items"]
addopts = ["--import-mode=importlib"]
```

- [ ] **Step 5: パッケージと例外を作る**

`tools/workshop/__init__.py`:

```python
"""reso-workshop の CLI（uv run workshop）。"""
```

`tools/workshop/errors.py`:

```python
"""workshop の CLI が利用者に表示して終える誤り。"""


class WorkshopError(Exception):
    """exit_code は CLI の終了コード（1 は検査や手順の失敗、2 は使い方の誤り）。"""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code
```

- [ ] **Step 6: アイテムの雛形を作る**

`templates/item/manifest.json`（`ownership` と `slot` の key・name・parent・position は CLI が入れるので書かない）:

```json
{
  "schemaVersion": "1",
  "slot": {
    "scale": [1, 1, 1]
  },
  "components": [
    {
      "key": "grabbable",
      "type": "FrooxEngine.Grabbable",
      "fields": {
        "Scalable": true
      }
    }
  ],
  "tests": [
    {
      "name": "root-exists",
      "assertions": [
        {
          "target": "$slot:root",
          "exists": true
        }
      ]
    }
  ]
}
```

`templates/item/flux/Main.pg`:

```
module Main
where {
    "Hello from resoloop!"->display
}
```

`templates/item/flux/protograph.toml`:

```toml
name = "workshop-item"
version = "0.1.0"

[build.dev]
optimization_preset = "dev"

[dependencies]
```

`templates/item/flux/.gitignore`:

```gitignore
build/
.protograph/
*.brson
```

`items/.gitkeep` は空のファイル。

- [ ] **Step 7: `AGENTS.md` の `## このプロジェクト固有` の節を書き換える**

`resoloop init` が書いた前半（ResoLoop project guide）は残す。`new-world.sh` が足した `## このプロジェクト固有` の見出しはそのまま残し（`--apply` がこの見出しで判定する）、節の本文を次に置き換える:

```markdown
## このプロジェクト固有

reso-workshop は、Resonite のアイテムを作り、工房のワールドへ反映して管理するリポジトリ（GitHub の非公開リポジトリ `usaturn/reso-workshop`）。設計は create-reso-world の `docs/superpowers/specs/2026-10-12-usaturn-reso-workshop-item-repository-design.md`。

- このプロジェクトでは、上の `content/`・`flux/` の代わりに `items/<名前>/` にアイテムごとのマニフェストと ProtoFlux を置く。所有キーは `workshop-<名前>`、ルートスロットは `<表示名> v<版>`、state は `.resoloop/state/workshop-<名前>.json`
- テスト: このディレクトリで `uv run pytest` を実行する
- アイテムを足すときは `uv run workshop new` を使う。`items/` を手で複製しない
- 工房への反映は `uv run workshop deploy` だけで行う。resoloop の `apply` を直接実行しない
- 削除（`--prune`）は、`diff` で削除の内容を利用者に見せてから実行する
- Resonite は、接続が必要になる直前に起動を頼む。ポートは毎回変わるので、その都度確認する
- インベントリへの保存は利用者が行う。保存したと聞いてから `uv run workshop saved` を実行し、`deploys.toml` をコミットする
- Meshy の有料の操作は、操作ごとに承認をもらう。原本は `worlds/reso-workshop-meshy/` に置く
- 50 MiB を超えるファイルはコミットしない（`uv run workshop check` が検出する）
- コミットは `main` に直接行う。push は利用者の指示があるときだけ行う
- `git clean` は使わない
- Spec・Plan は create-reso-world の `docs/superpowers/` に置く
```

- [ ] **Step 8: 確かめる**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && uv sync && uv run python -c "from workshop.errors import WorkshopError; print(WorkshopError('x').exit_code)"
```

Expected: `uv sync` が 0 で終わり、`1` と表示される。

```bash
cd /workspaces/reso-world && bash scripts/new-world.sh --apply --no-sync reso-workshop
```

Expected: `created:`・`linked:`・`appended:`・`updated:` の行が出ず、`DONE: reso-workshop` で 0 終了（雛形の不足が無い）。`--no-sync` なので、最後に `note: uv.lock is not generated yet` の行が出るが問題ない。

- [ ] **Step 9: コミットして、追跡の範囲を確かめる**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add -A && git commit -q -m "chore: scaffold reso-workshop item repository" && git status --short && git ls-files | grep -E '^(\.pi$|\.claude/settings\.json$|\.agents/sp-|\.resoloop/|\.venv/|content/|flux/)' ; git status --short --ignored | grep '^!!'
```

Expected: `git status --short` は空。`git ls-files | grep` は何も出さない。`--ignored` には `.venv/`・`.resoloop/`・`.pi`・`.claude/settings.json`・`.agents/sp-implementer.md` が出る。

---

### Task 2: アイテムの定義・区画・マニフェスト（`items.py`）

**テストの要否:** 要る。名前と `item.toml` の検査、区画の計算、マニフェストの検査と書き出しは分岐のあるロジック。

**Files:**
- Create: `tools/workshop/items.py`
- Create: `tests/conftest.py`
- Test: `tests/test_items.py`

**Interfaces:**
- Consumes: `workshop.errors.WorkshopError`
- Produces（`workshop.items`）:
  - 定数 `KINDS = ("prop", "gadget")`、`NAME_RULE: str`
  - `@dataclass(frozen=True) class Item: name: str; display_name: str; kind: str; version: str; shelf: int`
  - `find_root(start: Path) -> Path`（見つからなければ `WorkshopError(..., exit_code=2)`）
  - `is_valid_name(name: str) -> bool`、`ownership_key(name: str) -> str`、`root_slot_name(item: Item) -> str`、`shelf_position(shelf: int) -> list[float]`
  - `item_dir(root: Path, name: str) -> Path`、`list_item_names(root: Path) -> list[str]`
  - `state_path(name: str) -> str`、`flux_state_path(name: str) -> str`（ルートからの相対パス）
  - `load_item(root: Path, name: str) -> tuple[Item | None, list[str]]`
  - `validate_manifest(root: Path, name: str) -> list[str]`
  - `render_manifest(root: Path, item: Item) -> Path`
  - `flux_manifest(name: str) -> dict[str, Any]`
- Produces（`tests/conftest.py` の fixture）: `git`（`git(root, *args) -> str`、失敗で例外）、`git_repo`（空のコミットの無いリポジトリ）、`workshop_root`（本物の `templates/item` と `.gitignore` を写し、最初のコミットを作った工房）

- [ ] **Step 1: テストの共通部品を書く**

`tests/conftest.py`:

```python
"""テストの共通部品。工房のリポジトリを一時ディレクトリに作る。"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_IDENTITY = (
    "-c", "user.name=workshop-test",
    "-c", "user.email=workshop-test@example.invalid",
    "-c", "commit.gpgsign=false",
)


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_IDENTITY, *args], capture_output=True, text=True, check=True
    )
    return result.stdout


@pytest.fixture
def git() -> Callable[..., str]:
    return run_git


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    return root


@pytest.fixture
def workshop_root(git_repo: Path) -> Path:
    """本物の templates/item と .gitignore を写し、最初のコミットを作った工房。"""
    shutil.copytree(REPO_ROOT / "templates" / "item", git_repo / "templates" / "item")
    shutil.copy2(REPO_ROOT / ".gitignore", git_repo / ".gitignore")
    (git_repo / "items").mkdir()
    (git_repo / "items" / ".gitkeep").write_text("", encoding="utf-8")
    run_git(git_repo, "add", "-A")
    run_git(git_repo, "commit", "-q", "-m", "init")
    return git_repo
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_items.py`:

```python
import json
import os
import shutil
from pathlib import Path

import pytest

from workshop import items
from workshop.errors import WorkshopError

VALID = 'display_name = "Desk Lamp"\nkind = "gadget"\nversion = "1.2.0"\nshelf = 3\n'


def write_item(root: Path, name: str, text: str) -> Path:
    directory = root / "items" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "item.toml").write_text(text, encoding="utf-8")
    return directory


def test_load_item_reads_valid_definition(workshop_root):
    write_item(workshop_root, "desk-lamp", VALID)
    item, errors = items.load_item(workshop_root, "desk-lamp")
    assert errors == []
    assert item == items.Item("desk-lamp", "Desk Lamp", "gadget", "1.2.0", 3)


@pytest.mark.parametrize(
    "text, fragment",
    [
        ('display_name = " "\nkind = "prop"\nversion = "1.0.0"\nshelf = 1\n', "display_name"),
        ('display_name = "A"\nkind = "avatar"\nversion = "1.0.0"\nshelf = 1\n', "kind"),
        ('display_name = "A"\nkind = "prop"\nversion = "1.0"\nshelf = 1\n', "version"),
        ('display_name = "A"\nkind = "prop"\nversion = "01.0.0"\nshelf = 1\n', "version"),
        ('display_name = "A"\nkind = "prop"\nversion = "1.0.0"\nshelf = 0\n', "shelf"),
        ('display_name = "A"\nkind = "prop"\nversion = "1.0.0"\nshelf = true\n', "shelf"),
        ('display_name = "A"\nkind = "prop"\nversion = "1.0.0"\nshelf = 1\ncolor = "red"\n', "color"),
        ('display_name = "A"\nkind = "prop"\n', "version"),
        ("display_name = \n", "読めません"),
    ],
)
def test_load_item_rejects_invalid_definition(workshop_root, text, fragment):
    write_item(workshop_root, "lamp", text)
    item, errors = items.load_item(workshop_root, "lamp")
    assert item is None
    assert any(fragment in error for error in errors)


def test_load_item_reports_missing_file(workshop_root):
    (workshop_root / "items" / "lamp").mkdir()
    item, errors = items.load_item(workshop_root, "lamp")
    assert item is None
    assert errors == ["items/lamp/item.toml: ありません"]


def test_load_item_rejects_invalid_directory_name(workshop_root):
    write_item(workshop_root, "Bad_Name", VALID)
    item, errors = items.load_item(workshop_root, "Bad_Name")
    assert item is None
    assert errors[0].startswith("items/Bad_Name:")


@pytest.mark.parametrize(
    "name, ok",
    [
        ("lamp", True),
        ("desk-lamp2", True),
        ("a", True),
        ("a" * 40, True),
        ("a" * 41, False),
        ("Lamp", False),
        ("-lamp", False),
        ("lamp-", False),
        ("desk_lamp", False),
        ("", False),
    ],
)
def test_is_valid_name(name, ok):
    assert items.is_valid_name(name) is ok


@pytest.mark.parametrize(
    "shelf, position",
    [
        (1, [0.0, 1.0, 2.0]),
        (2, [1.5, 1.0, 2.0]),
        (8, [10.5, 1.0, 2.0]),
        (9, [0.0, 1.0, 3.5]),
        (17, [0.0, 1.0, 5.0]),
    ],
)
def test_shelf_position(shelf, position):
    assert items.shelf_position(shelf) == position


def test_list_item_names_skips_hidden_entries_and_files(workshop_root):
    for name in ("b-item", "a-item", ".hidden"):
        (workshop_root / "items" / name).mkdir()
    (workshop_root / "items" / "README.md").write_text("x", encoding="utf-8")
    assert items.list_item_names(workshop_root) == ["a-item", "b-item"]


def test_list_item_names_without_items_directory(tmp_path):
    assert items.list_item_names(tmp_path) == []


def test_find_root_from_item_directory(workshop_root):
    directory = write_item(workshop_root, "lamp", VALID)
    assert items.find_root(directory) == workshop_root


def test_find_root_outside_repository(tmp_path):
    with pytest.raises(WorkshopError) as raised:
        items.find_root(tmp_path)
    assert raised.value.exit_code == 2


def test_validate_manifest_accepts_template(workshop_root):
    directory = write_item(workshop_root, "lamp", VALID)
    shutil.copy2(workshop_root / "templates" / "item" / "manifest.json", directory / "manifest.json")
    assert items.validate_manifest(workshop_root, "lamp") == []


@pytest.mark.parametrize(
    "manifest, fragment",
    [
        ({"schemaVersion": "1", "ownership": {"key": "x"}}, "ownership"),
        ({"schemaVersion": "1", "slot": {"key": "root"}}, "slot.key"),
        ({"schemaVersion": "1", "slot": {"name": "X"}}, "slot.name"),
        ({"schemaVersion": "1", "slot": {"parent": "Root"}}, "slot.parent"),
        ({"schemaVersion": "1", "slot": {"position": [0, 0, 0]}}, "slot.position"),
        ({"schemaVersion": "1", "slot": []}, "slot は"),
        ([1, 2], "オブジェクト"),
    ],
)
def test_validate_manifest_rejects_cli_owned_fields(workshop_root, manifest, fragment):
    directory = write_item(workshop_root, "lamp", VALID)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    errors = items.validate_manifest(workshop_root, "lamp")
    assert any(fragment in error for error in errors)


@pytest.mark.parametrize("content, fragment", [(None, "ありません"), ("{", "読めません")])
def test_validate_manifest_reports_missing_or_broken_file(workshop_root, content, fragment):
    directory = write_item(workshop_root, "lamp", VALID)
    if content is not None:
        (directory / "manifest.json").write_text(content, encoding="utf-8")
    errors = items.validate_manifest(workshop_root, "lamp")
    assert len(errors) == 1 and fragment in errors[0]


def test_render_manifest_fills_cli_owned_values(workshop_root):
    directory = write_item(workshop_root, "desk-lamp", VALID)
    manifest = {"schemaVersion": "1", "slot": {"scale": [2, 2, 2]}, "components": []}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    item, _ = items.load_item(workshop_root, "desk-lamp")
    path = items.render_manifest(workshop_root, item)
    assert path == directory / "manifest.rendered.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ownership"] == {"key": "workshop-desk-lamp"}
    assert data["slot"] == {
        "scale": [2, 2, 2],
        "key": "root",
        "name": "Desk Lamp v1.2.0",
        "parent": "Root",
        "position": [3.0, 1.0, 2.0],
    }
    assert data["components"] == []
    assert json.loads((directory / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_flux_manifest_states_resolve_to_item_states():
    manifest = items.flux_manifest("desk-lamp")
    flux_dir = Path("/r/items/desk-lamp/flux")
    assert manifest["parent"] == "$slot:root"
    assert os.path.normpath(flux_dir / manifest["worldState"]) == os.path.normpath(
        Path("/r") / items.state_path("desk-lamp")
    )
    assert os.path.normpath(flux_dir / manifest["deployState"]) == os.path.normpath(
        Path("/r") / items.flux_state_path("desk-lamp")
    )
```

- [ ] **Step 3: テストが失敗することを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_items.py -q`
Expected: FAIL（`ImportError: cannot import name 'items'`）

- [ ] **Step 4: 実装する**

`tools/workshop/items.py`:

```python
"""アイテムの定義（item.toml）・区画の位置・マニフェストの検査と書き出し。仕様: Spec 5 章。"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workshop.errors import WorkshopError

NAME_RE = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?")
NAME_MAX = 40
NAME_RULE = "^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ に合う 40 文字以内"
KINDS = ("prop", "gadget")
VERSION_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
ITEM_KEYS = ("display_name", "kind", "version", "shelf")
CLI_OWNED_SLOT_KEYS = ("key", "name", "parent", "position")
SHELF_COLUMNS = 8
SHELF_SPACING = 1.5
SHELF_HEIGHT = 1.0
SHELF_FRONT = 2.0
ROOT_MARKER = Path("templates") / "item" / "manifest.json"


@dataclass(frozen=True)
class Item:
    name: str
    display_name: str
    kind: str
    version: str
    shelf: int


def find_root(start: Path) -> Path:
    """start から親へたどり、templates/item/manifest.json を持つディレクトリを返す。"""
    for candidate in (start, *start.parents):
        if (candidate / ROOT_MARKER).is_file():
            return candidate
    raise WorkshopError(
        "reso-workshop のリポジトリの中で実行してください（templates/item/manifest.json が見つかりません）",
        exit_code=2,
    )


def is_valid_name(name: str) -> bool:
    return len(name) <= NAME_MAX and NAME_RE.fullmatch(name) is not None


def ownership_key(name: str) -> str:
    return f"workshop-{name}"


def root_slot_name(item: Item) -> str:
    return f"{item.display_name} v{item.version}"


def shelf_position(shelf: int) -> list[float]:
    index = shelf - 1
    return [
        (index % SHELF_COLUMNS) * SHELF_SPACING,
        SHELF_HEIGHT,
        SHELF_FRONT + (index // SHELF_COLUMNS) * SHELF_SPACING,
    ]


def item_dir(root: Path, name: str) -> Path:
    return root / "items" / name


def list_item_names(root: Path) -> list[str]:
    """items/ 直下のディレクトリ名を辞書順で返す。隠しディレクトリとファイルは数えない。"""
    directory = root / "items"
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_dir() and not p.name.startswith("."))


def state_path(name: str) -> str:
    return f".resoloop/state/{ownership_key(name)}.json"


def flux_state_path(name: str) -> str:
    return f".resoloop/flux-state/{ownership_key(name)}.json"


def load_item(root: Path, name: str) -> tuple[Item | None, list[str]]:
    """item.toml を読み、Spec 5 章の規則で検査する。誤りがあれば (None, 誤りの一覧) を返す。"""
    if not is_valid_name(name):
        return None, [f"items/{name}: 名前は {NAME_RULE} にしてください"]
    label = f"items/{name}/item.toml"
    try:
        data = tomllib.loads((item_dir(root, name) / "item.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{label}: ありません"]
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        return None, [f"{label}: 読めません（{error}）"]
    errors = [f"{label}: 知らない項目 {key} があります" for key in sorted(set(data) - set(ITEM_KEYS))]
    display_name = data.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        errors.append(f"{label}: display_name は空でない文字列にしてください")
    kind = data.get("kind")
    if kind not in KINDS:
        errors.append(f"{label}: kind は prop か gadget にしてください")
    version = data.get("version")
    if not isinstance(version, str) or VERSION_RE.fullmatch(version) is None:
        errors.append(f"{label}: version は X.Y.Z（それぞれ 0 以上の整数）にしてください")
    shelf = data.get("shelf")
    if isinstance(shelf, bool) or not isinstance(shelf, int) or shelf < 1:
        errors.append(f"{label}: shelf は 1 以上の整数にしてください")
    if errors:
        return None, errors
    return Item(name, display_name, kind, version, shelf), []


def validate_manifest(root: Path, name: str) -> list[str]:
    """manifest.json が読めて、CLI が決める項目を書いていないことを確かめる。"""
    label = f"items/{name}/manifest.json"
    try:
        data = json.loads((item_dir(root, name) / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{label}: ありません"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"{label}: 読めません（{error}）"]
    if not isinstance(data, dict):
        return [f"{label}: JSON のオブジェクトにしてください"]
    errors = []
    if "ownership" in data:
        errors.append(f"{label}: ownership は workshop が決めるので書かないでください")
    slot = data.get("slot", {})
    if not isinstance(slot, dict):
        errors.append(f"{label}: slot は JSON のオブジェクトにしてください")
    else:
        errors.extend(
            f"{label}: slot.{key} は workshop が決めるので書かないでください"
            for key in CLI_OWNED_SLOT_KEYS
            if key in slot
        )
    return errors


def render_manifest(root: Path, item: Item) -> Path:
    """CLI が決める値を入れたマニフェストを、相対パスの基準が変わらないよう同じディレクトリに書く。"""
    directory = item_dir(root, item.name)
    data = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    data["ownership"] = {"key": ownership_key(item.name)}
    data["slot"] = {
        **data.get("slot", {}),
        "key": "root",
        "name": root_slot_name(item),
        "parent": "Root",
        "position": shelf_position(item.shelf),
    }
    path = directory / "manifest.rendered.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def flux_manifest(name: str) -> dict[str, Any]:
    """gadget の flux/resoloop.flux.json。state は items/<名前>/flux からの相対パス。"""
    return {
        "schemaVersion": "1",
        "projectDirectory": ".",
        "parent": "$slot:root",
        "worldState": f"../../../{state_path(name)}",
        "deployState": f"../../../{flux_state_path(name)}",
        "modules": [{"name": "main", "source": "Main.pg", "module": "Main"}],
    }
```

- [ ] **Step 5: テストが通ることを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_items.py -q`
Expected: PASS（全件）

- [ ] **Step 6: コミットする**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add tools/workshop/items.py tests/conftest.py tests/test_items.py && git commit -q -m "feat: add item definitions, shelves and manifest rendering"
```

---

### Task 3: 反映と保存の記録（`ledger.py`）

**テストの要否:** 要る。TOML の書き出しと読み戻し、壊れた記録の検出、状態と保存の条件は分岐のあるロジック。

**Files:**
- Create: `tools/workshop/ledger.py`
- Test: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `workshop.errors.WorkshopError`
- Produces（`workshop.ledger`）:
  - `@dataclass(frozen=True) class DeployRecord: version: str; commit: str; dirty: bool; deployed_at: str; session: str; result: str; failed_step: str = ""; saved_at: str = ""`
  - 定数 `STATUS_NOT_DEPLOYED = "未反映"`、`STATUS_FAILED = "反映失敗"`、`STATUS_WAITING = "保存待ち"`、`STATUS_SAVED = "保存済み"`
  - `now_iso() -> str`、`toml_string(value: str) -> str`
  - `ledger_path(root: Path, name: str) -> Path`
  - `parse_records(text: str, label: str) -> list[DeployRecord]`、`dump_records(records: list[DeployRecord]) -> str`
  - `load_records(root: Path, name: str) -> list[DeployRecord]`、`write_records(root: Path, name: str, records: list[DeployRecord]) -> None`、`append_record(root: Path, name: str, record: DeployRecord) -> None`
  - `item_status(records: list[DeployRecord]) -> str`、`last_saved_at(records: list[DeployRecord]) -> str`
  - `saved_refusals(records: list[DeployRecord]) -> list[str]`、`mark_saved(root: Path, name: str, saved_at: str) -> DeployRecord`
  - 読めない・形が違う記録は `WorkshopError`（exit_code 1）。メッセージは label（`items/<名前>/deploys.toml`）で始まる

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ledger.py`:

```python
import tomllib
from dataclasses import replace

import pytest

from workshop import ledger
from workshop.errors import WorkshopError

PASSED = ledger.DeployRecord(
    version="1.0.0",
    commit="a" * 40,
    dirty=False,
    deployed_at="2026-10-12T21:00:00+09:00",
    session="ws://localhost:49691/",
    result="passed",
)
SAVED_OTHER = replace(PASSED, commit="b" * 40, saved_at="2026-10-11T10:00:00+09:00")


@pytest.fixture
def item_root(tmp_path):
    (tmp_path / "items" / "lamp").mkdir(parents=True)
    return tmp_path


def test_dump_and_parse_round_trip_with_awkward_strings():
    odd = 'quote " back \\ newline \n tab \t 日本語 del \x7f'
    records = [PASSED, replace(PASSED, session=odd, result="failed", failed_step="test")]
    text = ledger.dump_records(records)
    tomllib.loads(text)
    assert ledger.parse_records(text, "x") == records


def test_empty_ledger_has_no_records():
    assert ledger.parse_records(ledger.dump_records([]), "x") == []


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("[[deploy]\n", "読めません"),
        ('color = "red"\n', "知らない項目"),
        ("deploy = 1\n", "配列"),
        ('[[deploy]]\nversion = "1.0.0"\n', "がありません"),
        (
            '[[deploy]]\nversion = "1.0.0"\ncommit = ""\ndirty = "no"\ndeployed_at = ""\n'
            'session = ""\nresult = "passed"\n',
            "型",
        ),
        (
            '[[deploy]]\nversion = "1.0.0"\ncommit = ""\ndirty = false\ndeployed_at = ""\n'
            'session = ""\nresult = "ok"\n',
            "result",
        ),
        (
            '[[deploy]]\nversion = "1.0.0"\ncommit = ""\ndirty = false\ndeployed_at = ""\n'
            'session = ""\nresult = "passed"\nnote = "x"\n',
            "知らない項目",
        ),
    ],
)
def test_parse_rejects_broken_ledger(text, fragment):
    with pytest.raises(WorkshopError) as raised:
        ledger.parse_records(text, "items/lamp/deploys.toml")
    assert fragment in str(raised.value)
    assert str(raised.value).startswith("items/lamp/deploys.toml")


@pytest.mark.parametrize(
    "records, status",
    [
        ([], "未反映"),
        ([replace(PASSED, result="failed", failed_step="apply")], "反映失敗"),
        ([PASSED], "保存待ち"),
        ([replace(PASSED, saved_at="2026-10-12T21:10:00+09:00")], "保存済み"),
        ([replace(PASSED, saved_at="2026-10-12T21:10:00+09:00"), replace(PASSED, version="1.1.0")], "保存待ち"),
    ],
)
def test_item_status(records, status):
    assert ledger.item_status(records) == status


def test_last_saved_at_finds_latest_saved_record():
    records = [replace(PASSED, saved_at="T1"), replace(PASSED, saved_at="T2"), PASSED]
    assert ledger.last_saved_at(records) == "T2"
    assert ledger.last_saved_at([PASSED]) == ""


@pytest.mark.parametrize(
    "records, fragment",
    [
        ([], "反映の記録がありません"),
        ([replace(PASSED, result="failed", failed_step="test")], "失敗"),
        ([replace(PASSED, dirty=True)], "未コミット"),
        ([replace(PASSED, saved_at="T1")], "保存済み"),
        ([SAVED_OTHER, PASSED], "version を上げて"),
    ],
)
def test_saved_refusals(records, fragment):
    assert any(fragment in reason for reason in ledger.saved_refusals(records))


@pytest.mark.parametrize(
    "records",
    [
        [PASSED],
        [replace(PASSED, saved_at="T0"), PASSED],
        [SAVED_OTHER, replace(PASSED, version="1.1.0")],
    ],
)
def test_saved_accepts(records):
    assert ledger.saved_refusals(records) == []


def test_mark_saved_sets_saved_at_on_last_record(item_root):
    ledger.write_records(item_root, "lamp", [replace(PASSED, result="failed", failed_step="test"), PASSED])
    updated = ledger.mark_saved(item_root, "lamp", "2026-10-12T21:10:00+09:00")
    assert updated == replace(PASSED, saved_at="2026-10-12T21:10:00+09:00")
    records = ledger.load_records(item_root, "lamp")
    assert records[-1] == updated
    assert records[0].saved_at == ""


def test_mark_saved_refusal_leaves_file_unchanged(item_root):
    ledger.write_records(item_root, "lamp", [replace(PASSED, dirty=True)])
    before = ledger.ledger_path(item_root, "lamp").read_bytes()
    with pytest.raises(WorkshopError):
        ledger.mark_saved(item_root, "lamp", "2026-10-12T21:10:00+09:00")
    assert ledger.ledger_path(item_root, "lamp").read_bytes() == before


def test_append_record_keeps_existing_records(item_root):
    ledger.write_records(item_root, "lamp", [PASSED])
    ledger.append_record(item_root, "lamp", replace(PASSED, version="1.1.0"))
    assert [record.version for record in ledger.load_records(item_root, "lamp")] == ["1.0.0", "1.1.0"]


def test_load_records_reports_missing_file(item_root):
    with pytest.raises(WorkshopError) as raised:
        ledger.load_records(item_root, "lamp")
    assert str(raised.value) == "items/lamp/deploys.toml: ありません"
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_ledger.py -q`
Expected: FAIL（`ImportError: cannot import name 'ledger'`）

- [ ] **Step 3: 実装する**

`tools/workshop/ledger.py`:

```python
"""反映と保存の記録（items/<名前>/deploys.toml）。CLI だけが書く。仕様: Spec 5 章・6 章。"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, fields, replace
from datetime import datetime
from pathlib import Path

from workshop.errors import WorkshopError

HEADER = "# workshop が書く反映と保存の記録。手で編集しない。\n"
RESULTS = ("passed", "failed")
STATUS_NOT_DEPLOYED = "未反映"
STATUS_FAILED = "反映失敗"
STATUS_WAITING = "保存待ち"
STATUS_SAVED = "保存済み"


@dataclass(frozen=True)
class DeployRecord:
    version: str
    commit: str
    dirty: bool
    deployed_at: str
    session: str
    result: str
    failed_step: str = ""
    saved_at: str = ""


FIELD_TYPES = {field.name: (bool if field.name == "dirty" else str) for field in fields(DeployRecord)}
REQUIRED_FIELDS = ("version", "commit", "dirty", "deployed_at", "session", "result")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ledger_path(root: Path, name: str) -> Path:
    return root / "items" / name / "deploys.toml"


def toml_string(value: str) -> str:
    """TOML の基本文字列にする。JSON の文字列表記は TOML でも読めるが、DEL（U+007F）だけは逃がす。"""
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def parse_records(text: str, label: str) -> list[DeployRecord]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise WorkshopError(f"{label}: 読めません（{error}）") from error
    unknown = sorted(set(data) - {"deploy"})
    if unknown:
        raise WorkshopError(f"{label}: 知らない項目 {', '.join(unknown)} があります")
    entries = data.get("deploy", [])
    if not isinstance(entries, list):
        raise WorkshopError(f"{label}: deploy は [[deploy]] の配列にしてください")
    records = []
    for index, entry in enumerate(entries, start=1):
        where = f"{label}: {index} 件目"
        if not isinstance(entry, dict):
            raise WorkshopError(f"{where}が表ではありません")
        extra = sorted(set(entry) - set(FIELD_TYPES))
        if extra:
            raise WorkshopError(f"{where}に知らない項目 {', '.join(extra)} があります")
        missing = [key for key in REQUIRED_FIELDS if key not in entry]
        if missing:
            raise WorkshopError(f"{where}に {', '.join(missing)} がありません")
        for key, value in entry.items():
            if type(value) is not FIELD_TYPES[key]:
                raise WorkshopError(f"{where}の {key} の型が違います")
        if entry["result"] not in RESULTS:
            raise WorkshopError(f"{where}の result は passed か failed にしてください")
        records.append(DeployRecord(**entry))
    return records


def dump_records(records: list[DeployRecord]) -> str:
    parts = [HEADER]
    for record in records:
        parts.append("\n[[deploy]]\n")
        for field in fields(DeployRecord):
            value = getattr(record, field.name)
            text = ("true" if value else "false") if isinstance(value, bool) else toml_string(value)
            parts.append(f"{field.name} = {text}\n")
    return "".join(parts)


def load_records(root: Path, name: str) -> list[DeployRecord]:
    label = f"items/{name}/deploys.toml"
    try:
        text = ledger_path(root, name).read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise WorkshopError(f"{label}: ありません") from error
    except (OSError, UnicodeDecodeError) as error:
        raise WorkshopError(f"{label}: 読めません（{error}）") from error
    return parse_records(text, label)


def write_records(root: Path, name: str, records: list[DeployRecord]) -> None:
    """一時ファイルに書いてから置き換え、途中で止まっても書きかけの記録を残さない。"""
    path = ledger_path(root, name)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(dump_records(records), encoding="utf-8")
    temporary.replace(path)


def append_record(root: Path, name: str, record: DeployRecord) -> None:
    write_records(root, name, [*load_records(root, name), record])


def item_status(records: list[DeployRecord]) -> str:
    if not records:
        return STATUS_NOT_DEPLOYED
    last = records[-1]
    if last.result != "passed":
        return STATUS_FAILED
    return STATUS_SAVED if last.saved_at else STATUS_WAITING


def last_saved_at(records: list[DeployRecord]) -> str:
    for record in reversed(records):
        if record.saved_at:
            return record.saved_at
    return ""


def saved_refusals(records: list[DeployRecord]) -> list[str]:
    """保存を記録できない理由。インベントリの物とコミットを 1 対 1 にするための条件（Spec 6 章）。"""
    if not records:
        return ["反映の記録がありません。先に uv run workshop deploy を実行してください"]
    last = records[-1]
    reasons = []
    if last.result != "passed":
        reasons.append(f"最後の反映が失敗しています（{last.failed_step}）")
    if last.dirty:
        reasons.append("最後の反映は未コミットの変更を含んでいます。コミットしてから反映し直してください")
    if last.saved_at:
        reasons.append(f"最後の反映はすでに保存済みです（{last.saved_at}）")
    for other in records[:-1]:
        if other.version == last.version and other.saved_at and other.commit != last.commit:
            reasons.append(
                f"版 {last.version} は別のコミット {other.commit[:12]} で保存済みです。"
                "item.toml の version を上げてから反映し直してください"
            )
            break
    return reasons


def mark_saved(root: Path, name: str, saved_at: str) -> DeployRecord:
    records = load_records(root, name)
    reasons = saved_refusals(records)
    if reasons:
        raise WorkshopError("保存を記録できません: " + " / ".join(reasons))
    updated = replace(records[-1], saved_at=saved_at)
    write_records(root, name, [*records[:-1], updated])
    return updated
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_ledger.py -q`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add tools/workshop/ledger.py tests/test_ledger.py && git commit -q -m "feat: add deploy ledger and save conditions"
```

---

### Task 4: Git の状態（`gitstate.py`）

**テストの要否:** 要る。`git status -z` の解析、記録ファイルだけを除く判定、ファイルの大きさの境界は、実際の git リポジトリで確かめる挙動。

**Files:**
- Create: `tools/workshop/gitstate.py`
- Test: `tests/test_gitstate.py`

**Interfaces:**
- Consumes: `workshop.errors.WorkshopError`、fixture `git`・`git_repo`（Task 2 の `tests/conftest.py`）
- Produces（`workshop.gitstate`）:
  - `LARGE_FILE_LIMIT = 50 * 1024 * 1024`
  - `head_commit(root: Path) -> str`（コミットが無ければ `""`）
  - `changed_paths(root: Path) -> list[str]`
  - `is_dirty(root: Path) -> bool`（`items/<名前>/deploys.toml` だけの変更は数えない）
  - `large_files(root: Path, limit: int = LARGE_FILE_LIMIT) -> list[tuple[str, int]]`（追跡しているものと、無視されていない未追跡のもの。パスの辞書順）
  - git が失敗したら `WorkshopError`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_gitstate.py`:

```python
import os
from pathlib import Path

import pytest

from workshop import gitstate
from workshop.errors import WorkshopError


def write(root: Path, rel: str, text: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def committed(git_repo, git):
    write(git_repo, ".gitignore", "build/\n")
    write(git_repo, "items/lamp/item.toml")
    write(git_repo, "items/lamp/deploys.toml")
    git(git_repo, "add", "-A")
    git(git_repo, "commit", "-q", "-m", "init")
    return git_repo


def test_head_commit_in_empty_repository(git_repo):
    assert gitstate.head_commit(git_repo) == ""


def test_head_commit_after_commit(committed, git):
    assert gitstate.head_commit(committed) == git(committed, "rev-parse", "HEAD").strip()


def test_clean_tree_is_not_dirty(committed):
    assert gitstate.is_dirty(committed) is False


def test_ledger_changes_alone_are_not_dirty(committed):
    write(committed, "items/lamp/deploys.toml", "changed")
    write(committed, "items/new-item/deploys.toml", "new")
    assert gitstate.is_dirty(committed) is False


@pytest.mark.parametrize(
    "rel",
    [
        "items/lamp/item.toml",
        "items/lamp/sub/deploys.toml",
        "deploys.toml",
        "tools/日本語 名前.py",
        "build-notes.txt",
    ],
)
def test_other_changes_are_dirty(committed, rel):
    write(committed, rel, "changed")
    assert gitstate.is_dirty(committed) is True


def test_ignored_files_are_not_dirty(committed):
    write(committed, "build/lamp/model.json")
    assert gitstate.is_dirty(committed) is False


def test_staged_rename_is_dirty(committed, git):
    git(committed, "mv", "items/lamp/item.toml", "items/lamp/renamed.toml")
    assert gitstate.is_dirty(committed) is True
    assert set(gitstate.changed_paths(committed)) == {"items/lamp/renamed.toml", "items/lamp/item.toml"}


def test_outside_git_repository_is_an_error(tmp_path):
    with pytest.raises(WorkshopError):
        gitstate.is_dirty(tmp_path)


def test_large_files_reports_tracked_and_untracked_files_over_limit(committed, git):
    write(committed, "big-tracked.bin", "x" * 11)
    git(committed, "add", "big-tracked.bin")
    write(committed, "big-untracked.bin", "x" * 11)
    write(committed, "small.bin", "x" * 10)
    write(committed, "build/ignored.bin", "x" * 11)
    os.symlink("big-untracked.bin", committed / "link.bin")
    assert gitstate.large_files(committed, limit=10) == [("big-tracked.bin", 11), ("big-untracked.bin", 11)]


def test_large_files_default_limit_is_strictly_over_50_mib(committed):
    for rel, size in (("exact.bin", 50 * 1024 * 1024), ("over.bin", 50 * 1024 * 1024 + 1)):
        with open(committed / rel, "wb") as handle:
            handle.truncate(size)
    assert gitstate.large_files(committed) == [("over.bin", 50 * 1024 * 1024 + 1)]


def test_large_files_skips_deleted_tracked_file(committed):
    (committed / "items" / "lamp" / "item.toml").unlink()
    paths = [path for path, _ in gitstate.large_files(committed, limit=0)]
    assert "items/lamp/item.toml" not in paths
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_gitstate.py -q`
Expected: FAIL（`ImportError: cannot import name 'gitstate'`）

- [ ] **Step 3: 実装する**

`tools/workshop/gitstate.py`:

```python
"""Git の状態の読み取り: 今のコミット・未コミットの変更・大きなファイル。仕様: Spec 6 章・7 章。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from workshop.errors import WorkshopError

LEDGER_RE = re.compile(r"items/[^/]+/deploys\.toml")
LARGE_FILE_LIMIT = 50 * 1024 * 1024


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def head_commit(root: Path) -> str:
    result = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else ""


def changed_paths(root: Path) -> list[str]:
    """git status に出るパス（無視されていない未追跡のファイルと、名前の変更の前後を含む）。"""
    result = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if result.returncode != 0:
        raise WorkshopError(f"git status に失敗しました: {result.stderr.strip()}")
    tokens = result.stdout.split("\0")
    paths = []
    index = 0
    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in status or "C" in status:
            # -z では、名前の変更・複写の元のパスが次の項目として続く
            paths.append(tokens[index])
            index += 1
    return paths


def is_dirty(root: Path) -> bool:
    """items/<名前>/deploys.toml 以外に変更があるか。記録を書いただけでは未コミット扱いにしない。"""
    return any(LEDGER_RE.fullmatch(path) is None for path in changed_paths(root))


def large_files(root: Path, limit: int = LARGE_FILE_LIMIT) -> list[tuple[str, int]]:
    """limit バイトを超えるファイル。追跡しているものと、無視されていない未追跡のものを調べる。"""
    result = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if result.returncode != 0:
        raise WorkshopError(f"git ls-files に失敗しました: {result.stderr.strip()}")
    found = []
    for path in sorted(set(filter(None, result.stdout.split("\0")))):
        full = root / path
        if full.is_symlink() or not full.is_file():
            continue
        size = full.stat().st_size
        if size > limit:
            found.append((path, size))
    return found
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_gitstate.py -q`
Expected: PASS（全件）

- [ ] **Step 5: コミットする**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add tools/workshop/gitstate.py tests/test_gitstate.py && git commit -q -m "feat: read commit, uncommitted changes and large files from git"
```

---

### Task 5: `new`・`list`・`check`・`saved`（`scaffold.py`・`checks.py`・`cli.py`）

**テストの要否:** 要る。雛形からの作成、区画の割り当て、検査の集約、終了コード、cwd からのルートの発見は、CLI を実行して確かめる挙動。

**Files:**
- Create: `tools/workshop/scaffold.py`、`tools/workshop/checks.py`、`tools/workshop/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `workshop.items`（Task 2）、`workshop.ledger`（Task 3）、`workshop.gitstate`（Task 4）、fixture `workshop_root`
- Produces:
  - `workshop.scaffold.INITIAL_VERSION = "0.1.0"`、`used_shelves(root: Path) -> set[int]`、`next_free_shelf(used: set[int]) -> int`、`create_item(root: Path, name: str, kind: str, display_name: str) -> Path`
  - `workshop.checks.check_items(root: Path, names: list[str]) -> list[str]`（区画の重なりと大きなファイルはリポジトリ全体で調べる）
  - `workshop.cli.build_parser() -> argparse.ArgumentParser`、`workshop.cli.require_item(root: Path, name: str) -> None`、`workshop.cli.COMMANDS: dict[str, Callable[[Path, argparse.Namespace], int]]`、`workshop.cli.main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cli.py`:

```python
import json
import shutil
from dataclasses import replace

import pytest

from workshop import cli, items, ledger

PASSED = ledger.DeployRecord(
    version="0.1.0",
    commit="a" * 40,
    dirty=False,
    deployed_at="2026-10-12T21:00:00+09:00",
    session="ws://localhost:49691/",
    result="passed",
)


@pytest.fixture
def in_root(workshop_root, monkeypatch):
    monkeypatch.chdir(workshop_root)
    return workshop_root


def new(name, kind="prop", display="Lamp"):
    return cli.main(["new", name, "--kind", kind, "--display-name", display])


def test_new_prop_creates_item_from_template(in_root):
    assert new("desk-lamp", display="Desk Lamp") == 0
    item, errors = items.load_item(in_root, "desk-lamp")
    assert errors == []
    assert item == items.Item("desk-lamp", "Desk Lamp", "prop", "0.1.0", 1)
    directory = in_root / "items" / "desk-lamp"
    template = in_root / "templates" / "item" / "manifest.json"
    assert (directory / "manifest.json").read_bytes() == template.read_bytes()
    assert ledger.load_records(in_root, "desk-lamp") == []
    assert not (directory / "flux").exists()


def test_new_gadget_adds_flux_project(in_root):
    assert new("switch", kind="gadget") == 0
    flux = in_root / "items" / "switch" / "flux"
    assert (flux / "Main.pg").is_file()
    assert (flux / ".gitignore").is_file()
    assert json.loads((flux / "resoloop.flux.json").read_text(encoding="utf-8")) == items.flux_manifest("switch")


def test_new_takes_smallest_free_shelf(in_root):
    for name in ("a", "b", "c"):
        assert new(name) == 0
    shutil.rmtree(in_root / "items" / "b")
    assert new("d") == 0
    assert items.load_item(in_root, "d")[0].shelf == 2


@pytest.mark.parametrize("name", ["Desk", "desk_lamp", "lamp-", "a" * 41])
def test_new_rejects_invalid_name(in_root, name):
    assert new(name) == 2
    assert not (in_root / "items" / name).exists()


def test_new_rejects_existing_item(in_root):
    assert new("lamp") == 0
    before = (in_root / "items" / "lamp" / "item.toml").read_bytes()
    assert new("lamp", display="Other") == 2
    assert (in_root / "items" / "lamp" / "item.toml").read_bytes() == before


def test_new_rejects_unknown_kind(in_root):
    with pytest.raises(SystemExit) as raised:
        new("lamp", kind="avatar")
    assert raised.value.code == 2


def test_new_keeps_awkward_display_name(in_root):
    display = 'Lamp "Mk.2" \\ 卓上ライト'
    assert new("lamp", display=display) == 0
    assert items.load_item(in_root, "lamp")[0].display_name == display


def test_check_passes_for_fresh_items(in_root, capsys):
    assert new("lamp") == 0
    assert new("switch", kind="gadget") == 0
    capsys.readouterr()
    assert cli.main(["check"]) == 0
    assert "OK: 2 件のアイテム" in capsys.readouterr().out


def test_check_reports_every_problem(in_root, capsys):
    for name, kind in (("a", "prop"), ("b", "prop"), ("g", "gadget")):
        assert new(name, kind=kind) == 0
    (in_root / "items" / "b" / "item.toml").write_text(
        'display_name = "B"\nkind = "prop"\nversion = "0.1.0"\nshelf = 1\n', encoding="utf-8"
    )
    shutil.rmtree(in_root / "items" / "g" / "flux")
    (in_root / "items" / "empty").mkdir()
    (in_root / "items" / "Bad_Name").mkdir()
    (in_root / "items" / "a" / "deploys.toml").write_text("[[deploy]\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["check"]) == 1
    err = capsys.readouterr().err
    assert "区画 1" in err
    assert "items/g/flux/resoloop.flux.json" in err
    assert "items/empty/item.toml: ありません" in err
    assert "items/Bad_Name:" in err
    assert "items/a/deploys.toml: 読めません" in err
    assert "Traceback" not in err


def test_check_unknown_item_is_usage_error(in_root):
    assert cli.main(["check", "nope"]) == 2


def test_list_without_items(in_root, capsys):
    assert cli.main(["list"]) == 0
    assert "アイテムはまだありません" in capsys.readouterr().out


def test_list_shows_status_per_item(in_root, capsys):
    for name in ("a", "b", "c"):
        assert new(name) == 0
    ledger.write_records(in_root, "b", [PASSED])
    ledger.write_records(in_root, "c", [replace(PASSED, saved_at="2026-10-12T21:10:00+09:00")])
    capsys.readouterr()
    assert cli.main(["list"]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == [
        "a\tprop\t0.1.0\t未反映\t-",
        "b\tprop\t0.1.0\t保存待ち\t-",
        "c\tprop\t0.1.0\t保存済み\t2026-10-12T21:10:00+09:00",
    ]


def test_list_reports_broken_ledger_without_traceback(in_root, capsys):
    assert new("a") == 0
    (in_root / "items" / "a" / "deploys.toml").write_text("[[deploy]\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["list"]) == 1
    captured = capsys.readouterr()
    assert "a\t-\t-\t検査エラー\t-" in captured.out
    assert "Traceback" not in captured.err


def test_saved_refuses_without_records(in_root, capsys):
    assert new("a") == 0
    assert cli.main(["saved", "a"]) == 1
    assert "反映の記録がありません" in capsys.readouterr().err


def test_saved_records_time_on_last_record(in_root):
    assert new("a") == 0
    ledger.write_records(in_root, "a", [PASSED])
    assert cli.main(["saved", "a"]) == 0
    assert ledger.load_records(in_root, "a")[-1].saved_at != ""


def test_saved_with_broken_ledger_exits_1(in_root, capsys):
    assert new("a") == 0
    (in_root / "items" / "a" / "deploys.toml").write_text("[[deploy]\n", encoding="utf-8")
    assert cli.main(["saved", "a"]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_saved_unknown_item_is_usage_error(in_root):
    assert cli.main(["saved", "nope"]) == 2


def test_main_works_from_item_directory(in_root, monkeypatch):
    assert new("a") == 0
    monkeypatch.chdir(in_root / "items" / "a")
    assert cli.main(["list"]) == 0


def test_main_outside_repository_is_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["list"]) == 2
    assert "reso-workshop" in capsys.readouterr().err
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_cli.py -q`
Expected: FAIL（`ImportError: cannot import name 'cli'`）

- [ ] **Step 3: 実装する**

`tools/workshop/scaffold.py`:

```python
"""雛形からアイテムを作る（workshop new）。仕様: Spec 6 章。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from workshop import items, ledger
from workshop.errors import WorkshopError

INITIAL_VERSION = "0.1.0"


def used_shelves(root: Path) -> set[int]:
    shelves = set()
    for name in items.list_item_names(root):
        item, _ = items.load_item(root, name)
        if item is not None:
            shelves.add(item.shelf)
    return shelves


def next_free_shelf(used: set[int]) -> int:
    shelf = 1
    while shelf in used:
        shelf += 1
    return shelf


def item_toml(display_name: str, kind: str, version: str, shelf: int) -> str:
    return (
        f"display_name = {ledger.toml_string(display_name)}\n"
        f'kind = "{kind}"\n'
        f'version = "{version}"\n'
        f"shelf = {shelf}\n"
    )


def create_item(root: Path, name: str, kind: str, display_name: str) -> Path:
    if not items.is_valid_name(name):
        raise WorkshopError(f"名前 {name} は {items.NAME_RULE} にしてください", exit_code=2)
    if kind not in items.KINDS:
        raise WorkshopError("kind は prop か gadget にしてください", exit_code=2)
    if not display_name.strip():
        raise WorkshopError("表示名を空にはできません", exit_code=2)
    directory = items.item_dir(root, name)
    if directory.exists() or directory.is_symlink():
        raise WorkshopError(f"items/{name} はすでにあります", exit_code=2)
    template = root / "templates" / "item"
    shelf = next_free_shelf(used_shelves(root))
    directory.mkdir(parents=True)
    shutil.copy2(template / "manifest.json", directory / "manifest.json")
    (directory / "item.toml").write_text(item_toml(display_name, kind, INITIAL_VERSION, shelf), encoding="utf-8")
    ledger.write_records(root, name, [])
    if kind == "gadget":
        shutil.copytree(template / "flux", directory / "flux")
        (directory / "flux" / "resoloop.flux.json").write_text(
            json.dumps(items.flux_manifest(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return directory
```

`tools/workshop/checks.py`:

```python
"""アイテムの検査（workshop check と、deploy の最初の段階）。仕様: Spec 6 章。"""

from __future__ import annotations

from pathlib import Path

from workshop import gitstate, items, ledger
from workshop.errors import WorkshopError


def check_items(root: Path, names: list[str]) -> list[str]:
    """names の各アイテムを検査する。区画の重なりと大きなファイルはリポジトリ全体で調べる。"""
    shelves: dict[int, list[str]] = {}
    for name in items.list_item_names(root):
        item, _ = items.load_item(root, name)
        if item is not None:
            shelves.setdefault(item.shelf, []).append(name)
    errors: list[str] = []
    for name in names:
        item, item_errors = items.load_item(root, name)
        errors.extend(item_errors)
        if not items.is_valid_name(name):
            continue
        errors.extend(items.validate_manifest(root, name))
        try:
            ledger.load_records(root, name)
        except WorkshopError as error:
            errors.append(str(error))
        if item is None:
            continue
        flux = items.item_dir(root, name) / "flux" / "resoloop.flux.json"
        if item.kind == "gadget" and not flux.is_file():
            errors.append(f"items/{name}/flux/resoloop.flux.json: gadget には必要です")
        others = [other for other in shelves.get(item.shelf, []) if other != name]
        if others:
            errors.append(f"items/{name}/item.toml: 区画 {item.shelf} が {', '.join(others)} と重なっています")
    for path, size in gitstate.large_files(root):
        errors.append(f"{path}: {size / 1024 / 1024:.1f} MiB あり、50 MiB を超えています")
    return errors
```

`tools/workshop/cli.py`:

```python
"""workshop の CLI（uv run workshop）。仕様: Spec 6 章。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from workshop import checks, items, ledger, scaffold
from workshop.errors import WorkshopError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workshop", description="Resonite のアイテムを作り、工房へ反映して管理する")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="雛形からアイテムを作る")
    new.add_argument("name")
    new.add_argument("--kind", required=True, choices=items.KINDS)
    new.add_argument("--display-name", required=True)
    commands.add_parser("list", help="全アイテムの状態を表示する")
    check = commands.add_parser("check", help="アイテムを検査する（名前を省くと全部）")
    check.add_argument("names", nargs="*")
    saved = commands.add_parser("saved", help="インベントリへの保存を記録する")
    saved.add_argument("name")
    return parser


def require_item(root: Path, name: str) -> None:
    if not items.is_valid_name(name) or not items.item_dir(root, name).is_dir():
        raise WorkshopError(f"アイテム {name} はありません", exit_code=2)


def cmd_new(root: Path, args: argparse.Namespace) -> int:
    directory = scaffold.create_item(root, args.name, args.kind, args.display_name)
    print(f"作成しました: {directory.relative_to(root).as_posix()}")
    return 0


def cmd_list(root: Path, args: argparse.Namespace) -> int:
    names = items.list_item_names(root)
    if not names:
        print("アイテムはまだありません")
        return 0
    print("名前\t種類\t版\t状態\t最後の保存")
    broken = False
    for name in names:
        item, _ = items.load_item(root, name)
        try:
            records = ledger.load_records(root, name)
        except WorkshopError:
            records = None
        if item is None or records is None:
            print(f"{name}\t-\t-\t検査エラー\t-")
            broken = True
            continue
        saved_at = ledger.last_saved_at(records) or "-"
        print(f"{name}\t{item.kind}\t{item.version}\t{ledger.item_status(records)}\t{saved_at}")
    if broken:
        print("検査エラーのアイテムがあります。uv run workshop check で確かめてください", file=sys.stderr)
    return 1 if broken else 0


def cmd_check(root: Path, args: argparse.Namespace) -> int:
    for name in args.names:
        require_item(root, name)
    names = args.names or items.list_item_names(root)
    errors = checks.check_items(root, names)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {len(names)} 件のアイテム")
    return 0


def cmd_saved(root: Path, args: argparse.Namespace) -> int:
    require_item(root, args.name)
    record = ledger.mark_saved(root, args.name, ledger.now_iso())
    print(f"保存済みとして記録しました: {args.name} v{record.version}（コミット {record.commit[:12]}）")
    print(f"items/{args.name}/deploys.toml をコミットしてください")
    return 0


COMMANDS: dict[str, Callable[[Path, argparse.Namespace], int]] = {
    "new": cmd_new,
    "list": cmd_list,
    "check": cmd_check,
    "saved": cmd_saved,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = items.find_root(Path.cwd())
        return COMMANDS[args.command](root, args)
    except WorkshopError as error:
        print(f"エラー: {error}", file=sys.stderr)
        return error.exit_code
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest -q`
Expected: PASS（Task 2〜5 の全件）

- [ ] **Step 5: 実際のコマンドで確かめる**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && uv run workshop --help && uv run workshop list && uv run workshop check; echo "exit=$?"
```

Expected: ヘルプにサブコマンド `new`・`list`・`check`・`saved` が出る。`アイテムはまだありません`、`OK: 0 件のアイテム`、`exit=0`。

- [ ] **Step 6: コミットする**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add tools/workshop/scaffold.py tools/workshop/checks.py tools/workshop/cli.py tests/test_cli.py && git commit -q -m "feat: add workshop new, list, check and saved commands"
```

---

### Task 6: 工房への反映（`deploy.py`・`workshop deploy`）

**テストの要否:** 要る。段階の順序、失敗したときの停止と記録の有無、resoloop への引数は、偽の resoloop で実行して確かめる挙動。

**Files:**
- Create: `tools/workshop/deploy.py`
- Modify: `tools/workshop/cli.py`（`deploy` サブコマンドを足す）
- Test: `tests/test_deploy.py`

**Interfaces:**
- Consumes: `checks.check_items`、`gitstate.head_commit`・`gitstate.is_dirty`、`items.load_item`・`items.render_manifest`・`items.state_path`、`ledger.DeployRecord`・`ledger.append_record`・`ledger.now_iso`、`scaffold.create_item`（テスト）、`cli.require_item`・`cli.COMMANDS`・`cli.build_parser`
- Produces（`workshop.deploy`）:
  - `Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]`、`run_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]`
  - `class StepFailed(Exception)`（属性 `step: str`）
  - `deploy(root: Path, name: str, url: str, prune: bool, *, run: Runner | None = None, now: Callable[[], str] = ledger.now_iso) -> int`（`run` が None なら呼び出し時の `run_command` を使う）
  - `failed_step` の名前: `check`・`pytest`・`build`・`render`・`validate`・`flux-validate`・`diff`（記録しない）、`apply`・`flux-deploy`・`test`・`item-audit`・`rediff`（記録する）
- 補足: アイテムの pytest と `build.py` は `sys.executable`（`uv run workshop` が使っている `.venv` の Python）で実行する。Spec 7 章の `uv run python items/<名前>/build.py --out build/<名前>` と同じ環境で、uv を入れ子に呼ばずに済む

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_deploy.py`:

```python
import json
import subprocess
import sys

import pytest

from workshop import cli, deploy, ledger, scaffold

URL = "ws://localhost:49691/"
NOW = "2026-10-12T21:00:00+09:00"
STATE = ".resoloop/state/workshop-lamp.json"


def done(returncode=0, stdout='{"ok":true,"data":{}}', stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def diff_output(operations=()):
    operations = list(operations)
    data = {
        "operations": operations,
        "changes": [op for op in operations if op["action"] != "no-op"],
        "creates": sum(op["action"] == "create" for op in operations),
        "updates": sum(op["action"] == "update" for op in operations),
        "deletes": sum(op["action"] == "delete" for op in operations),
    }
    return done(stdout=json.dumps({"ok": True, "data": data}))


def step_of(args):
    if args[0] == sys.executable:
        return "pytest" if args[1:3] == ["-m", "pytest"] else "build"
    if args[1] in ("flux", "item"):
        return f"{args[1]} {args[2]}"
    return args[1]


class FakeRunner:
    """呼び出しを書き残し、段階ごとに決めた結果を返す。最後の 1 件は何度でも返す。"""

    def __init__(self, responses=None):
        self.responses = {step: list(results) for step, results in (responses or {}).items()}
        self.calls = []

    def __call__(self, args, cwd):
        self.calls.append(list(args))
        step = step_of(args)
        queue = self.responses.get(step)
        if queue:
            return queue.pop(0) if len(queue) > 1 else queue[0]
        return diff_output() if step == "diff" else done()

    def steps(self):
        return [step_of(args) for args in self.calls]


def commit_item(root, git, kind="prop"):
    scaffold.create_item(root, "lamp", kind, "Lamp")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "add lamp")
    return root


@pytest.fixture
def lamp(workshop_root, git):
    return commit_item(workshop_root, git)


def run_deploy(root, runner, prune=False):
    return deploy.deploy(root, "lamp", URL, prune, run=runner, now=lambda: NOW)


def test_prop_deploy_runs_steps_in_order_and_records_pass(lamp, git):
    runner = FakeRunner()
    assert run_deploy(lamp, runner) == 0
    assert runner.steps() == ["validate", "diff", "apply", "test", "item audit", "diff"]
    head = git(lamp, "rev-parse", "HEAD").strip()
    assert ledger.load_records(lamp, "lamp") == [
        ledger.DeployRecord(version="0.1.0", commit=head, dirty=False, deployed_at=NOW, session=URL, result="passed")
    ]
    assert (lamp / "items" / "lamp" / "manifest.rendered.json").is_file()


def test_live_commands_target_item_state_and_session(lamp):
    runner = FakeRunner()
    assert run_deploy(lamp, runner) == 0
    validate, *live = runner.calls
    assert validate == ["resoloop", "validate", "items/lamp/manifest.rendered.json", "--json"]
    for args in live:
        assert args[args.index("--state") + 1] == STATE
        assert args[args.index("--url") + 1] == URL
    assert live[3][:5] == ["resoloop", "item", "audit", "$slot:root", "--strict"]


def test_gadget_adds_flux_steps(workshop_root, git):
    root = commit_item(workshop_root, git, kind="gadget")
    runner = FakeRunner()
    assert run_deploy(root, runner) == 0
    assert runner.steps() == [
        "validate",
        "flux validate-manifest",
        "diff",
        "apply",
        "flux deploy-manifest",
        "test",
        "item audit",
        "diff",
    ]


def test_item_tests_and_build_run_before_validate(lamp):
    (lamp / "items" / "lamp" / "tests").mkdir()
    (lamp / "items" / "lamp" / "build.py").write_text("", encoding="utf-8")
    runner = FakeRunner({"pytest": [done(returncode=5)]})
    assert run_deploy(lamp, runner) == 0
    assert runner.steps()[:3] == ["pytest", "build", "validate"]
    assert runner.calls[0][1:] == ["-m", "pytest", "items/lamp/tests"]
    assert runner.calls[1][1:] == ["items/lamp/build.py", "--out", "build/lamp"]
    assert (lamp / "build" / "lamp").is_dir()


def test_failing_item_tests_stop_before_resoloop(lamp):
    (lamp / "items" / "lamp" / "tests").mkdir()
    runner = FakeRunner({"pytest": [done(returncode=1, stdout="1 failed")]})
    assert run_deploy(lamp, runner) == 1
    assert runner.steps() == ["pytest"]
    assert ledger.load_records(lamp, "lamp") == []


def test_check_failure_stops_without_any_call(lamp):
    (lamp / "items" / "lamp" / "item.toml").write_text('kind = "prop"\n', encoding="utf-8")
    runner = FakeRunner()
    assert run_deploy(lamp, runner) == 1
    assert runner.calls == []
    assert ledger.load_records(lamp, "lamp") == []


def test_deletes_without_prune_stop_before_apply(lamp, capsys):
    delete = {"action": "delete", "kind": "slot", "path": "Root/Lamp v0.1.0/Old"}
    runner = FakeRunner({"diff": [diff_output([delete])]})
    assert run_deploy(lamp, runner) == 1
    assert "apply" not in runner.steps()
    assert "Root/Lamp v0.1.0/Old" in capsys.readouterr().err
    assert ledger.load_records(lamp, "lamp") == []


def test_prune_passes_flags_to_apply(lamp):
    delete = {"action": "delete", "kind": "slot", "path": "Root/Lamp v0.1.0/Old"}
    runner = FakeRunner({"diff": [diff_output([delete]), diff_output()]})
    assert run_deploy(lamp, runner, prune=True) == 0
    apply = runner.calls[runner.steps().index("apply")]
    assert "--prune" in apply and "--yes" in apply


@pytest.mark.parametrize(
    "result",
    [
        done(returncode=4, stdout="", stderr='{"ok":false,"error":{"code":"CONNECTION_FAILED"}}'),
        done(stdout="not json"),
        done(stdout='{"ok":true,"data":{"changes":null,"operations":[]}}'),
    ],
)
def test_unusable_diff_stops_without_record(lamp, result):
    runner = FakeRunner({"diff": [result]})
    assert run_deploy(lamp, runner) == 1
    assert runner.steps() == ["validate", "diff"]
    assert ledger.load_records(lamp, "lamp") == []


def test_live_failure_is_recorded(lamp):
    runner = FakeRunner({"test": [done(returncode=6, stderr="APPLY_TEST_FAILED")]})
    assert run_deploy(lamp, runner) == 1
    assert "item audit" not in runner.steps()
    [record] = ledger.load_records(lamp, "lamp")
    assert (record.result, record.failed_step) == ("failed", "test")


def test_remaining_changes_after_apply_fail_rediff(lamp):
    update = {"action": "update", "kind": "component", "path": "Root/Lamp v0.1.0"}
    runner = FakeRunner({"diff": [diff_output(), diff_output([update])]})
    assert run_deploy(lamp, runner) == 1
    [record] = ledger.load_records(lamp, "lamp")
    assert (record.result, record.failed_step) == ("failed", "rediff")


def test_uncommitted_change_is_recorded_as_dirty(lamp):
    manifest = lamp / "items" / "lamp" / "manifest.json"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    runner = FakeRunner()
    assert run_deploy(lamp, runner) == 0
    assert ledger.load_records(lamp, "lamp")[0].dirty is True


def test_missing_executable_is_a_step_failure(lamp):
    def runner(args, cwd):
        raise FileNotFoundError(args[0])

    assert run_deploy(lamp, runner) == 1
    assert ledger.load_records(lamp, "lamp") == []


def test_cli_deploy_uses_run_command(lamp, monkeypatch):
    runner = FakeRunner()
    monkeypatch.setattr(deploy, "run_command", runner)
    monkeypatch.chdir(lamp)
    assert cli.main(["deploy", "lamp", "--url", URL]) == 0
    assert runner.steps() == ["validate", "diff", "apply", "test", "item audit", "diff"]


def test_cli_deploy_unknown_item_is_usage_error(lamp, monkeypatch):
    monkeypatch.chdir(lamp)
    assert cli.main(["deploy", "nope", "--url", URL]) == 2
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest tests/test_deploy.py -q`
Expected: FAIL（`ImportError: cannot import name 'deploy'`）

- [ ] **Step 3: `deploy.py` を実装する**

`tools/workshop/deploy.py`:

```python
"""工房への反映（workshop deploy）。仕様: Spec 7 章。"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from workshop import checks, gitstate, items, ledger

Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]
PYTEST_NO_TESTS = 5  # pytest の終了コード: 集めたテストが 0 件
DETAIL_LIMIT = 2000  # 失敗の表示に使う出力（末尾）の文字数


def run_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


class StepFailed(Exception):
    """deploy の段階の失敗。step は deploys.toml の failed_step に入る名前。"""

    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step


def call(run: Runner, root: Path, step: str, args: list[str], ok_codes: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    try:
        result = run(args, root)
    except OSError as error:
        raise StepFailed(step, f"{args[0]} を実行できません（{error}）") from error
    if result.returncode not in ok_codes:
        detail = (result.stderr.strip() or result.stdout.strip())[-DETAIL_LIMIT:]
        raise StepFailed(step, f"終了コード {result.returncode}: {detail}")
    return result


def read_diff(result: subprocess.CompletedProcess[str], step: str) -> dict[str, Any]:
    try:
        data = json.loads(result.stdout)["data"]
        if not isinstance(data["changes"], list) or not isinstance(data["operations"], list):
            raise TypeError("changes・operations が配列ではありません")
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise StepFailed(step, f"diff の出力を読めません（{error}）") from error
    return data


def delete_paths(data: dict[str, Any]) -> list[str]:
    return [
        str(operation.get("path", "?"))
        for operation in data["operations"]
        if isinstance(operation, dict) and operation.get("action") == "delete"
    ]


def live_args(command: list[str], state: str, url: str) -> list[str]:
    return ["resoloop", *command, "--state", state, "--url", url, "--json"]


def prepare(run: Runner, root: Path, name: str) -> tuple[items.Item, str]:
    """1. 準備（オフライン）。アイテムと manifest.rendered.json の相対パスを返す。"""
    errors = checks.check_items(root, [name])
    item, item_errors = items.load_item(root, name)
    if errors or item is None:
        raise StepFailed("check", " / ".join(errors or item_errors))
    rel = f"items/{name}"
    directory = root / rel
    if (directory / "tests").is_dir():
        call(run, root, "pytest", [sys.executable, "-m", "pytest", f"{rel}/tests"], ok_codes=(0, PYTEST_NO_TESTS))
    if (directory / "build.py").is_file():
        (root / "build" / name).mkdir(parents=True, exist_ok=True)
        call(run, root, "build", [sys.executable, f"{rel}/build.py", "--out", f"build/{name}"])
    try:
        items.render_manifest(root, item)
    except (OSError, ValueError) as error:
        raise StepFailed("render", str(error)) from error
    rendered = f"{rel}/manifest.rendered.json"
    call(run, root, "validate", ["resoloop", "validate", rendered, "--json"])
    if item.kind == "gadget":
        call(run, root, "flux-validate", ["resoloop", "flux", "validate-manifest", f"{rel}/flux/resoloop.flux.json", "--json"])
    return item, rendered


def deploy(
    root: Path,
    name: str,
    url: str,
    prune: bool,
    *,
    run: Runner | None = None,
    now: Callable[[], str] = ledger.now_iso,
) -> int:
    run = run or run_command
    commit = gitstate.head_commit(root)
    dirty = commit == "" or gitstate.is_dirty(root)
    state = items.state_path(name)
    if dirty:
        print("注意: 未コミットの変更があります。この反映は workshop saved で保存の記録に使えません", file=sys.stderr)
    try:
        print("[1/5] 準備（オフラインの検査）")
        item, rendered = prepare(run, root, name)
        print("[2/5] 差分の確認")
        data = read_diff(call(run, root, "diff", live_args(["diff", rendered], state, url)), "diff")
        deletes = delete_paths(data)
        print(f"作成 {data.get('creates', '?')}・更新 {data.get('updates', '?')}・削除 {len(deletes)}")
        if deletes and not prune:
            for path in deletes:
                print(f"  削除: {path}", file=sys.stderr)
            raise StepFailed("diff", "削除が含まれています。内容を確かめてから --prune を付けて実行し直してください")
    except StepFailed as failure:
        print(f"失敗: {failure}", file=sys.stderr)
        print("工房は変えていないので、記録しません", file=sys.stderr)
        return 1

    deployed_at = now()

    def record(result: str, failed_step: str = "") -> None:
        ledger.append_record(
            root,
            name,
            ledger.DeployRecord(
                version=item.version,
                commit=commit,
                dirty=dirty,
                deployed_at=deployed_at,
                session=url,
                result=result,
                failed_step=failed_step,
            ),
        )

    try:
        print("[3/5] 反映")
        apply_command = ["apply", rendered, *(["--prune", "--yes"] if prune else [])]
        call(run, root, "apply", live_args(apply_command, state, url))
        if item.kind == "gadget":
            flux = f"items/{name}/flux/resoloop.flux.json"
            call(run, root, "flux-deploy", live_args(["flux", "deploy-manifest", flux], state, url))
        print("[4/5] 実機での検査")
        call(run, root, "test", live_args(["test", rendered], state, url))
        call(run, root, "item-audit", live_args(["item", "audit", "$slot:root", "--strict"], state, url))
        after = read_diff(call(run, root, "rediff", live_args(["diff", rendered], state, url)), "rediff")
        if after["changes"]:
            raise StepFailed("rediff", f"反映後も差分が {len(after['changes'])} 件残っています")
    except StepFailed as failure:
        record("failed", failure.step)
        print(f"失敗: {failure}", file=sys.stderr)
        print(f"[5/5] 失敗として items/{name}/deploys.toml に記録しました", file=sys.stderr)
        return 1
    record("passed")
    print(f"[5/5] items/{name}/deploys.toml に記録しました")
    print(f"Resonite の中でインベントリに保存したら、uv run workshop saved {name} を実行してください")
    return 0
```

- [ ] **Step 4: `cli.py` に `deploy` を足す**

`tools/workshop/cli.py` の import を次にする:

```python
from workshop import checks, deploy, items, ledger, scaffold
```

`build_parser()` の `check` の追加の後、`saved` の追加の前に入れる:

```python
    deploy_parser = commands.add_parser("deploy", help="工房へ反映して検査し、記録する")
    deploy_parser.add_argument("name")
    deploy_parser.add_argument("--url", required=True, help="工房のセッションの URL（例: ws://localhost:49691/）")
    deploy_parser.add_argument("--prune", action="store_true", help="diff に出た削除も実行する")
```

`cmd_saved` の前に足す:

```python
def cmd_deploy(root: Path, args: argparse.Namespace) -> int:
    require_item(root, args.name)
    return deploy.deploy(root, args.name, args.url, args.prune)
```

`COMMANDS` を次にする:

```python
COMMANDS: dict[str, Callable[[Path, argparse.Namespace], int]] = {
    "new": cmd_new,
    "list": cmd_list,
    "check": cmd_check,
    "deploy": cmd_deploy,
    "saved": cmd_saved,
}
```

- [ ] **Step 5: テストが通ることを確かめる**

Run: `cd /workspaces/reso-world/worlds/reso-workshop && uv run pytest -q`
Expected: PASS（Task 2〜6 の全件）

- [ ] **Step 6: コミットする**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git add tools/workshop/deploy.py tools/workshop/cli.py tests/test_deploy.py && git commit -q -m "feat: add workshop deploy pipeline"
```

---

### Task 7: README と clone したあとの手順の確認

**テストの要否:** 不要。文書と手順だけで、新しいロジックが無い。代わりに、clone したあとの手順を実際に実行して確かめる（Step 2）。

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: Task 1〜6 のコマンド（`uv run workshop new|list|check|deploy|saved`）

- [ ] **Step 1: `README.md` を書く**

`/workspaces/reso-world/worlds/reso-workshop/README.md`:

````markdown
# reso-workshop

Resonite で使うアイテム（動かない小物・家具、仕掛けのあるガジェット）を ResoLoop と Blender で作り、工房のワールドへ反映して管理するリポジトリ。create-reso-world の Dev Container の `worlds/reso-workshop/` で使う。

## 準備（clone したあと）

create-reso-world のルート（`/workspaces/reso-world`）で実行する。

```bash
gh repo clone usaturn/reso-workshop worlds/reso-workshop
bash scripts/new-world.sh --apply reso-workshop
```

- `.resoloop.json` の `blenderExecutable` は `/workspaces/reso-world/worlds/reso-workshop/.resoloop/blender-system-python` を指すので、この場所に clone する
- `new-world.sh --apply` が、Git に入れていない symlink（`.pi`・`.claude/settings.json`・`.agents/sp-*.md`）と `.resoloop/` のラッパーを作り、`uv sync` を実行する

## 使い方

```bash
uv run workshop new desk-lamp --kind prop --display-name "Desk Lamp"   # 雛形から作る
# items/desk-lamp/manifest.json などを編集する
uv run workshop check                                                  # 検査
git add -A && git commit -m "feat: add desk lamp"                      # 保存に使う反映はコミット済みにする
uv run workshop deploy desk-lamp --url ws://localhost:<ポート>/         # 工房へ反映・検査・記録
# Resonite の中で、工房に出た「Desk Lamp v0.1.0」をインベントリに保存する
uv run workshop saved desk-lamp                                        # 保存を記録
git add items/desk-lamp/deploys.toml && git commit -m "chore: record desk lamp v0.1.0 saved"
uv run workshop list                                                   # 全アイテムの状態
```

- `deploy` は、準備（オフラインの検査）→ 差分の確認 → 反映 → 実機での検査（`resoloop test`・`item audit --strict`・反映後の差分が 0 件）→ 記録、の順に進み、失敗した段階で止まる
- 差分に削除が含まれるときは止まる。削除の一覧を確かめてから `--prune` を付けて実行し直す
- `saved` は、最後の反映が成功していて、未コミットの変更が無く、まだ保存していないときだけ記録できる。保存済みの版を別のコミットで保存し直すときは、先に `item.toml` の `version` を上げる

## アイテムの中身（`items/<名前>/`）

| ファイル | 内容 |
| --- | --- |
| `item.toml` | 表示名（`display_name`）・種類（`kind`: `prop` / `gadget`）・版（`version`）・工房の区画（`shelf`）。手で編集する |
| `deploys.toml` | 反映と保存の記録。CLI だけが書く |
| `manifest.json` | ResoLoop のマニフェスト。`ownership` と、`slot` の `key`・`name`・`parent`・`position` は CLI が入れるので書かない |
| `flux/` | gadget の ProtoFlux（`resoloop.flux.json` と `.pg`） |
| `build.py` | Blender で形を作るときだけ置く。`--out build/<名前>` を受け取り、出力をそこへ書く |
| `tests/` | アイテムのテスト。`deploy` の最初に実行する |

- 所有キーは `workshop-<名前>`、ルートスロットの名前は `<表示名> v<版>`、state は `.resoloop/state/workshop-<名前>.json`
- 区画 n の位置は X = ((n − 1) mod 8) × 1.5、Y = 1.0、Z = 2.0 + floor((n − 1) / 8) × 1.5（ワールドの原点基準、メートル）

## 決まりごと

- 50 MiB を超えるファイルは入れない（`workshop check` が検出する）。Meshy の原本は `worlds/reso-workshop-meshy/` に置く
- エージェント向けの規約は `AGENTS.md` の「このプロジェクト固有」にある
````

- [ ] **Step 2: clone したあとの手順を確かめる**

```bash
cd /workspaces/reso-world && git -C worlds/reso-workshop add README.md && git -C worlds/reso-workshop commit -q -m "docs: add README" \
  && git clone -q worlds/reso-workshop worlds/reso-workshop-clonetest \
  && bash scripts/new-world.sh --apply reso-workshop-clonetest; echo "exit=$?"; \
  git -C worlds/reso-workshop-clonetest status --short; \
  (cd worlds/reso-workshop-clonetest && uv run workshop list && uv run pytest -q 2>&1 | tail -1)
```

Expected:
- `new-world.sh` が `created: .resoloop/blender-system-python`・`created: .resoloop/.gitignore`・`linked: .claude/settings.json -> ...`・`linked: .pi -> ...`・`linked: .agents/sp-implementer.md -> ...`・`kept: .resoloop.json (...)`・`DONE: reso-workshop-clonetest` を出し、`exit=0`
- `git status --short` は空（作ったものはすべて Git の対象外）
- `アイテムはまだありません`、pytest は全件成功

- [ ] **Step 3: 確認用の clone を消す**

```bash
rm -rf -- /workspaces/reso-world/worlds/reso-workshop-clonetest && ls /workspaces/reso-world/worlds
```

Expected: `reso-workshop-clonetest` が無い。

---

### Task 8: 実機での確認（controller が行う）

**テストの要否:** 不要。Task 6 までのテストで守る挙動を、実際の ResoLoop と Resonite で一通り動かして確かめる作業。利用者とのやり取り（Resonite の起動・ポート・セッションからの削除）が要るので、controller が行う。

**Files:**
- 一時的に作って消す: `items/smoke-box/`、`build/smoke-box/`（作らない場合もある）、`.resoloop/state/workshop-smoke-box.json`

- [ ] **Step 1: 使い捨てのアイテムを作る**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && uv run workshop new smoke-box --kind prop --display-name "Smoke Box"
```

`items/smoke-box/manifest.json` を次に置き換える:

```json
{
  "schemaVersion": "1",
  "components": [
    { "key": "grabbable", "type": "FrooxEngine.Grabbable", "fields": { "Scalable": true } },
    { "key": "collider", "type": "FrooxEngine.BoxCollider", "fields": { "Size": [0.2, 0.2, 0.2] } }
  ],
  "children": [
    {
      "slot": { "key": "box", "name": "Box" },
      "components": [
        { "key": "box-mesh", "type": "FrooxEngine.BoxMesh", "fields": { "Size": [0.2, 0.2, 0.2] } },
        { "key": "box-material", "type": "FrooxEngine.PBS_Metallic", "fields": { "AlbedoColor": [0.85, 0.45, 0.15, 1] } },
        {
          "key": "box-renderer",
          "type": "FrooxEngine.MeshRenderer",
          "fields": { "Mesh": "$component:box-mesh", "Materials": ["$component:box-material"] }
        }
      ]
    }
  ],
  "tests": [
    { "name": "box-exists", "assertions": [{ "target": "$slot:box", "exists": true }] }
  ]
}
```

```bash
uv run workshop check smoke-box && uv run workshop list
```

Expected: `OK: 1 件のアイテム`、`smoke-box	prop	0.1.0	未反映	-`

- [ ] **Step 2: 利用者に Resonite の起動と工房のセッションのポートを確かめる**

利用者に、工房に使うワールドを開いてもらい、ResoniteLink のポートを聞く。`resoloop status --url ws://localhost:<ポート>/ --json` で接続できることを確かめる。

- [ ] **Step 3: 反映する（2 回）**

```bash
uv run workshop deploy smoke-box --url ws://localhost:<ポート>/; echo "exit=$?"
uv run workshop deploy smoke-box --url ws://localhost:<ポート>/; echo "exit=$?"
uv run workshop list; uv run workshop saved smoke-box; echo "exit=$?"
```

Expected:
- 1 回目・2 回目とも `[5/5] items/smoke-box/deploys.toml に記録しました` で `exit=0`。2 回目の差分は `作成 0・更新 0・削除 0`
- 記録は 2 件とも `result = "passed"`、`dirty = true`（使い捨てのアイテムはコミットしないため）
- `saved` は「未コミットの変更を含んでいます」で拒否され、`exit=1`
- 利用者に、工房の区画 1（原点から Z +2 m、高さ 1 m）に「Smoke Box v0.1.0」が見え、つかめることを確かめてもらう

- [ ] **Step 4: 片付ける**

利用者に、工房のセッションから「Smoke Box v0.1.0」を消してもらう。そのあと:

```bash
cd /workspaces/reso-world/worlds/reso-workshop && rm -rf -- items/smoke-box build/smoke-box && rm -f -- .resoloop/state/workshop-smoke-box.json && git status --short; uv run workshop list
```

Expected: `git status --short` は空、`アイテムはまだありません`。

---

### Task 9: 公開と記録（controller が行う）

**テストの要否:** 不要。公開の前の検査と、外部への操作。

- [ ] **Step 1: 公開の前の検査**

```bash
cd /workspaces/reso-world/worlds/reso-workshop && git status --short && uv run pytest -q 2>&1 | tail -1 && uv run workshop check \
  && git grep -n -I -E 'msy_[A-Za-z0-9]|sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|github_pat_|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY' $(git rev-list --all) ; echo "secret-scan-exit=$?"
```

Expected: `git status` は空、pytest は全件成功、`OK: 0 件のアイテム`、秘密の走査は何も出さず `secret-scan-exit=1`（一致なし）。一致が出たら 1 件ずつ中身を見て、同梱スキルの説明にある例の文字列などで秘密ではないことを確かめる。秘密だった場合は push せずに利用者へ報告する。

- [ ] **Step 2: 利用者に確認してから、GitHub にリポジトリを作って push する**

AskUserQuestion で「`gh repo create usaturn/reso-workshop --private` で作成し、`main` を push する」ことの確認を取る。了承を得たら:

```bash
cd /workspaces/reso-world/worlds/reso-workshop && gh repo create usaturn/reso-workshop --private --source . --remote origin --push \
  && gh repo view usaturn/reso-workshop --json visibility,defaultBranchRef \
  && test "$(git ls-remote origin refs/heads/main | cut -f1)" = "$(git rev-parse HEAD)" && echo "pushed main matches"
```

Expected: `visibility` が `PRIVATE`、`defaultBranchRef.name` が `main`、`pushed main matches`。

- [ ] **Step 3: 文書と記録を更新する**

- Spec と Plan の状態を completed にし、結果（コミット、テストの件数、実機の結果、GitHub の URL）と所要時間を書く。`docs/reso-workshop` ブランチにコミットする（push はしない。公開未実施と報告する）
- 確認用コピーを `scripts/superpowers-review-copy.sh` で別名（`...-r2-spec.md`、`...-plan.md` の新しい名前）で作る
- Claude Code の記憶（`reso-workshop-item-repository-state.md`）を更新する

---

### Task 10: シェーダー参照の自動許可（Task 8 の途中で追加、Spec D-12）

**経緯:** Task 8 の 1 回目の deploy で、`item audit --strict` が `ITEM_NOT_PORTABLE` で失敗した。原因は `PBS_Metallic` の `_shader` がエンジン既定の `StaticShader`（`Reso_4A5`、`persistent=false`、`resdb:///…unityshader`）を指していたこと。利用者が「工房全体で常に許可」を選び、Spec に D-12 を足した。実行時の最終レビューの修正（`0217555`）の後に行う。

**テストの要否:** 要る。監査の失敗出力の解析と再監査の分岐は、偽の resoloop で実行して確かめる挙動。

**Files:**
- Modify: `tools/workshop/deploy.py`（item-audit の段階）、`README.md`（deploy の説明に 1 行）、`AGENTS.md`（「このプロジェクト固有」に 1 行）
- Test: `tests/test_deploy.py`

**Interfaces:**
- Consumes: `deploy.call`・`deploy.live_args`・`deploy.StepFailed`・`deploy.error_summary`（`0217555` の時点の deploy.py）
- Produces: `deploy.shader_roles(output: str) -> list[str] | None`（item audit の失敗出力の JSON から、許可してよいシェーダー参照の役割を重複なく出現順で返す。許可できない誤りが 1 つでもある、または読めないなら None）

**要件:**
1. item-audit の段階で、1 回目の `resoloop item audit '$slot:root' --strict`（今と同じ引数）が 0 で終われば今までどおり。
2. 0 以外のときは、出力（stderr、空なら stdout）を `{"ok":false,"error":{"code":"ITEM_NOT_PORTABLE","context":{"report":{"issues":[…]}}}}` として読む。`severity` が `error` の issue がすべて、`code == "ITEM_EXTERNAL_REFERENCE"`、`member == "_shader"`、`targetType` が `FrooxEngine.Shader>` で終わる、`role` が文字列、を満たすときだけ、その役割の一覧を得る（1 件以上）。`severity` が `error` 以外の issue は判定に使わない。
3. 役割が得られたら、`--allow-external-role <role>` を役割ごとに足して（`--strict` の後、`--state` の前）もう一度監査する。0 で終われば合格とし、`シェーダーの参照を許可しました: <role>, …` を表示する。
4. 役割が得られない、または 2 回目も失敗したら、今までどおり `StepFailed("item-audit", …)`（記録は failed、`failed_step = "item-audit"`）。表示には失敗した方の出力を使う。
5. README の deploy の説明と AGENTS.md の「このプロジェクト固有」に、「マテリアルのシェーダー参照（`_shader`）は工房全体で自動的に許可する。それ以外の外部参照は item audit で止まる」旨を 1 行ずつ書く。

**テスト（tests/test_deploy.py に足す）:**
- シェーダーの issue だけで 1 回目が終了コード 6 → 2 回目の item audit に `--allow-external-role [FrooxEngine]FrooxEngine.PBS_Metallic:_shader` が付き、0 で終わる → 記録は passed、出力に役割が出る
- シェーダーの issue と別の外部参照の issue が混じる → 2 回目を呼ばず、記録は failed / `item-audit`
- 1 回目の出力が JSON でない → 2 回目を呼ばず failed / `item-audit`
- 2 回目も失敗 → failed / `item-audit`
- 同じ役割の issue が 2 つ → `--allow-external-role` は 1 回だけ
- `severity` が `warning` の別種の issue が混じっても、error がシェーダーだけなら許可して再監査する

**検証:** `uv run pytest -q -W error` が全件合格。Task 8 の実機確認を続け、Smoke Box の deploy が passed になること。

---

### Task 11: Meshy の Mech Knight をアイテムにする（利用者の追加依頼、2026-10-12）

利用者の依頼: 「準備できたら tmp/warsebraid/Meshy_AI_Dark_Fantasy_Mech_Kni_1012091015_image-to-3d-texture.glb をデプロイして。何も確認とらなくていいので、途中でとめずに resonite にデプロイしといて」「Meshy モデルについての参考になる Issue があったら参考にして」。この Task はアイテムを作って commit するまで。工房への deploy は controller が行う。

**Repository:** `/workspaces/reso-world/worlds/reso-workshop`（branch `main`、HEAD b941c0a、作業ツリーは空）

**元の GLB:** `/workspaces/reso-world/tmp/warsebraid/Meshy_AI_Dark_Fantasy_Mech_Kni_1012091015_image-to-3d-texture.glb`（86,804,860 bytes。Meshy の Web アプリの image-to-3d。メッシュ 1・2,014,090 三角形・頂点 1,070,556、素材 1: 不透明の PBR（baseColor・metallicRoughness・normal の JPEG 3 枚）、`doubleSided: true`、アニメ・スキン無し。glTF の bounds は X ±0.71、Y −0.947〜0.951、Z ±0.56）。元のファイルは動かさない・変えない。

**参考（create-reso-world Issue #90 の知見、asakusa01 で実証済み）:** Web アプリの GLB は asakusa01 の `finish.py` に直接渡せば、素材の検査 → 法線マップの UV 名の補正 → 溶接 → 削減 → カスタム法線の消去 → open3d の UVAtlas（多様体の補正込み）→ 2048px・16 サンプルで焼き直し → `resoloop blender export` → `validate` まで通る。近くで見る大きな物は削減を緩める（4 万三角形）。Voxel Remesh は穴の多い形だけ（今回は使わない）。発光マップは最大値 32/255 未満なら捨てる（finish.py が処理）。両面表示（culling）は書き出しで失われる（asakusa01 と同じく受け入れる。利用者は確認不要と指示）。

## 手順

1. **原本の保管（Git の外、Spec D-6）**: `/workspaces/reso-world/worlds/reso-workshop-meshy/mech-knight/source.glb` にコピーし、同じ場所に `source.json`（元のパス、bytes、SHA-256、コピーした日時、`"origin": "Meshy web app image-to-3d"`、`"task_id": null`（不明））を書く。
2. **仕上げの道具を移す**: `/workspaces/reso-world/worlds/asakusa01/assets/meshy/tools/finish.py` と `uvatlas_uv.py` を、reso-workshop の `tools/meshy/finish.py`・`tools/meshy/uvatlas_uv.py` へコピーし、asakusa01 固有の部分だけ直す。処理（溶接・削減・UV・焼き直し・素材の検査）は変えない。
   - `PROJECT_ROOT` をこの配置に合わせる（`tools/meshy/finish.py` → `parents[2]`）。`meshy_blender` は reso-workshop の `.agents/skills/meshy-resoloop/scripts` から読む（同じ ResoLoop 同梱スキルがある）
   - コレクション名・素材名などの `Asakusa01` を工房の名前に（例: コレクション `Workshop<Title>Export`、素材 `workshop_meshy_<name>`）。docstring の使い方を reso-workshop の実行方法に直し、出典（asakusa01、Issue #90）を 1 行書く
   - `pyproject.toml` に `[dependency-groups]` の `meshy = ["open3d==0.20.0"]` を足し、`uv lock` する。`uv run --group meshy python -c "import open3d"` が通ることを確かめる
3. **仕上げる**（reso-workshop を cwd に）:
   `resoloop blender run tools/meshy/finish.py --arg=--input --arg=/workspaces/reso-world/worlds/reso-workshop-meshy/mech-knight/source.glb --arg=--name --arg=mech-knight --arg=--height --arg=2.0 --arg=--target --arg=40000 --arg=--texture-size --arg=2048 --arg=--output-dir --arg=items/mech-knight/assets --arg=--meta-extra --arg=<source.json の内容を {"meshy": {...}} にした一時 JSON>`
   時間がかかる（数分〜数十分）。同期で待つ。終わったら `meta.json`（三角形数・寸法・UV の使用率・発光の有無）と textures を確かめて報告に書く。
4. **アイテムを作る**: `uv run workshop new mech-knight --kind prop --display-name "Mech Knight"` のあと、`item.toml` の `shelf` を `2` にする（工房の区画 1 には使い捨ての Smoke Box が実機に残っているため）。
5. **`items/mech-knight/build.py`**: `--out <dir>` を受け取り、`resoloop blender export items/mech-knight/assets/mech-knight.blend --output <dir> --parent Root …` を実行して `<dir>/model.apply.json` などを作る。CLI は `build/<名前>` を消してから呼ぶので、`<dir>` は存在しない前提でよい。cwd はリポジトリのルート。エクスポートのオプション（`--collection`、`--preserve-hierarchy`、`--pack-pbr` など）は `resoloop --help`・同梱スキル `resonite-blender`・asakusa01 の使い方（`worlds/asakusa01/modeling/asakusa01/` を grep）に合わせて決め、理由を報告に書く。失敗したら非 0 で終える。Python は標準ライブラリだけ（subprocess）。
6. **`items/mech-knight/manifest.json`**: `"include": ["../../build/mech-knight/model.apply.json"]` で書き出しを取り込み、`components` に `FrooxEngine.Grabbable`（`Scalable: true`、key `grabbable`）と、仕上げた寸法に合う `FrooxEngine.BoxCollider`（`Size`、原点が底面なので `Offset` は高さの半分）を置く。`tests` は root と、書き出しのメッシュのスロット（stable key）が存在すること。`ownership` と `slot` の key・name・parent・position は書かない（CLI が決める）。include の規則: `children`・`components`・`tests` は連結、オブジェクトはマージ、ルートの文書の scalar が勝つ。
7. **オフラインで確かめる**: `uv run workshop check mech-knight`、`uv run python items/mech-knight/build.py --out build/mech-knight`、`uv run python -c "from pathlib import Path; from workshop import items; i,_=items.load_item(Path('.'),'mech-knight'); print(items.render_manifest(Path('.'), i))"`、`resoloop validate items/mech-knight/manifest.rendered.json --json`。最後に `build/mech-knight` を消す（Git の対象外。deploy が作り直す）。
8. **大きさ**: コミットするファイルはすべて 50 MiB 以下（`uv run workshop check` が検出する）。全体の容量も報告に書く。
9. **コミット**: `tools/meshy/`、`pyproject.toml`、`uv.lock`、`items/mech-knight/`（`assets/`・`item.toml`・`deploys.toml`・`manifest.json`・`build.py`）。`build/`・`manifest.rendered.json` は入れない（`.gitignore` 済み）。push しない。

**テストの要否:** 不要。`finish.py`・`uvatlas_uv.py` は asakusa01 で実証した処理の移植で Blender の中で動く。`build.py` は resoloop を呼ぶだけ。代わりに手順 3・7 の実行結果で確かめる。`uv run pytest -q -W error` が今までどおり全件合格することも確かめる（items/mech-knight にテストは無い）。

---

## 結果（2026-10-12）

### コード（`usaturn/reso-workshop`、PRIVATE、https://github.com/usaturn/reso-workshop 、main `311312d`）

| Task | コミット | レビュー |
| --- | --- | --- |
| 1 骨組み | `eb5e727` | 承認（Minor 2 件は見送り） |
| 2 items.py | `f3ec875` | 承認 |
| 3 ledger.py | `00618b5` | 承認 |
| 4 gitstate.py | `de99153` | 承認 |
| 5 new/list/check/saved | `c73f8ec` | 承認（仕様の ❌ 1 件は Minor と判断） |
| 6 deploy | `8058ab0` | 承認 |
| 7 README・clone の確認 | `c32bb40` | 承認 |
| 最終レビュー（opus）の修正 | `0217555` | With fixes → I-1〜I-4・M-1・M-2・M-4〜M-6 を修正、再レビューで全件解消 |
| 10 シェーダー参照の許可（D-12） | `b941c0a` | 承認 |
| 11 Mech Knight | `8148518`・`b6c17d8`・`311312d`（反映の記録） | 承認 |

- テスト: `uv run pytest -q -W error` で 138 件合格
- clone したあとの手順（`new-world.sh --apply`）: 使い捨ての clone で、作業ツリーが空のまま pytest が通ることを確認（Task 7）

### 実機（`ws://localhost:36055/`、セッション名 New World、利用者が discover の候補から選択）

- Smoke Box（使い捨て）
  - 1 回目: `item-audit` で失敗（`PBS_Metallic:_shader` → `StaticShader`）、failed として記録された。これを受けて Spec D-12 と Task 10 を追加
  - 2 回目（`b941c0a`）: passed（シェーダーの参照を許可、差分は作成 0・更新 0・削除 0）。`saved` は未コミットを理由に拒否（終了コード 1）
  - 利用者の了承を得て、state のルート `Reso_116A`（名前と位置を確かめた）だけを `resoloop slot delete --yes` で削除し、`SLOT_NOT_FOUND` で消えたことを確認。ローカルの item と state はコミットせず、セッションの scratchpad に退避
- Mech Knight（利用者の追加依頼、Task 11）: 作成 20 件、`test`・`item audit --strict`（許可なしで合格）・反映後の diff 0 件。記録は passed、`dirty = false`、コミット `b6c17d8`。インベントリへの保存と `workshop saved` は利用者の操作待ち
- 撮影はしていない（利用者の指示: 撮る前に声をかける。ワールドが背面だと真っ黒になる）

### 実行中に判断したこと（SDD の台帳から）

- 実装のコミットは reso-workshop の `main` へ直接（Spec D-10）。レビュー用の差分は reso-workshop の git から作成
- Task 8・9 は利用者とのやり取りと外部への操作を含むので controller が実施。最終レビューは Task 8 の前に実施
- テストが CLI のエラーメッセージの一部を照合するのは許可（文書の文言ではなくプログラムの出力）
- Task 5 の「作成の途中で失敗すると作りかけのディレクトリが残る」は Minor（Spec が定める拒否の場合は満たしている）
- Task 7 の clone の確認は、2 回目の `--apply` が何も作らなかったことと clone の pytest の合格で受け入れ
- I-4: gadget は対象のまま、flux-sdk の有無を準備の段階で確かめて止める（この Dev Container には flux-sdk が無い）
- I-3: `build/<名前>` は CLI が消してから `build.py` を呼ぶ
- M-3（未コミットの passed を「保存待ち」と表示）は Spec 6 章のとおり残す。最終レビューの見送り Minor はそのまま
- D-12 の実装: 監査結果に出た `_shader` の役割だけを許可して再監査（常に渡すとマテリアルの無いアイテムで strict 監査が失敗するため）
- Task 11: 両面表示の損失は確認なしで受け入れ（利用者の指示）。区画は 2（区画 1 に Smoke Box が残っていたため）

### 知見の記録

- create-reso-world Issue #90 にコメント（issuecomment-6122214262）: 仕上げの道具の移植、include の asset のパス、`item audit` と `_shader`、flux-sdk が無いこと

### 所要時間（18:25〜19:16 JST、約 51 分）

| 区間 | 時間 |
| --- | --- |
| Plan の作成 | 18:25〜18:31 |
| Task 1〜7（実装とレビュー） | 18:31〜約 18:45 |
| 最終レビューと修正・再レビュー | 約 18:45〜19:00 |
| Task 8 の実機確認と Task 10 | 19:00〜19:05 |
| Task 11（Mech Knight の仕上げ 約 2.6 分を含む）と反映 | 19:05〜19:14 |
| 公開（Task 9）と後片付け | 19:14〜19:16 |

### 公開の状態

- reso-workshop: push 済み
- この Spec・Plan（create-reso-world のブランチ `docs/reso-workshop`）: ローカルのコミットのみ、公開未実施（文書専用 PR は指示があれば作成する）
