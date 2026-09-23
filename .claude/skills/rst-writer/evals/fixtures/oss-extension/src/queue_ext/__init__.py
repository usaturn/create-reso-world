"""Fictional Sphinx extension used by the rst-writer eval fixtures."""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.states import Inliner
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

__version__ = "0.2.0"

__all__ = ["format_badge", "main", "setup"]

_LOG = logging.getLogger(__name__)


def format_badge(name: str, prefix: str = "task") -> str:
    """Return a label; reject an empty or whitespace-only name."""
    value = name.strip()
    if not value:
        raise ValueError("name must not be blank")
    return f"{prefix}:{value}"


class QueueSummaryDirective(Directive):
    """Show the first ``max-items`` lines of the directive body."""

    required_arguments = 1
    has_content = True
    option_spec: ClassVar[dict[str, Any]] = {"max-items": directives.nonnegative_int}

    def run(self) -> list[nodes.Node]:
        queue_name = self.arguments[0]
        max_items: int = self.options.get("max-items", 3)
        lines = [line.strip() for line in self.content if line.strip()]
        shown = lines[:max_items]

        title = nodes.paragraph()
        title += nodes.Text("Queue ")
        title += nodes.literal(text=queue_name)
        title += nodes.Text(f" summary ({len(shown)} of {len(lines)} entries):")

        result: list[nodes.Node] = [title]
        if shown:
            listing = nodes.bullet_list()
            for line in shown:
                item = nodes.list_item()
                item += nodes.paragraph(text=line)
                listing += item
            result.append(listing)
        return result


def queue_name_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner,
    options: dict[str, Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Render the given queue name as an inline literal."""
    return [nodes.literal(rawtext, text)], []


def main(argv: list[str] | None = None) -> int:
    """Console entry point for inspecting queue summaries."""
    parser = argparse.ArgumentParser(prog="queue-ext")
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        metavar="N",
        help="maximum number of entries to show",
    )
    args = parser.parse_args(argv)
    if os.environ.get("QUEUE_EXT_DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
    _LOG.debug("resolved limit=%s", args.limit)
    print(f"limit={args.limit}")
    return 0


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register config values, the queue-summary directive, and the role."""
    app.add_config_value("queue_limit", 3, "env", [int])
    app.add_config_value("queue_prefix", "task", "env", [str])
    app.add_directive("queue-summary", QueueSummaryDirective)
    app.add_role("queue-name", queue_name_role)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
