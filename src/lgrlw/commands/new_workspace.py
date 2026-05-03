"""``lgrlw new-workspace`` -- create a new research workspace."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw._resources import templates_root
from lgrlw.fs import copy_tree, read_frontmatter, write_frontmatter
from lgrlw.monorepo import MonorepoError, resolve_subproject
from lgrlw.schemas import (
    WORKSPACE_ID_PATTERN,
    WorkspaceKind,
    WorkspacePaperFrontmatter,
    WorkspaceStatus,
)

console = Console()


def new_workspace_command(
    name: Annotated[
        str,
        typer.Argument(
            help="Workspace id / slug (e.g. paper_001, idea_selfrag_variants).",
            show_default=False,
        ),
    ],
    title: Annotated[
        str,
        typer.Option(
            "--title",
            help="Working title of the paper or idea.",
        ),
    ],
    kind: Annotated[
        WorkspaceKind,
        typer.Option(
            "--kind",
            help="Workspace kind. Selects the template under templates/research-workspace/.",
        ),
    ] = WorkspaceKind.paper,
    root: Annotated[
        Path | None,
        typer.Option(
            "--root",
            help="Project root (auto-detected if omitted).",
        ),
    ] = None,
    direction: Annotated[
        str | None,
        typer.Option(
            "--direction",
            help=(
                "Monorepo direction slug. Required when --root points at a monorepo "
                "umbrella; ignored otherwise."
            ),
        ),
    ] = None,
) -> None:
    """Create a new workspace under ``research-workspaces/<name>/``.

    For ``--kind paper`` the generated workspace contains the S3-S8 lifecycle
    directories and a pre-filled ``paper_status.md`` with frontmatter.
    """
    if not WORKSPACE_ID_PATTERN.fullmatch(name):
        console.print(f"[red]error[/red] invalid workspace id {name!r}")
        raise typer.Exit(code=1)
    if not title.strip():
        console.print("[red]error[/red] --title must not be empty")
        raise typer.Exit(code=1)

    try:
        paths = resolve_subproject(root, direction)
    except MonorepoError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc
    dst = paths.workspace(name)
    if dst.exists():
        console.print(f"[red]error[/red] workspace already exists: {dst}")
        raise typer.Exit(code=1)

    tpl = templates_root() / "research-workspace" / kind.value
    if not tpl.is_dir():
        console.print(
            f"[red]error[/red] no workspace template for kind {kind.value!r} (expected {tpl})"
        )
        raise typer.Exit(code=1)

    copy_tree(tpl, dst)

    if kind == WorkspaceKind.paper:
        status_path = dst / "00_Project" / "paper_status.md"
        _, body = read_frontmatter(status_path)
        fm = WorkspacePaperFrontmatter(
            id=name,
            kind=kind,
            title=title,
            status=WorkspaceStatus.drafting,
            created_on=date.today(),
        )
        write_frontmatter(status_path, fm.model_dump(mode="json", exclude_none=True), body)

    console.print(
        f"[green]created[/green] workspace "
        f"[bold]{dst.relative_to(paths.root)}[/bold] (kind={kind.value})"
    )


__all__ = ["new_workspace_command"]
