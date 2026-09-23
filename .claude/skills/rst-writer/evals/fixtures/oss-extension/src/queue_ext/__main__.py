"""Allow ``python -m queue_ext`` to reach :func:`queue_ext.main`."""

import sys

from queue_ext import main

sys.exit(main())
