"""`tools.test_support` の pytest fixture。

利用側の test module で ``pytest_plugins = ("tools.test_support.plugin",)``
を宣言して読み込む。

ここの fixture は autouse にしない。test module で読み込んだプラグインの fixture は
テスト一式から見え、autouse だと読み込んだ後に収集したモジュールにも効く。
"""

from __future__ import annotations

import pytest


@pytest.fixture
def outside_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストの中だけ ``AGENT_RUNNER_DEPTH`` を外し、runner の担当の中でもテストを実行できるようにする。

    runner は担当に ``AGENT_RUNNER_DEPTH=1`` を付け、``run_workflow`` と CLI はそれを見て
    ``nested_invocation`` で止まる（入れ子の防止）。偽の adapter・偽の CLI だけを起動するテストも
    本物の ``run_workflow`` を通るので、担当が関連テストを実行すると検査したい挙動の前に落ちる。

    偽の担当だけを起動する test module が、モジュール単位で明示して使う::

        pytest_plugins = ("tools.test_support.plugin",)
        pytestmark = pytest.mark.usefixtures("outside_runner")

    本物の担当を起動しうるテストには使わない。入れ子の防止そのものを確かめるテストは、
    テストの中で ``AGENT_RUNNER_DEPTH`` を設定し直すので、この fixture を使うモジュールでも通る。
    """
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)
