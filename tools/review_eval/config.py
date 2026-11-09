"""収集の設定（review-eval.toml）のモデルと読み込み。"""

import os
import re
import tomllib
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, model_validator

from tools.review_eval import shim

Route = Literal["pr-review", "pr-review-fix-loop", "review-fix-planning", "review-verify"]
ROUTES: tuple[Route, ...] = get_args(Route)

# sources の repo の形（capture の review_dir の owner・repo と同じ規則）。`.` 始まりの repo は reconcile が走査しないので置けない
_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
_REPO = re.compile(r"[A-Za-z0-9._-]+")


class ConfigError(Exception):
    """設定の誤り。メッセージに設定値を含めない。"""


class _Model(BaseModel):
    # TOML は日付を date、パスを文字列で渡すため、型変換を許す（strict にしない）
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(_Model):
    repo: str = Field(min_length=1)
    routes: Annotated[list[Route], Field(min_length=1)]
    since: date | None = None
    until: date | None = None
    note: str | None = None

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


class Config(_Model):
    schema_version: Literal[1]
    enabled: StrictBool
    approved_by: str | None = None
    approved_on: date | None = None
    store: Path
    workspace_root: Path
    max_store_bytes: int = Field(gt=0)
    max_artifact_bytes: int = Field(default=4 * 1024 * 1024, gt=0)
    max_sweep_files: int = Field(default=2000, gt=0)
    scan_timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)
    lock_timeout_seconds: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    secret_scanner: list[str] | None = None
    sources: list[Source] = Field(default_factory=list[Source])

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not self.store.is_absolute() or not self.workspace_root.is_absolute():
            raise ValueError("store と workspace_root は絶対パスにする")
        if self.enabled and (not self.approved_by or self.approved_on is None or not self.sources):
            raise ValueError("enabled の設定には approved_by・approved_on・sources が必要")
        repos = [source.repo.casefold() for source in self.sources]
        if len(set(repos)) != len(repos):
            raise ValueError("sources の repo が重複している（大文字と小文字は区別しない）")
        reviews = Path(os.path.normpath(self.workspace_root / "reviews"))
        store = Path(os.path.normpath(self.store))
        if store == reviews or reviews in store.parents:
            raise ValueError("store は workspace_root/reviews の中に置けない")
        return self

    def source_for(self, repository: str) -> Source | None:
        key = repository.casefold()
        return next((source for source in self.sources if source.repo.casefold() == key), None)


def load_config(path: Path) -> Config:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"設定を TOML として読めない: {type(exc).__name__}") from None
    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['type']}" for e in exc.errors())
        raise ConfigError(f"設定の内容が不正: {details}") from None


def load_active(environ: Mapping[str, str] | None = None) -> Config | None:
    """有効な設定だけを返す。ファイルが無い・無効なら None。有効なのに誤りがあれば ConfigError。sources は明示の許可リストで、登録（projects.toml など）は照合しない。"""
    path = shim.config_path(environ)
    if path is None or not path.is_file():
        return None
    config = load_config(path)
    if not config.enabled:
        return None
    return config
