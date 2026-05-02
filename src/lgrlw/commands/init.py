"""``lgrlw init`` -- bootstrap a new Research-Wiki project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw._resources import templates_root
from lgrlw.config import dump_config
from lgrlw.fs import copy_tree, ensure_dir
from lgrlw.paths import PROJECT_MARKER
from lgrlw.schemas import ProjectConfig

console = Console()


def init_command(
    path: Annotated[
        Path,
        typer.Argument(
            help="Directory to initialise (created if missing).",
            show_default=False,
        ),
    ],
    direction: Annotated[
        str,
        typer.Option(
            "--direction",
            "-d",
            help="Short slug naming the research direction (e.g. efficient-llm-inference).",
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-initialise even if the target directory already has a .lgrlw.toml.",
        ),
    ] = False,
) -> None:
    """Create the three-space skeleton under ``path``.

    The skeleton contains a fully-populated ``literature-kb/`` (from the
    packaged template), an empty ``research-workspaces/`` container, and a
    ``.lgrlw.toml`` marker file.
    """
    target = path.resolve()
    marker = target / PROJECT_MARKER
    if marker.is_file() and not force:
        console.print(
            f"[red]error[/red] {target} already hosts a Research-Wiki project "
            f"({PROJECT_MARKER} present). Re-run with --force to overwrite."
        )
        raise typer.Exit(code=1)

    ensure_dir(target)

    tpl = templates_root()
    copy_tree(tpl / "literature-kb", target / "literature-kb")

    ws_dir = target / "research-workspaces"
    ensure_dir(ws_dir)
    readme = ws_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# research-workspaces/\n\n"
            'Create a new workspace with `lgrlw new-workspace <id> --title "..."`.\n'
            "See `docs/boundary-rules.md` for what may (and may not) live here.\n",
            encoding="utf-8",
        )

    dump_config(ProjectConfig(direction=direction), marker)

    console.print(f"[green]initialised[/green] Research-Wiki project at [bold]{target}[/bold]")
    console.print(f"  direction   : {direction}")
    console.print(f"  kb          : {target / 'literature-kb'}")
    console.print(f"  workspaces  : {ws_dir}")
    console.print(f"  config      : {marker}")


__all__ = ["init_command"]
