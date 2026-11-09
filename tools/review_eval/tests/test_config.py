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
