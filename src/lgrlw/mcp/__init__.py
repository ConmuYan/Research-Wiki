"""Optional Model Context Protocol server for Research-Wiki.

Install the optional dependency with ``pip install "lgrlw[mcp]"`` and
start the stdio server with ``lgrlw mcp serve``.
"""

from __future__ import annotations

from lgrlw.mcp.server import create_server, run_stdio_server

__all__ = ["create_server", "run_stdio_server"]
