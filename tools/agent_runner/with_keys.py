"""ランチャー起動セッションで、runner の agent が使う key を補ってからコマンドを起動する。

runner は起動時の環境（``/proc/self/environ``）から子の環境を組み立てる。起動後に
``os.environ`` を変えても子には届かないので、不足している key を補った環境で
``os.execvpe`` し直す。

補う名前は、雛形と個人設定を後段と同じ規則で重ねた全 agent の ``env`` から
``HOME``・``PATH``・``GIT_*`` を除いたもの。workflows の担当・fallback の参照と重複は
検査しない（後段が上書き後に検査する）。解決順序は、今の環境（非空値を保持・上書き
しない）→ ランチャー環境の ``ANTHROPIC_BASE_URL`` の完全一致による導出 →
``~/.config/create-reso-world/env``。段階 1・2 で解決した名前は env ファイルから
上書きしない。shell としては実行せず、解析できない代入がある名前は前の行の値も含めて
補わない。値は stderr に出さない。
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".devcontainer/agent-runner.toml"
USAGE = "usage: with_keys.py [--template PATH] [--config PATH] -- <command> [args...]"
# 通常のシェルから起動したときと同じ値を使う名前は補わない。GIT_* は別途除く。
_SKIPPED_NAMES = frozenset({"HOME", "PATH"})
_LOOKS_LIKE = re.compile(r"^[ \t]*(?:export[ \t]+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)=")
# 値は、展開になる $・`・\ を含まない二重引用符、単一引用符、危険な文字を含まない裸の語、空。
# 後ろは空白と # コメントだけ。これ以外は解析できない代入として扱う。
# 値が ~ で始まる行と、:~ を含む行も解析できない（文字どおり渡すとシェルと違う値になりうる）。
_ASSIGNMENT = re.compile(
    r"""
    ^[ \t]*
    (?:export[ \t]+)?
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)=
    (?:
        "(?P<double>[^"$`\\]*)"
        | '(?P<single>[^']*)'
        | (?P<bare>[^\s"'$`\\;|&<>()]+)
    )?
    (?:[ \t]+\#.*)?
    [ \t]*$
    """,
    re.VERBOSE,
)
# ランチャーが設定する ANTHROPIC_BASE_URL と、そのセッションで使う key の変数名。
# 完全一致だけを扱い、前後の空白除去・末尾スラッシュの正規化・部分一致はしない。
_LAUNCHER_BASE_URL_KEYS: Mapping[str, str] = {
    "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic": "MAAS_ANTHROPIC_TOKEN",
    "https://ollama.com": "OLLAMA_API_KEY",
    "https://api.deepinfra.com/anthropic": "DEEPINFRA_TOKEN",
    "https://opencode.ai/zen/go": "OPENCODE_API_KEY",
}
# ASCII 英数字を 1 文字も含まないトークンは key として使えない。
_ASCII_ALNUM = re.compile(r"[A-Za-z0-9]")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_runner.config import (  # noqa: E402
    ConfigError,
    _merge,
    _read,
    _reject_removed_runtime,
    _validation_category,
    resolve_config_path,
)
from tools.agent_runner.models import Agent, Config  # noqa: E402


class _Usage(Exception):
    """argv が wrapper の形でない。診断に値を含めない。"""


def needed_names(template: Path, personal: Path | None) -> set[str]:
    """全 agent の env から HOME・PATH・GIT_* を除いた名前。

    雛形と個人設定は後段と同じ規則で重ねる。担当の参照・重複は検査しない。
    後段が上書きで受け付ける設定を、ここだけで拒否しない。
    """
    data = _read(template)
    if personal is not None:
        data = _merge(data, _read(personal))
    names = {name for agent in _agents_for_env(data).values() for name in agent.env}
    return {name for name in names if name not in _SKIPPED_NAMES and not name.startswith("GIT_")}


def _agents_for_env(data: dict[str, object]) -> dict[str, Agent]:
    """agents の形だけを検査する。workflows の担当・fallback は後段に任せる。"""
    _reject_removed_runtime(data)
    try:
        loaded = Config.model_validate({"schema_version": 1, "agents": data.get("agents", {})})
    except ValidationError as error:
        raise ConfigError(_validation_category(error)) from None
    return loaded.agents


def _parsed_value(match: re.Match[str]) -> str:
    double = match.group("double")
    if double is not None:
        return double
    single = match.group("single")
    if single is not None:
        return single
    bare = match.group("bare")
    return bare if bare is not None else ""


def _tilde_unparsable(line: str, value: str) -> bool:
    """値が ~ で始まる、または行に :~ がある。文字どおり渡すとシェルと違う値になりうる。"""
    return value.startswith("~") or ":~" in line


def parse_assignments(text: str, names: set[str]) -> tuple[dict[str, str], list[str]]:
    """改行だけで区切って静的に読む。解析できない再代入は、その名前の候補をすべて捨てる。"""
    values: dict[str, str] = {}
    skipped: set[str] = set()
    # shell は \n だけで行を区切る。splitlines() は U+2028 等でも切れて別の値になる。
    for raw_line in text.split("\n"):
        line = raw_line.removesuffix("\r")
        looked = _LOOKS_LIKE.match(line)
        if looked is None or looked.group("name") not in names:
            continue
        name = looked.group("name")
        parsed = _ASSIGNMENT.fullmatch(line)
        value = _parsed_value(parsed) if parsed is not None else None
        if value is None or _tilde_unparsable(line, value):
            # 通常のシェルは後の行を使う。前の literal を残すと別の key を送りうる。
            skipped.add(name)
            values.pop(name, None)
            continue
        if name in skipped:
            continue
        values[name] = value
    return values, sorted(skipped)


def fill_environment(
    environ: Mapping[str, str],
    names: set[str],
    source: Path,
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """今の環境、ランチャー環境の導出、source の順に、未設定・空の名前だけを補う。

    戻り値は (環境, ランチャーから導出した名前, source から補った名前,
    解析できず補わなかった名前)。今の環境に非空の値がある名前は上書きしない。
    ランチャーの導出は ``ANTHROPIC_BASE_URL`` の完全一致と、ASCII 英数字を含む
    ``ANTHROPIC_AUTH_TOKEN`` のときだけ行う。ファイルが無ければ何もしない。
    開けない・UTF-8 で読めないときは ``with_keys: cannot read <path>`` を stderr に
    出して補わない。値は出さない。
    """
    environment = dict(environ)
    # 今の環境に値がある名前は除く。別の値で上書きしない。
    pending = {name for name in names if not environment.get(name)}
    derived: list[str] = []
    derived_name = _LAUNCHER_BASE_URL_KEYS.get(environment.get("ANTHROPIC_BASE_URL", ""))
    auth_token = environment.get("ANTHROPIC_AUTH_TOKEN", "")
    if (
        derived_name is not None
        and derived_name in pending
        and _ASCII_ALNUM.search(auth_token) is not None
    ):
        environment[derived_name] = auth_token
        pending.remove(derived_name)
        derived.append(derived_name)
    if not pending:
        return environment, derived, [], []
    try:
        text = source.read_text(encoding="utf-8")
    except FileNotFoundError:
        return environment, derived, [], []
    except (OSError, UnicodeDecodeError):
        # 例外文はファイルの断片を含みうる。値は出さず、読めないことだけを出す。
        print(f"with_keys: cannot read {source}", file=sys.stderr)
        return environment, derived, [], []
    assignments, skipped = parse_assignments(text, pending)
    filled: list[str] = []
    for name in sorted(assignments):
        value = assignments[name]
        if name not in pending or not value:
            continue
        environment[name] = value
        filled.append(name)
    return environment, derived, filled, skipped


def _parse_args(arguments: Sequence[str]) -> tuple[Path | None, Path | None, list[str]]:
    try:
        separator = arguments.index("--")
    except ValueError:
        raise _Usage from None
    options = arguments[:separator]
    command = list(arguments[separator + 1 :])
    if not command:
        raise _Usage
    template: Path | None = None
    config: Path | None = None
    index = 0
    while index < len(options):
        option = options[index]
        if option not in {"--template", "--config"} or index + 1 >= len(options):
            raise _Usage
        value = Path(options[index + 1])
        if option == "--template":
            template = value
        else:
            config = value
        index += 2
    return template, config, command


def _personal(explicit: Path | None) -> Path | None:
    """--config が無ければ、runner と同じく存在する個人設定だけを重ねる。"""
    if explicit is not None:
        return explicit
    candidate = resolve_config_path()
    if candidate.exists() or candidate.is_symlink():
        return candidate
    return None


def _report_derived(names: Sequence[str]) -> None:
    for name in names:
        detail = f"with_keys: filled {name} from launcher environment (ANTHROPIC_BASE_URL)"
        print(detail, file=sys.stderr)


def _report_filled(names: Sequence[str], source: Path) -> None:
    if not names:
        return
    print(f"with_keys: filled {', '.join(names)} from {source}", file=sys.stderr)


def _report_skipped(names: Sequence[str], source: Path) -> None:
    for name in names:
        detail = f"with_keys: skipped {name} (unparsable assignment in {source})"
        print(detail, file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        template_arg, config_arg, command = _parse_args(arguments)
    except _Usage:
        print(USAGE, file=sys.stderr)
        return 2
    template = TEMPLATE if template_arg is None else template_arg
    try:
        names = needed_names(template, _personal(config_arg))
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 2
    source = Path.home() / ".config/create-reso-world/env"
    environment, derived, filled, skipped = fill_environment(os.environ, names, source)
    _report_derived(derived)
    _report_skipped(skipped, source)
    _report_filled(filled, source)
    sys.stderr.flush()
    os.execvpe(command[0], command, environment)


if __name__ == "__main__":
    raise SystemExit(main())
