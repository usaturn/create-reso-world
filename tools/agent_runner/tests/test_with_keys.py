"""wrapper が key を補いすぎたり、shell として評価したり、値を漏らしたりしないこと。

次の失敗はエラーにならずに損害が残る（S）。

- 今の環境の key を env ファイルの別の値で上書きすると、別のアカウントの key で外部へ要求を送る
- agent の env に無い名前を子に渡すと、allowlist の外の秘密情報が runner に入る
- env ファイルの行を実行すると、ファイルの記述がコマンドとして動く
- 補った値を stderr に出すと、値がログに残る
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPER = ROOT / "tools/agent_runner/with_keys.py"


def test_wrapper_fills_missing_allowlisted_names_only(tmp_path: Path) -> None:
    home = tmp_path / "home"
    env_file = home / ".config/create-reso-world/env"
    env_file.parent.mkdir(parents=True)
    marker = tmp_path / "marker"
    # 偽の値はソースに連結した文字列を残さない（gitleaks）。
    fake_a = "-".join(["fake", "commandcode", "value"])
    fake_b = "-".join(["fake", "opencode", "file"])
    fake_c = "-".join(["fake", "meshy", "value"])
    fake_d = "-".join(["fake", "opencode", "env"])
    fake_e = "-".join(["fake", "deepinfra", "value"])
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "",
                f"COMMANDCODE_API_KEY={fake_a}",
                f'export OPENCODE_API_KEY="{fake_b}"',
                f"MESHY_API_KEY='{fake_c}'",
                f"DEEPINFRA_TOKEN={fake_e}",
                f'DEEPINFRA_TOKEN="$(touch {marker})"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    # 存在しない個人設定を明示し、利用者の config を読まない。
    child_env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "AGENT_RUNNER_CONFIG": str(tmp_path / "missing" / "config.toml"),
        "OPENCODE_API_KEY": fake_d,
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            "--",
            sys.executable,
            "-c",
            "import json, os; print(json.dumps(dict(os.environ)))",
        ],
        env=child_env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    environment = json.loads(completed.stdout)
    # 雛形の env にある名前は、今の環境に無ければ子に届く。
    assert environment["COMMANDCODE_API_KEY"] == fake_a
    # 上書きすると別のアカウントの key で外部へ要求を送るが、エラーにはならない。
    assert environment["OPENCODE_API_KEY"] == fake_d
    # allowlist の外の秘密情報は、env ファイルにあっても runner に入れない。
    assert "MESHY_API_KEY" not in environment
    # 解析できない再代入の前の literal に戻すと、別の key を送りうる。実行もしない。
    assert "DEEPINFRA_TOKEN" not in environment
    assert not marker.exists()
    # 値がログに出ると、失敗していなくても秘密情報が残る。
    for secret in (fake_a, fake_b, fake_c, fake_d, fake_e):
        assert secret not in completed.stderr
    assert "COMMANDCODE_API_KEY" in completed.stderr
