"""実環境の形をした共有 test fixture。

runner の担当（``AGENT_RUNNER_DEPTH=1``）の中でも偽の担当だけのテストを動かす fixture
（``tools.test_support.plugin``）と、改行・タブ・CRLF・非 ASCII を含む複数行の自由記述のサンプルを置く。
"""

from tools.test_support.texts import FINDING_CONTENT

__all__ = [
    "FINDING_CONTENT",
]
