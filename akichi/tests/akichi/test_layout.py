import json

from modeling.akichi import layout


def test_layout_is_deterministic():
    a = json.dumps(layout.build_layout(), sort_keys=True)
    b = json.dumps(layout.build_layout(), sort_keys=True)
    assert a == b


def test_layout_counts():
    data = layout.build_layout()
    assert len(data["towers"]) == 10
    assert len(data["stalls"]) == 12
    assert len(data["shacks"]) == 10
    assert len(data["nightlife"]) == 4
    assert len(data["ads"]) == 26
    assert len(data["cables"]) == 12
    assert len(data["signs"]) == 14


def test_layout_validates_clean():
    data = layout.build_layout()
    assert layout.validate_layout(data) == []


def test_vacant_lot_is_clear():
    data = layout.build_layout()
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    for tower in data["towers"]:
        cx, cz = tower["center"]
        w, d = tower["footprint"]
        # footprint が vacant と重ならない
        assert not (cx - w/2 < vmax[0] and cx + w/2 > vmin[0]
                    and cz - d/2 < vmax[1] and cz + d/2 > vmin[1]), tower["id"]


def test_validator_detects_intrusion():
    data = layout.build_layout()
    data["towers"][0]["center"] = [0.0, 0.0]  # vacant の中へ移動
    issues = layout.validate_layout(data)
    assert any("vacant" in issue for issue in issues)


def test_all_ids_unique_and_zero_padded():
    data = layout.build_layout()
    ids = [item["id"] for group in ("towers","stalls","shacks","nightlife","ads","cables","signs") for item in data[group]]
    assert len(ids) == len(set(ids))
    assert all("-" in i and i.split("-")[1].isdigit() for i in ids)