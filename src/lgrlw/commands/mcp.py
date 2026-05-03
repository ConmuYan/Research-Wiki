"""``lgrlw mcp serve`` -- run the Model Context Protocol server (v0.3).

This module ships with the core ``lgrlw`` install but the MCP server
itself depends on the optional ``mcp`` Python SDK. Users who want it
should install the ``mcp`` extra::

    pip install "lgrlw[mcp]"

The ``mcp_app`` Typer sub-application is always registered on the main
CLI so ``lgrlw mcp --help`` works even if the SDK is missing; trying to
actually start the server without the SDK prints a friendly error and
exits non-zero.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()

try:
    from lgrlw.mcp.server import run_stdio_server as _imported_run_stdio_server
except ImportError:  # pragma: no cover - exercised only when extra missing
    _RUN_STDIO_SERVER: Callable[[Path | None], None] | None = None
else:
    _RUN_STDIO_SERVER = _imported_run_stdio_server

mcp_app = typer.Typer(
    name="mcp",
    help=(
        "Model Context Protocol server for Research-Wiki "
        '(optional; install with `pip install "lgrlw\\[mcp]"`).'
    ),
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@mcp_app.command("serve", help="Run the Research-Wiki MCP server over stdio.")
def mcp_serve_command(
    root: Annotated[
        Path | None,
        typer.Option(
            "--root",
            help=(
                "Default Research-Wiki project root for tools that operate on an existing "
                "project. Tools also accept a per-call `root` argument that overrides this. "
                "Auto-detected upward from cwd when omitted."
            ),
        ),
    ] = None,
) -> None:
    """Start the MCP server on stdio.

    The server exposes every CLI command (``init``, ``new_workspace``,
    ``add_literature``, ``export_pack``, ``promote``, ``lint``,
    ``add_direction``) as MCP tools, and the project's KB papers and
    workspaces as MCP resources. See ``docs/mcp-server.md`` for the full
    tool/resource catalogue.
    """
    if _RUN_STDIO_SERVER is None:
        console.print(
            "[red]error[/red] the MCP server requires the optional `mcp` package. "
            'install with: pip install "lgrlw[mcp]"'
        )
        raise typer.Exit(code=1)

    _RUN_STDIO_SERVER(root)


__all__ = ["mcp_app", "mcp_serve_command"]
