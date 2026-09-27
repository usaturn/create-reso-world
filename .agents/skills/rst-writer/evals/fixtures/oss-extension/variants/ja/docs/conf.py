import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "Queue Extension"
author = "Queue Extension maintainers"
release = "0.2.0"
extensions = ["queue_ext", "sphinx.ext.autodoc"]
needs_sphinx = "9.1"
language = "ja"
root_doc = "index"
html_theme = "basic"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
