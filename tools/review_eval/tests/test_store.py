import multiprocessing
import stat
from pathlib import Path

import pytest

from tools.review_eval.models import Observation
from tools.review_eval.store import Store, StoreError
from tools.review_eval.tests.support import make_observation, put_revisions_worker

REVISIONS = [
    "# レビュー\n\n指摘 1: 日本語と改行を含む本文\n".encode(),
    "# レビュー\n\n指摘 1 を修正した 2 つ目の revision\n\n- 追加\n".encode(),
]


def _put(store: Store, data: bytes, observed_at: str) -> Observation:
    sha = store.put_blob(data)
    observation = make_observation(sha, len(data), observed_at=observed_at)
    assert store.put_observation(observation)
    return observation


def test_restore_returns_every_revision_after_originals_are_gone(tmp_path: Path) -> None:
    store = Store.init(tmp_path / "store")
    review_dir = tmp_path / "reviews" / "o" / "r" / "#1-b"
    review_dir.mkdir(parents=True)
    original = review_dir / "model.md"
    observed: list[Observation] = []
    for index, data in enumerate(REVISIONS):
        original.write_bytes(data)
        observed.append(_put(store, data, f"2026-10-30T00:00:0{index}Z"))
    original.unlink()
    review_dir.rmdir()

    for index, data in enumerate(REVISIONS):
        dest = tmp_path / f"restored-{index}"
        results = store.restore([observed[index]], dest)
        assert results[0]["status"] == "restored"
        written = dest / "#1-b" / "model.md"
        assert written.read_bytes() == data


def test_concurrent_puts_create_one_observation_per_revision(tmp_path: Path) -> None:
    store = Store.init(tmp_path / "store")
    revisions = [f"revision {index} 日本語\n".encode() for index in range(3)]
    context = multiprocessing.get_context("spawn")
    with context.Pool(8) as pool:
        results = pool.starmap(put_revisions_worker, [(str(store.root), revisions)] * 8)
    for index in range(3):
        assert sum(1 for created in results if created[index]) == 1
    observations = store.observations()
    assert len(observations) == 3
    assert len(list((store.root / "observations").rglob("*.json"))) == 3
    for observation in observations:
        assert store.read_blob(observation.sha256)
    assert store.verify() == []


def test_existing_blob_with_wrong_bytes_is_not_overwritten(tmp_path: Path) -> None:
    store = Store.init(tmp_path / "store")
    data = REVISIONS[0]
    sha = store.put_blob(data)
    blob = next(path for path in (store.root / "blobs").rglob("*") if path.is_file())
    blob.chmod(0o600)
    blob.write_bytes(b"tampered")
    with pytest.raises(StoreError):
        store.put_blob(data)
    assert blob.read_bytes() == b"tampered"
    assert any(sha in problem for problem in store.verify())


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
