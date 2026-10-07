#!/bin/bash
# 秘密情報の検出の設定（.github/workflows/ci.yml の gitleaks ジョブと .gitleaks.toml）を検査する。
# 履歴の全体を既定の規則で走査し、除外は決めた識別子と偽のトークンだけに限る。どれが崩れても秘密情報の混入を見逃すか、
# 除外の設定が読まれない
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run python - <<'PY'
import re
import tomllib

import yaml

ci = yaml.safe_load(open(".github/workflows/ci.yml", encoding="utf-8"))
steps = ci["jobs"]["gitleaks"]["steps"]
checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
# 浅い clone では過去のコミットに入った秘密情報を走査しない
assert checkout["with"]["fetch-depth"] == 0, checkout
leaks = next(s for s in steps if s.get("uses", "").startswith("gitleaks/gitleaks-action@"))
assert leaks["env"]["GITLEAKS_CONFIG"] == ".gitleaks.toml", leaks

# gitleaks-action@v3 は既定で 8.24.3 を入れるが、.gitleaks.toml の [[allowlists]] は
# gitleaks 8.25 以降でないと読まれないため、GITLEAKS_VERSION で明示していることを確かめる
version = leaks["env"]["GITLEAKS_VERSION"]
parsed = tuple(int(part) for part in version.split("."))[:2]
assert parsed >= (8, 25), version

config = tomllib.load(open(".gitleaks.toml", "rb"))
# 既定の規則を外すと、ほとんどの秘密情報を検出しなくなる
assert config["extend"]["useDefault"] is True, config
# 除外は次の 2 つだけ。増やすと秘密情報を除外してしまうおそれがある
allowlists = config["allowlists"]
assert len(allowlists) == 2, allowlists
identifiers = next(a for a in allowlists if a["regexTarget"] == "match")
assert identifiers["targetRules"] == ["generic-api-key"], identifiers
(pattern,) = identifiers["regexes"]
# 既定の規則に当たる形の偽のトークン。.gitleaks.toml の 2 つ目の allowlist が、この値そのものだけを除外する
fake_token = "Zx9Qm2Lp8Rt4Vw6Yb1Nc3Kd5Hf7Jg0Ss"
for identifier in ('key":"mat_material_Slum02_rubber_d4d07289"', 'key": "mesh_junk-pile-01__corrugated_1a2b3c4d"'):
    assert re.search(pattern, identifier), identifier
for secret in (f'key": "{fake_token}"', 'api_key": "mat_material_x"'):
    assert not re.search(pattern, secret), secret
fixture = next(a for a in allowlists if a["regexTarget"] == "secret")
assert fixture["targetRules"] == ["generic-api-key"], fixture
(fixture_pattern,) = fixture["regexes"]
assert re.search(fixture_pattern, fake_token), fixture_pattern
# 別の値（実行時に作る逆順の文字列）や、前後に文字が付いた値は除外しない
for other in (fake_token[::-1], fake_token + "x", "x" + fake_token):
    assert not re.search(fixture_pattern, other), other
PY

printf 'PASS: secret scanning covers the full history with the default rules and narrow allowlists\n'
