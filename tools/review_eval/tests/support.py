"""review-eval のテスト補助: 一時の設定・observation の作成と、spawn 用の worker。"""

import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from tools.review_eval.config import ROUTES
from tools.review_eval.models import FormatInfo, Observation, TargetInfo, observation_identity

FAKE_SCANNER: list[str] = [
    sys.executable,
    "-c",
    "import sys; open(sys.argv[2], 'w').write('[]')",
    "{source}",
    "{report}",
]

_FLAGGING_CODE = (
    "import json, pathlib, sys\n"
    "source, report = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])\n"
    "found = [{'File': str(p)} for p in sorted(source.iterdir()) if b'ghp_' in p.read_bytes()]\n"
    "report.write_text(json.dumps(found))\n"
    "raise SystemExit(99 if found else 0)\n"
)
FLAGGING_SCANNER: list[str] = [sys.executable, "-c", _FLAGGING_CODE, "{source}", "{report}"]


def write_collection_config(
    path: Path,
    *,
    store: Path,
    workspace_root: Path,
    repos: Sequence[str],
    routes: Sequence[str] = ROUTES,
    scanner: Sequence[str] | None = FAKE_SCANNER,
    max_store_bytes: int = 64 * 1024 * 1024,
    **overrides: object,
) -> Path:
    values: dict[str, object] = {
        "schema_version": 1,
        "enabled": True,
        "approved_by": "test",
        "store": str(store),
        "workspace_root": str(workspace_root),
        "max_store_bytes": max_store_bytes,
    }
    if scanner is not None:
        values["secret_scanner"] = list(scanner)
    values.update(overrides)
    lines = [f"{key} = {json.dumps(value)}" for key, value in values.items()]
    lines.insert(2, f"approved_on = {date.today().isoformat()}")
    for repo in repos:
        lines += ["", "[[sources]]", f"repo = {json.dumps(repo)}", f"routes = {json.dumps(list(routes))}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_observation(
    sha256: str,
    size: int,
    *,
    repository: str = "o/r",
    pr: int = 1,
    review_dir: str | None = "#1-b",
    path: str = "model.md",
    observed_at: str = "2026-10-30T00:00:00Z",
) -> Observation:
    return Observation(
        schema="review-eval-observation/v1",
        observation_id=observation_identity(repository, pr, review_dir, path, sha256),
        repository=repository,
        pr=pr,
        review_dir=review_dir,
        path=path,
        sha256=sha256,
        bytes=size,
        body="stored",
        format=FormatInfo(schema=None, kind=None, known=False),
        target=TargetInfo(reviewed_head=None, base=None, source_key=None, missing_reason=None),
        observed_at=observed_at,
        file_mtime=None,
        trigger="save",
        route="pr-review",
        event="test",
        context={},
        inputs=[],
        collector={"name": "test"},
    )


def put_revisions_worker(store_root: str, revisions: Sequence[bytes]) -> list[bool]:
    """spawn されたプロセスで各 revision を put し、observation を作れたかを返す。"""
    from tools.review_eval.store import Store

    store = Store.open(Path(store_root))
    created: list[bool] = []
    for data in revisions:
        sha = store.put_blob(data)
        created.append(store.put_observation(make_observation(sha, len(data))))
    return created


def append_times_worker(store_root: str, who: str, count: int) -> list[int]:
    """spawn されたプロセスで台帳に `time.add` を `count` 件追記し、受け取った seq を返す。"""
    from tools.review_eval.ledger import Ledger
    from tools.review_eval.store import Store

    ledger = Ledger(Store.open(Path(store_root)), lock_timeout=60)
    return [ledger.append({"op": "time.add", "stage": "other", "seconds": 1}, by=who) for _ in range(count)]
