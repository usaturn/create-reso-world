#!/bin/bash
# CI の定義（.github/workflows/ci.yml）と gitleaks の設定（.gitleaks.toml）が仕様 9.2 節のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run python - <<'PY'
import re
import tomllib

import yaml

ci = yaml.safe_load(open(".github/workflows/ci.yml", encoding="utf-8"))
# PyYAML は on: を真偽値の True として読む
triggers = ci.get("on", ci.get(True))
assert set(triggers) == {"push", "pull_request"}, triggers
jobs = ci["jobs"]
assert set(jobs) == {"devcontainer-tests", "layout", "skill-tests", "gitleaks"}, sorted(jobs)


def runs(job):
    return [step["run"] for step in jobs[job]["steps"] if "run" in step]


def uses(job):
    return [step["uses"] for step in jobs[job]["steps"] if "uses" in step]


assert "bash .devcontainer/run-tests.bash" in runs("devcontainer-tests"), runs("devcontainer-tests")
assert any(all(p in r for p in ("zsh", "ripgrep", "bubblewrap")) for r in runs("devcontainer-tests")), "zsh, ripgrep and bubblewrap are needed by the tests"
assert any(u.startswith("astral-sh/setup-uv@") for u in uses("devcontainer-tests"))
assert runs("layout") == ["bash scripts/check-layout.sh"], runs("layout")
assert not any("resoloop" in u for u in uses("layout")), "layout runs without resoloop"
assert runs("skill-tests") == ["uv run pytest tests/skills .agents/skills"], runs("skill-tests")
assert any(u.startswith("astral-sh/setup-uv@") for u in uses("skill-tests"))
steps = jobs["gitleaks"]["steps"]
checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
assert checkout["with"]["fetch-depth"] == 0, checkout
leaks = next(s for s in steps if s.get("uses", "").startswith("gitleaks/gitleaks-action@"))
assert leaks["env"]["GITLEAKS_CONFIG"] == ".gitleaks.toml", leaks
for job in jobs.values():
    assert job["runs-on"] == "ubuntu-latest"
    assert "blender" not in str(job).lower(), "CI does not build worlds with Blender"

config = tomllib.load(open(".gitleaks.toml", "rb"))
assert config["extend"]["useDefault"] is True, config
(allow,) = config["allowlists"]
assert allow["targetRules"] == ["generic-api-key"] and allow["regexTarget"] == "match", allow
(pattern,) = allow["regexes"]
for identifier in ('key":"mat_material_Slum02_rubber_d4d07289"', 'key": "mesh_junk-pile-01__corrugated_1a2b3c4d"'):
    assert re.search(pattern, identifier), identifier
for secret in ('key": "Zx9Qm2Lp8Rt4Vw6Yb1Nc3Kd5Hf7Jg0Ss"', 'api_key": "mat_material_x"'):
    assert not re.search(pattern, secret), secret
PY

printf 'PASS: CI workflow and gitleaks config follow spec 9.2\n'
