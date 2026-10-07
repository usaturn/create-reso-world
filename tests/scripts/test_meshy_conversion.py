"""Real offline Blender/export tests, plus publication and write-boundary failures.

Mutations caught: joining objects, losing textures/channels, wrong transforms,
publishing a failed export, trusting stale hashes or paths, overwriting outputs.
"""

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "scripts/meshy.py"
FIXTURE = ROOT / "tests/fixtures/meshy/create_fixture.py"
PARENT = 'path:["Root","VerifiedFixtureParent"]'


def run(argv, *, env=None, cwd=None):
    return subprocess.run(
        argv, env=env, cwd=cwd, text=True, capture_output=True, timeout=90, check=False
    )


@pytest.fixture(scope="module")
def tools():
    resoloop = shutil.which("resoloop")
    if not resoloop:
        pytest.skip("ResoLoop CLI unavailable; real offline exporter required")
    found = run([resoloop, "blender", "find", "--json"])
    if found.returncode:
        pytest.skip("ResoLoop cannot find Blender/bpy: " + found.stdout)
    return resoloop


@pytest.fixture(scope="module")
def glbs(tmp_path_factory, tools):
    directory = tmp_path_factory.mktemp("real-glbs")
    result = {}
    for case in ("opaque", "transparency", "transmission", "animation"):
        path = directory / (case + ".glb")
        proc = run(
            [
                tools,
                "blender",
                "run",
                str(FIXTURE),
                "--arg=--output",
                "--arg=" + str(path),
                "--arg=--case",
                "--arg=" + case,
                "--json",
            ]
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert path.read_bytes()[:4] == b"glTF"
        result[case] = path
    return result


@pytest.fixture
def world(tmp_path, glbs):
    project = tmp_path / "world"
    project.mkdir()
    (project / ".resoloop.json").write_text("{}")
    operation = project / "content/generated/meshy/asset"
    source = operation / "source"
    source.mkdir(parents=True)
    # Deliberately not generated.glb/model.glb: consume the download manifest.
    path = source / "arbitrary-download-name.glb"
    shutil.copyfile(glbs["opaque"], path)
    manifest = {
        "schema_version": 1,
        "operation_id": str(uuid.uuid4()),
        "kind": "image",
        "resource": "image-to-3d",
        "request": {},
        "stage": "downloaded",
        "task": {"task_id": "offline-fixture", "status": "SUCCEEDED"},
        "downloads": {
            "state": "completed",
            "files": [
                {
                    "key": "model_urls.glb",
                    "path": str(path),
                    "status": "written",
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            ],
        },
    }
    manifest_path = operation / "operation.json"
    manifest_path.write_text(json.dumps(manifest))
    return project, operation, path, manifest_path


def convert(world, *extra, env=None):
    project = world[0]
    child_env = {k: v for k, v in os.environ.items() if not k.startswith("MESHY_")}
    if env:
        child_env.update(env)
    return run(
        [
            sys.executable,
            str(ENTRY),
            "--project",
            str(project),
            "convert",
            "--operation",
            "asset",
            "--height",
            "2",
            "--yaw",
            "90",
            "--origin",
            "ground",
            "--parent",
            PARENT,
            "--name",
            "OfflineFixture",
            *extra,
        ],
        env=child_env,
    )


def assert_unpublished(world):
    assert not (world[1] / "converted").exists()
    assert "conversion" not in json.loads(world[3].read_text())
    assert not list(world[1].glob(".conversion-*"))


# Catch transform/channel/texture loss in the actual saved blend and exported bundle.
@pytest.mark.parametrize("origin", ["ground", "center"])
def test_real_conversion_preserves_objects_textures_and_normalizes_bounds(
    world, tools, tmp_path, origin
):
    before = world[2].read_bytes()
    proc = convert(world, "--origin", origin)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert world[2].read_bytes() == before
    conversion = json.loads(world[3].read_text())["conversion"]
    assert conversion == result
    blend = Path(conversion["blend"])
    report = json.loads(Path(conversion["report"]).read_text())
    bundle = Path(conversion["bundle"])
    assert blend.is_file() and blend.is_relative_to(world[1] / "converted")
    assert report["mesh_count"] == 2
    assert report["triangles"] == 24
    assert report["materials"] == 1
    assert report["bounds"]["height"] == pytest.approx(2)
    assert report["bounds"]["min"][2] == pytest.approx(0 if origin == "ground" else -1)
    exported = json.loads((bundle / "report.json").read_text())
    assert exported["preserveHierarchy"] is True
    assert exported["triangles"] == 24
    assert {m["name"] for m in exported["meshes"]} == {"LowerPart", "UpperPart"}
    assert len(exported["textures"]) == 2
    assert all((bundle / t["file"]).is_file() for t in exported["textures"])
    assert all(t["width"] == t["height"] == 2 for t in exported["textures"])
    apply = json.loads((bundle / "model.apply.json").read_text())
    assert apply["slot"]["parent"] == PARENT
    assert all((bundle / a["source"]).is_file() for a in apply["assets"].values())
    assert exported["source"] == str(blend)
    assert exported["outputDirectory"] == str(bundle)
    # Reopen, not just inspect the converter's own report: pack must survive saving.
    probe = tmp_path / "probe.py"
    probe.write_text("""import bpy, json, sys
from mathutils import Vector
from pathlib import Path
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
sh = bpy.data.materials['FixtureMaterial'].node_tree.nodes.get('Principled BSDF')
albedo = sh.inputs['Base Color'].links[0].from_node.image
channels = {}
for name in ('Metallic', 'Roughness'):
    node = sh.inputs[name].links[0].from_node
    channels[name] = {'type': node.type, 'space': node.image.colorspace_settings.name,
                      'pixels': list(node.image.pixels), 'packed': bool(node.image.packed_file)}
original_images = [{'name':i.name, 'packed':bool(i.packed_file), 'size':list(i.size)} for i in bpy.data.images if i.type == 'IMAGE']
pbr = bpy.data.images.load(str(next(Path(sys.argv[-2]).glob('pbr_*.png'))))
pbr.colorspace_settings.name = 'Non-Color'
Path(sys.argv[-1]).write_text(json.dumps({'channels': channels,
    'albedo': {'space':albedo.colorspace_settings.name, 'pixels':list(albedo.pixels)},
    'packed_pbr': list(pbr.pixels),
    'parents': {o.name:o.parent.name for o in objects},
    'centers': {o.name:list(o.matrix_world.translation) for o in objects},
    'images': original_images,
    'min': [min(p[i] for p in points) for i in range(3)],
    'max': [max(p[i] for p in points) for i in range(3)]}))
""")
    inspection = tmp_path / "inspection.json"
    check = run(
        [
            tools,
            "blender",
            "run",
            str(probe),
            "--blend",
            str(blend),
            "--arg=" + str(bundle),
            "--arg=" + str(inspection),
            "--json",
        ]
    )
    assert check.returncode == 0, check.stdout + check.stderr
    saved = json.loads(inspection.read_text())
    assert saved["parents"] == {
        "LowerPart": "FixtureHierarchy",
        "UpperPart": "FixtureHierarchy",
    }
    assert saved["centers"]["LowerPart"][:2] == pytest.approx([0, -0.5], abs=1e-6)
    assert saved["centers"]["UpperPart"][:2] == pytest.approx([0, 0.5], abs=1e-6)
    assert saved["max"][2] - saved["min"][2] == pytest.approx(2)
    assert saved["albedo"]["space"] == "sRGB"
    assert saved["albedo"]["pixels"] == pytest.approx(
        [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1], abs=1 / 255
    )
    assert saved["packed_pbr"] == pytest.approx([0.75, 1, 0, 0.75] * 4, abs=1 / 255)
    for name, value in (("Metallic", 0.75), ("Roughness", 0.25)):
        channel = saved["channels"][name]
        assert channel["type"] == "TEX_IMAGE" and channel["space"] == "Non-Color"
        assert channel["packed"]
        assert channel["pixels"][:4] == pytest.approx(
            [value, value, value, 1], abs=1 / 255
        )
    assert all(i["packed"] and i["size"] == [2, 2] for i in saved["images"])
    # A second conversion may not destroy a successful editable source/bundle.
    second = convert(world)
    assert second.returncode != 0
    assert blend.is_file()
    assert json.loads(world[3].read_text())["conversion"] == conversion


# Catch silent static adaptation of alpha, specialized shaders or animated assets.
@pytest.mark.parametrize(
    "case,label",
    [
        ("transparency", "FixtureMaterial"),
        ("transmission", "FixtureMaterial"),
        ("animation", "LowerPart"),
    ],
)
def test_unsupported_glb_fails_by_name_without_publication(world, glbs, case, label):
    shutil.copyfile(glbs[case], world[2])
    manifest = json.loads(world[3].read_text())
    manifest["downloads"]["files"][0].update(
        bytes=world[2].stat().st_size,
        sha256=hashlib.sha256(world[2].read_bytes()).hexdigest(),
    )
    world[3].write_text(json.dumps(manifest))
    proc = convert(world)
    assert proc.returncode != 0
    assert label in proc.stderr, proc.stdout + proc.stderr
    assert_unpublished(world)


# Export failure really creates partial files: they must never become a usable bundle.
@pytest.mark.parametrize("mode", ["failure", "incomplete"])
def test_failed_export_is_not_published(world, tools, tmp_path, mode):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "resoloop"
    fake.write_text(f"""#!{sys.executable}
import os, pathlib, sys
if sys.argv[1:3] == ['blender', 'run']:
    os.execv({tools!r}, [{tools!r}] + sys.argv[1:])
assert sys.argv[1:3] == ['blender', 'export']
p = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])
p.mkdir()
(p / 'partial.mesh.json').write_text('{{}}')
print('{{"ok":{str(mode == "incomplete").lower()}}}')
sys.exit({0 if mode == "incomplete" else 1})
""")
    fake.chmod(0o755)
    proc = convert(world, env={"PATH": str(bindir) + os.pathsep + os.environ["PATH"]})
    assert proc.returncode != 0
    assert (
        "conversion_outputs_missing"
        if mode == "incomplete"
        else "resoloop_export_failed"
    ) in proc.stderr
    assert_unpublished(world)


# Catch trusting edited manifests or escaping output/input boundaries before subprocesses.
@pytest.mark.parametrize(
    "bad",
    [
        "hash",
        "size",
        "partial",
        "ambiguous",
        "missing",
        "outside",
        "outside_project",
        "symlink",
        "output_symlink",
        "locked",
    ],
)
def test_conversion_rejects_unsafe_or_unready_inputs(world, tmp_path, bad):
    manifest = json.loads(world[3].read_text())
    entry = manifest["downloads"]["files"][0]
    lock = None
    if bad == "hash":
        entry["sha256"] = "0" * 64
    elif bad == "size":
        entry["bytes"] += 1
    elif bad == "partial":
        manifest["downloads"]["state"] = "partial"
    elif bad == "ambiguous":
        manifest["downloads"]["files"].append(dict(entry))
    elif bad == "missing":
        world[2].unlink()
    elif bad in ("outside", "outside_project", "symlink"):
        outside = (world[0] if bad == "outside" else tmp_path) / "outside.glb"
        shutil.copyfile(world[2], outside)
        if bad in ("outside", "outside_project"):
            entry["path"] = str(outside)
        else:
            world[2].unlink()
            world[2].symlink_to(outside)
    elif bad == "output_symlink":
        (world[1] / "converted").symlink_to(
            tmp_path / "elsewhere", target_is_directory=True
        )
    elif bad == "locked":
        lock = (world[1] / ".lock").open("w")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    world[3].write_text(json.dumps(manifest))
    try:
        proc = convert(world, env={"PATH": "/nonexistent"})
        assert proc.returncode != 0
        expected = {
            "hash": "source_glb_changed",
            "size": "source_glb_changed",
            "partial": "completed_downloads_required",
            "ambiguous": "unique_glb_required",
            "missing": "source_glb_missing",
            "outside": "source_outside_operation",
            "outside_project": "path_outside_project",
            "symlink": "symlink_forbidden",
            "output_symlink": "symlink_forbidden",
            "locked": "operation_locked",
        }[bad]
        assert expected in proc.stderr, proc.stdout + proc.stderr
        assert "conversion" not in json.loads(world[3].read_text())
        assert not list(world[1].glob(".conversion-*"))
    finally:
        if lock:
            lock.close()


# Catch invalid normalization requests before spawning Blender (including API use).
@pytest.mark.parametrize(
    "extra",
    [
        ["--height", "0"],
        ["--height", "-2"],
        ["--height", "nan"],
        ["--yaw", "inf"],
        ["--parent", ""],
        ["--name", "../escape"],
    ],
)
def test_invalid_conversion_parameters_are_rejected(world, extra):
    proc = convert(world, *extra, env={"PATH": "/nonexistent"})
    assert proc.returncode != 0
    assert "invalid_conversion_parameters" in proc.stderr
    assert_unpublished(world)


# Catch a manifest write failing after replace: no success marker may survive rollback.
def test_failed_manifest_publication_restores_operation(world, tools):
    bootstrap = f"""import sys
sys.path.insert(0, {str(ROOT / "scripts")!r})
import meshy_conversion, meshy
original = meshy_conversion.save_operation
def fail_after_replace(*args):
    original(*args)
    raise OSError('simulated directory fsync failure')
meshy_conversion.save_operation = fail_after_replace
raise SystemExit(meshy.main())
"""
    args = [
        "--project",
        str(world[0]),
        "convert",
        "--operation",
        "asset",
        "--height",
        "2",
        "--parent",
        PARENT,
    ]
    proc = run([sys.executable, "-c", bootstrap, *args])
    assert proc.returncode != 0
    assert "local_workflow_failed" in proc.stderr
    assert_unpublished(world)


# Catch timed-out Blender descendants writing into a removed staging directory.
def test_resoloop_timeout_stops_process_tree(world, tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    marker = tmp_path / "late-write"
    fake = bindir / "resoloop"
    fake.write_text(f"""#!{sys.executable}
import json, pathlib, subprocess, sys, time
if sys.argv[2] == 'run':
    print(json.dumps({{'ok':True}}))
else:
    subprocess.Popen([sys.executable, '-c',
        "import time,pathlib;time.sleep(0.5);pathlib.Path({str(marker)!r}).write_text('orphan')"])
    time.sleep(1)
    print(json.dumps({{'ok':True}}))
""")
    fake.chmod(0o755)
    bootstrap = f"""import sys
sys.path.insert(0, {str(ROOT / "scripts")!r})
import meshy_conversion, meshy
meshy_conversion.RESOLOOP_PROCESS_TIMEOUT_SECONDS = 0.2
raise SystemExit(meshy.main())
"""
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"])
    proc = run(
        [
            sys.executable,
            "-c",
            bootstrap,
            "--project",
            str(world[0]),
            "convert",
            "--operation",
            "asset",
            "--height",
            "2",
            "--parent",
            PARENT,
        ],
        env=env,
    )
    assert proc.returncode != 0
    assert "resoloop_export_failed" in proc.stderr
    time.sleep(0.6)
    assert not marker.exists(), "timed-out exporter descendant survived"
    assert_unpublished(world)
