"""``lgrlw add-direction`` -- add a research direction to a monorepo umbrella."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw.commands.init import _materialise_subproject
from lgrlw.config import dump_config, load_config
from lgrlw.fs import ensure_dir
from lgrlw.monorepo import MONOREPO_DIR, MonorepoError, load_monorepo_config
from lgrlw.paths import PROJECT_MARKER, find_project_root
from lgrlw.schemas import PAPER_ID_PATTERN

console = Console()


def add_direction_command(
    direction: Annotated[
        str,
        typer.Argument(
            help="New direction slug. Becomes directions/<slug>/ under the monorepo umbrella.",
            show_default=False,
        ),
    ],
    root: Annotated[
        Path | None,
        typer.Option(
            "--root",
            help=(
                "Monorepo root (auto-detected upward from cwd if omitted). "
                "Must be a project that was created with `lgrlw init --monorepo`."
            ),
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help=(
                "Replace any pre-existing directions/<slug>/ skeleton. The umbrella's "
                "directions list is updated in either case."
            ),
        ),
    ] = False,
) -> None:
    """Materialise a new direction subproject inside an existing monorepo.

    The umbrella ``.lgrlw.toml``'s ``directions`` array is appended to in
    the same atomic update; the new subproject under
    ``directions/<slug>/`` is built from the same single-direction
    template that ``lgrlw init`` uses.
    """
    if not PAPER_ID_PATTERN.fullmatch(direction):
        console.print(
            f"[red]error[/red] invalid direction slug {direction!r}; "
            f"must match {PAPER_ID_PATTERN.pattern}"
        )
        raise typer.Exit(code=1)

    if root is not None:
        umbrella_root = root.resolve()
        if not (umbrella_root / PROJECT_MARKER).is_file():
            console.print(
                f"[red]error[/red] {umbrella_root} is not a Research-Wiki project "
                f"(missing {PROJECT_MARKER})"
            )
            raise typer.Exit(code=1)
    else:
        try:
            umbrella_root = find_project_root(Path.cwd())
        except FileNotFoundError as exc:
            console.print(f"[red]error[/red] {exc}")
            raise typer.Exit(code=1) from exc

    try:
        cfg = load_monorepo_config(umbrella_root)
    except MonorepoError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    sub_root = umbrella_root / MONOREPO_DIR / direction
    sub_marker = sub_root / PROJECT_MARKER

    if direction in cfg.directions and sub_marker.is_file() and not force:
        console.print(
            f"[red]error[/red] direction {direction!r} already registered at {sub_root}; "
            "re-run with --force to overwrite"
        )
        raise typer.Exit(code=1)

    ensure_dir(sub_root)
    _materialise_subproject(sub_root, direction)

    if direction not in cfg.directions:
        cfg = cfg.model_copy(update={"directions": [*cfg.directions, direction]})
    else:
        # Force re-add: keep ordering deterministic (existing position).
        cfg = load_config(umbrella_root / PROJECT_MARKER)
    dump_config(cfg, umbrella_root / PROJECT_MARKER)

    console.print(f"[green]added[/green] direction [bold]{direction}[/bold]")
    console.print(f"  umbrella    : {umbrella_root / PROJECT_MARKER}")
    console.print(f"  subproject  : {sub_root}")
    console.print(f"  kb          : {sub_root / 'literature-kb'}")
    console.print(f"  workspaces  : {sub_root / 'research-workspaces'}")


__all__ = ["add_direction_command"]
