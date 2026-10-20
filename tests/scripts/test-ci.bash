#!/bin/bash
# 秘密情報の検出の設定（.github/workflows/ci.yml の gitleaks ジョブと .gitleaks.toml）を検査する。
# 履歴の全体を既定の規則で走査し、除外は決めた識別子と偽のトークンだけに限る。どれが崩れても秘密情報の混入を見逃すか、
# 除外の設定が読まれない
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run python - <<'PY'
import hashlib
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
# 手元の検査（scripts/scan-before-push.sh）と CI で同じ版を使う。版は .devcontainer/install_gitleaks.bash にだけ書き、
# CI の env はその値をそろえて持つ。ずれると CI と手元で規則の解釈やログの形が変わる
installer = open(".devcontainer/install_gitleaks.bash", encoding="utf-8").read()
(pinned,) = re.findall(r'^readonly GITLEAKS_VERSION="([^"]+)"$', installer, re.MULTILINE)
assert version == pinned, (version, pinned)

config = tomllib.load(open(".gitleaks.toml", "rb"))
# 既定の規則を外すと、ほとんどの秘密情報を検出しなくなる
assert config["extend"]["useDefault"] is True, config
# 除外は次の 3 つだけ。増やすと秘密情報を除外してしまうおそれがある
allowlists = config["allowlists"]
assert len(allowlists) == 3, allowlists
identifiers = next(a for a in allowlists if a["regexTarget"] == "match")
assert identifiers["targetRules"] == ["generic-api-key"], identifiers
(pattern,) = identifiers["regexes"]
# 既定の規則に当たる形の偽のトークン。.gitleaks.toml の 2 つ目の allowlist が、この値そのものだけを除外する
fake_token = "Zx9Qm2Lp8Rt4Vw6Yb1Nc3Kd5Hf7Jg0Ss"
for identifier in ('key":"mat_material_Slum02_rubber_d4d07289"', 'key": "mesh_junk-pile-01__corrugated_1a2b3c4d"'):
    assert re.search(pattern, identifier), identifier
for secret in (f'key": "{fake_token}"', 'api_key": "mat_material_x"'):
    assert not re.search(pattern, secret), secret
values = [a for a in allowlists if a["regexTarget"] == "secret"]
fixture = next(a for a in values if re.search(a["regexes"][0], fake_token))
assert fixture["targetRules"] == ["generic-api-key"], fixture
(fixture_pattern,) = fixture["regexes"]
# 別の値（実行時に作る逆順の文字列）や、前後に文字が付いた値は除外しない
for other in (fake_token[::-1], fake_token + "x", "x" + fake_token):
    assert not re.search(fixture_pattern, other), other

# 3 つ目は、resoloop の key() が作る識別子（接頭辞_名前_sha256 の先頭 8 桁）の値を、書き方を問わず除外する（#135）
(names,) = [a for a in values if a is not fixture]
assert names["targetRules"] == ["generic-api-key"], names
(names_pattern,) = names["regexes"]
# push の前の検査は base の設定を使うので、除外が入る前の設定でも止まらないよう、識別子は連結で組み立てる
for parts in (
    ("mat", "material", "Slum02", "rubber", "d4d07289"),
    ("ul", "mat", "material", "Asakusa01", "ticker", "0a1b2c3d"),
    ("pbr", "mat", "material", "Slum02", "rubber", "d4d07289", "0f1e2d3c"),
    ("mesh", "SM", "NeonSign-LOD0__Cube", "001", "1a2b3c4d"),
):
    assert re.search(names_pattern, "_".join(parts)), parts
# 無作為な値は、識別子の前後や区切りを付けても除外しない。名前の塊に英字と数字が入り混じる値も無作為な値とみなす
hex32 = hashlib.sha256(b"create-reso-world issue-135 hex").hexdigest()[:32]
identifier = "_".join(("mat", "material", "Slum02", "rubber", "d4d07289"))
for other in (
    fake_token[::-1],
    "msy_" + fake_token,
    "ghp_" + fake_token,
    "_".join(("mat", "material", fake_token[4:20], "d4d07289")),
    "_".join(("mat", "material", "x")),
    "_".join(("mat", "material", "Slum02", "D4D07289")),
    # 前後に値が続くもの（正規表現の ^ と $ を守る）
    "_".join(("mat", "live", hex32)),
    fake_token + "_" + identifier,
    identifier + fake_token[:8],
    # key() の接頭辞（tex・mat・pbr・mesh・object・renderer・blender）が無い、人が付けたパスワードの形
    "_".join(("summer", "Holiday2024", "31415926")),
    "_".join(("letmein", "Tokyo", "88772211")),
):
    assert not re.search(names_pattern, other), other
PY

printf 'PASS: secret scanning covers the full history with the default rules and narrow allowlists\n'
