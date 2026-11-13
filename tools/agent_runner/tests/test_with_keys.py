"""wrapper が key を補いすぎたり、shell として評価したり、値を漏らしたりしないこと。

次の失敗はエラーにならずに損害が残る（S）。

- 今の環境の key を env ファイルの別の値で上書きすると、別のアカウントの key で外部へ要求を送る
- ランチャーの URL から別プロバイダの変数へ key を導出すると、別の送信先へ key を送る
- ランチャーの URL の部分一致や末尾スラッシュの正規化で key を導出すると、意図しない送信先へ key を送る
- ASCII 英数字を含まないトークンを導出すると、使えない key を子に渡して起動させる
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
    fake_f = "-".join(["fake", "maas", "launcher"])
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
        "ANTHROPIC_BASE_URL": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic",
        "ANTHROPIC_AUTH_TOKEN": fake_f,
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
    # ランチャーの URL と対応する 1 変数だけを、ランチャーのトークンから補う。
    assert environment["MAAS_ANTHROPIC_TOKEN"] == fake_f
    # 別プロバイダの URL から OLLAMA_API_KEY を導出すると、別の送信先へ key を送る。
    assert "OLLAMA_API_KEY" not in environment
    assert (
        "with_keys: filled MAAS_ANTHROPIC_TOKEN from launcher environment (ANTHROPIC_BASE_URL)"
        in completed.stderr
    )
    # 値がログに出ると、失敗していなくても秘密情報が残る。
    for secret in (fake_a, fake_b, fake_c, fake_d, fake_e, fake_f):
        assert secret not in completed.stderr
    assert "COMMANDCODE_API_KEY" in completed.stderr

    from tools.agent_runner.with_keys import TEMPLATE, fill_environment, needed_names

    names = needed_names(TEMPLATE, None)
    missing_env = tmp_path / "missing" / "env"
    # 前方一致や末尾スラッシュの正規化で導出すると、意図しない送信先へ key を送る。
    for base_url in ("https://ollama.com/v1", "https://ollama.com/"):
        env_a, derived_a, _, _ = fill_environment(
            {"ANTHROPIC_BASE_URL": base_url, "ANTHROPIC_AUTH_TOKEN": fake_f},
            names,
            missing_env,
        )
        assert derived_a == []
        assert "OLLAMA_API_KEY" not in env_a
        assert "COMMANDCODE_API_KEY" not in env_a

    # Ollama の URL から別プロバイダの変数を導出すると、別の送信先へ key を送る。
    env_o, derived_o, _, _ = fill_environment(
        {"ANTHROPIC_BASE_URL": "https://ollama.com", "ANTHROPIC_AUTH_TOKEN": fake_f},
        names,
        missing_env,
    )
    assert env_o["OLLAMA_API_KEY"] == fake_f
    assert derived_o == ["OLLAMA_API_KEY"]
    assert "COMMANDCODE_API_KEY" not in env_o

    # ASCII 英数字を含まないトークンを導出すると、使えない key で起動してしまう。
    env_b, derived_b, _, _ = fill_environment(
        {"ANTHROPIC_BASE_URL": "https://ollama.com", "ANTHROPIC_AUTH_TOKEN": "  \u00a0\ufeff\u3000"},
        names,
        missing_env,
    )
    assert derived_b == []
    assert "OLLAMA_API_KEY" not in env_b

    # 今の環境の値をランチャーの導出で上書きすると、別のアカウントの key で外部へ要求を送る。
    existing = "-".join(["fake", "maas", "existing"])
    env_c, derived_c, _, _ = fill_environment(
        {
            "MAAS_ANTHROPIC_TOKEN": existing,
            "ANTHROPIC_BASE_URL": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic",
            "ANTHROPIC_AUTH_TOKEN": fake_f,
        },
        names,
        missing_env,
    )
    assert env_c["MAAS_ANTHROPIC_TOKEN"] == existing
    assert derived_c == []

    # 導出済みの値を env ファイルの別値や解析不能な再代入で上書きすると、別の key を送りうる。
    opencode_bad_env = tmp_path / "opencode.env"
    opencode_bad_env.write_text(
        "\n".join(
            [
                f"OPENCODE_API_KEY={fake_b}",
                f'OPENCODE_API_KEY="$(touch {marker})"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    launcher_go = "-".join(["fake", "opencode", "launcher"])
    env_d, derived_d, _, skipped_d = fill_environment(
        {"ANTHROPIC_BASE_URL": "https://opencode.ai/zen/go", "ANTHROPIC_AUTH_TOKEN": launcher_go},
        names,
        opencode_bad_env,
    )
    assert env_d["OPENCODE_API_KEY"] == launcher_go
    assert derived_d == ["OPENCODE_API_KEY"]
    assert "OPENCODE_API_KEY" not in skipped_d

    launcher_deepinfra = "-".join(["fake", "deepinfra", "launcher"])
    env_e, derived_e, _, skipped_e = fill_environment(
        {
            "ANTHROPIC_BASE_URL": "https://api.deepinfra.com/anthropic",
            "ANTHROPIC_AUTH_TOKEN": launcher_deepinfra,
        },
        names,
        missing_env,
    )
    assert env_e["DEEPINFRA_TOKEN"] == launcher_deepinfra
    assert derived_e == ["DEEPINFRA_TOKEN"]
    assert "DEEPINFRA_TOKEN" not in skipped_e
