"""Behavior at the runner's configuration, wire-schema, and adapter boundaries."""

import traceback
from pathlib import Path

import pytest
from pydantic import ValidationError

from tools.agent_runner.config import ConfigError, check_depth, load_config, resolve_config_path
from tools.agent_runner.models import Receipt

# A shallow merge or array append loses inherited fields or keeps removed agents.
TEMPLATE = """schema_version = 1
[agents.first]
runtime = "pi"
command = ["fake-cli", "--original"]
model = "model-one"
approval = "noninteractive"
skill_sources = ["/template/skills"]
args = ["--template"]
env = ["HOME", "PATH"]
[agents.second]
runtime = "codex"
command = ["fake-cli-two"]
model = "model-two"
[agents.third]
runtime = "devin"
command = ["fake-cli-three"]
model = "model-three"
[roles.inspect]
skills = ["inspect"]
writes = false
deadline_seconds = 60
result_shape = "json"
[roles.implement]
skills = ["implement"]
writes = true
deadline_seconds = 120
result_shape = "text"
[workflows.audit.assignments.inspect]
agents = ["first"]
fallback = ["second", "third"]
[workflows.audit.assignments.implement]
agents = ["second"]
"""


@pytest.fixture
def template(tmp_path: Path) -> Path:
    path = tmp_path / "template.toml"
    path.write_text(TEMPLATE)
    return path


def personal_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "personal.toml"
    path.write_text(content)
    return path


def test_recursive_overlay_replaces_arrays_and_preserves_other_fields(template: Path, tmp_path: Path) -> None:
    personal = personal_config(
        tmp_path,
        """[agents.first]
command = ["personal-cli"]
args = []
env = ["PATH"]
[roles.inspect]
deadline_seconds = 30.5
[workflows.audit.assignments.inspect]
agents = ["third"]
fallback = ["second"]
""",
    )
    config = load_config(template, personal)
    assert config.agents["first"].command == ["personal-cli"]
    assert config.agents["first"].model == "model-one"
    assert config.agents["first"].skill_sources == ["/template/skills"]
    assert config.agents["first"].args == []
    assert config.agents["first"].env == ["PATH"]
    assert config.roles["inspect"].deadline_seconds == 30.5
    assert config.roles["inspect"].skills == ["inspect"]
    assert config.workflows["audit"].assignments["inspect"].agents == ["third"]
    assert config.workflows["audit"].assignments["inspect"].fallback == ["second"]


def test_assignment_override_is_last_and_keeps_explicit_fallback(template: Path, tmp_path: Path) -> None:
    personal = personal_config(
        tmp_path,
        '[workflows.audit.assignments.inspect]\nagents = ["third"]\nfallback = ["second"]\n',
    )
    config = load_config(template, personal, {"inspect": ["first"]}, "audit")
    assignment = config.workflows["audit"].assignments["inspect"]
    assert assignment.agents == ["first"]
    assert assignment.fallback == ["second"]
    assert load_config(template).workflows["audit"].assignments["inspect"].fallback == ["second", "third"]


# Missing validation would expose values through exception text or accept unsafe settings.
@pytest.mark.parametrize(
    ("overlay", "category"),
    [
        ('TOP_SECRET_unknown = "TOP_SECRET_value"\n', "unknown_key"),
    ],
)
def test_config_errors_are_categorized_without_input_or_traceback_leaks(
    template: Path, tmp_path: Path, overlay: str, category: str
) -> None:
    personal = personal_config(tmp_path, overlay)
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal)
    assert raised.value.category == category
    rendered = "".join(traceback.format_exception(raised.value))
    assert "TOP_SECRET" not in str(raised.value)
    assert "TOP_SECRET" not in repr(raised.value)
    assert "TOP_SECRET" not in rendered
    assert str(personal) not in str(raised.value)


@pytest.mark.parametrize(
    "overlay",
    [
        '[workflows.audit.assignments.unknown]\nagents = ["first"]\n',
    ],
)
def test_references_must_resolve(template: Path, tmp_path: Path, overlay: str) -> None:
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal_config(tmp_path, overlay))
    assert raised.value.category == "invalid_reference"


@pytest.mark.parametrize(
    "overlay",
    [
        "[workflows.audit.assignments.inspect]\nagents = []\n",
    ],
)
def test_self_cannot_be_mixed_or_used_as_fallback(template: Path, tmp_path: Path, overlay: str) -> None:
    with pytest.raises(ConfigError):
        load_config(template, personal_config(tmp_path, overlay))


def test_reserved_self_cannot_hide_a_real_agent_definition(template: Path, tmp_path: Path) -> None:
    personal = personal_config(
        tmp_path,
        '[agents.self]\nruntime = "pi"\ncommand = ["fake"]\nmodel = "hidden-model"\n',
    )
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal)
    assert raised.value.category == "invalid_value"


@pytest.mark.parametrize(
    "overlay",
    [
        '[agents.second]\nmodel = "model-one"\nprovider = "different-provider"\nmodel_key = "second-key"\n',
        '[agents.first]\nmodel_key = "first-key"\n'
        '[agents.second]\nmodel = "model-one"\nmodel_key = "second-key"\n',
    ],
)
def test_duplicate_models_are_rejected_across_all_candidates(template: Path, tmp_path: Path, overlay: str) -> None:
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal_config(tmp_path, overlay))
    assert raised.value.category == "duplicate_model"


# Ignoring shared keys silently schedules the same underlying model through provider aliases.
def test_model_identity_key_rejects_provider_aliases(template: Path, tmp_path: Path) -> None:
    providers = '[agents.first]\nprovider = "provider-one"\n[agents.second]\nprovider = "provider-two"\n'
    config = load_config(template, personal_config(tmp_path, providers))
    assert config.agents["first"].model == "model-one"
    assert config.agents["second"].model == "model-two"

    aliases = (
        '[agents.first]\nprovider = "provider-one"\nmodel_key = "shared-model"\n'
        '[agents.second]\nprovider = "provider-two"\nmodel_key = "shared-model"\n'
    )
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal_config(tmp_path, aliases))
    assert raised.value.category == "duplicate_model"


def test_diversity_constraint_checks_fallback_candidates(template: Path, tmp_path: Path) -> None:
    personal = personal_config(tmp_path, '[workflows.audit.exclude_same_model_as]\ninspect = "implement"\n')
    with pytest.raises(ConfigError) as raised:
        load_config(template, personal)
    assert raised.value.category == "duplicate_model"


def test_diversity_constraint_accepts_disjoint_candidates(template: Path, tmp_path: Path) -> None:
    personal = personal_config(
        tmp_path,
        '[workflows.audit.assignments.inspect]\nfallback = ["third"]\n'
        '[workflows.audit.exclude_same_model_as]\ninspect = "implement"\n',
    )
    config = load_config(template, personal)
    assert config.workflows["audit"].assignments["inspect"].fallback == ["third"]


@pytest.mark.parametrize(
    ("explicit", "xdg", "relative"),
    [
        ("/explicit/config.toml", "/xdg", "/explicit/config.toml"),
        ("~/personal.toml", "/xdg", "personal.toml"),
        (None, "/xdg", "/xdg/agent-runner/config.toml"),
        (None, "relative-xdg", ".config/agent-runner/config.toml"),
        (None, None, ".config/agent-runner/config.toml"),
    ],
)
def test_personal_path_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, explicit: str | None, xdg: str | None, relative: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AGENT_RUNNER_CONFIG", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    if explicit is not None:
        monkeypatch.setenv("AGENT_RUNNER_CONFIG", explicit)
    if xdg is not None:
        monkeypatch.setenv("XDG_CONFIG_HOME", xdg)
    expected = Path(relative) if relative.startswith("/") else tmp_path / relative
    assert resolve_config_path() == expected


@pytest.mark.parametrize("depth", ["1"])
def test_nested_or_malformed_depth_is_rejected(monkeypatch: pytest.MonkeyPatch, depth: str) -> None:
    monkeypatch.setenv("AGENT_RUNNER_DEPTH", depth)
    with pytest.raises(ConfigError) as raised:
        check_depth()
    assert raised.value.category == "nested_invocation"
    assert depth not in str(raised.value)


@pytest.mark.parametrize("depth", [None])
def test_top_level_depth_is_allowed(monkeypatch: pytest.MonkeyPatch, depth: str | None) -> None:
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)
    if depth is not None:
        monkeypatch.setenv("AGENT_RUNNER_DEPTH", depth)
    check_depth()


def receipt_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "run-1",
        "request_id": "request-1",
        "agent_id": "first",
        "role": "inspect",
        "status": "success",
        "payload": {"findings": [{"severity": "low", "line": 3}], "ok": True},
    }


@pytest.mark.parametrize(
    "payload",
    [{"nested": object()}, {"nonfinite": float("nan")}],
)
def test_receipt_rejects_non_json_payloads(payload: object) -> None:
    data = receipt_data()
    data["payload"] = payload
    with pytest.raises(ValidationError):
        Receipt.model_validate(data)
