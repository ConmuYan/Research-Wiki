"""``lgrlw export-pack`` -- build a dated, immutable KB snapshot for a workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw.export.pack import build_export_pack
from lgrlw.paths import resolve_project

console = Console()


def export_pack_command(
    workspace: Annotated[
        str,
        typer.Argument(
            help="Workspace id (directory name under research-workspaces/).",
            show_default=False,
        ),
    ],
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root (auto-detect if omitted)."),
    ] = None,
) -> None:
    """Emit a ``literature-kb/06_Exports/<workspace>_<date>/`` pack with manifest."""
    paths = resolve_project(root)
    try:
        pack_dir = build_export_pack(paths, workspace)
    except FileNotFoundError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except FileExistsError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]export-pack[/green] {pack_dir.relative_to(paths.root)}")
    console.print(
        f"  mirror : {paths.workspace_kb_exports(workspace).relative_to(paths.root)}/{pack_dir.name}"
    )


__all__ = ["export_pack_command"]
