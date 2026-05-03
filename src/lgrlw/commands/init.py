"""``lgrlw init`` -- bootstrap a new Research-Wiki project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw._resources import templates_root
from lgrlw.config import dump_config
from lgrlw.fs import copy_tree, ensure_dir
from lgrlw.monorepo import MONOREPO_DIR
from lgrlw.paths import PROJECT_MARKER
from lgrlw.schemas import PAPER_ID_PATTERN, ProjectConfig

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
    monorepo: Annotated[
        bool,
        typer.Option(
            "--monorepo",
            help=(
                "Create a multi-direction monorepo umbrella. The initial "
                "--direction becomes the first subproject under "
                "directions/<slug>/; further directions can be added with "
                "`lgrlw add-direction <slug>`."
            ),
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-initialise even if the target directory already has a .lgrlw.toml.",
        ),
    ] = False,
) -> None:
    """Create the three-space skeleton under ``path``.

    Without ``--monorepo`` (the v0.1/v0.2 layout), the skeleton contains
    a fully-populated ``literature-kb/``, an empty ``research-workspaces/``,
    and a ``.lgrlw.toml`` marker.

    With ``--monorepo`` (v0.3), the skeleton contains a
    ``directions/<direction>/`` subproject (built from the same single-
    direction template) and an umbrella ``.lgrlw.toml`` at the root that
    declares ``monorepo = true`` and lists every direction.
    """
    if not PAPER_ID_PATTERN.fullmatch(direction):
        console.print(
            f"[red]error[/red] invalid --direction slug {direction!r}; "
            f"must match {PAPER_ID_PATTERN.pattern}"
        )
        raise typer.Exit(code=1)

    target = path.resolve()
    marker = target / PROJECT_MARKER
    if marker.is_file() and not force:
        console.print(
            f"[red]error[/red] {target} already hosts a Research-Wiki project "
            f"({PROJECT_MARKER} present). Re-run with --force to overwrite."
        )
        raise typer.Exit(code=1)

    ensure_dir(target)

    if monorepo:
        sub_root = target / MONOREPO_DIR / direction
        if (sub_root / PROJECT_MARKER).is_file() and not force:
            console.print(
                f"[red]error[/red] direction {direction!r} already exists at {sub_root}; "
                "re-run with --force to overwrite"
            )
            raise typer.Exit(code=1)
        ensure_dir(sub_root)
        _materialise_subproject(sub_root, direction)
        umbrella_cfg = ProjectConfig(
            schema_version="1.1.0",
            direction=direction,
            monorepo=True,
            directions=[direction],
        )
        dump_config(umbrella_cfg, marker)

        console.print(f"[green]initialised[/green] Research-Wiki monorepo at [bold]{target}[/bold]")
        console.print(f"  umbrella    : {marker}")
        console.print(f"  direction   : {direction}")
        console.print(f"  subproject  : {sub_root}")
        console.print(f"  kb          : {sub_root / 'literature-kb'}")
        console.print(f"  workspaces  : {sub_root / 'research-workspaces'}")
        console.print("[dim]hint[/dim] add another direction with `lgrlw add-direction <slug>`.")
        return

    _materialise_subproject(target, direction)
    console.print(f"[green]initialised[/green] Research-Wiki project at [bold]{target}[/bold]")
    console.print(f"  direction   : {direction}")
    console.print(f"  kb          : {target / 'literature-kb'}")
    console.print(f"  workspaces  : {target / 'research-workspaces'}")
    console.print(f"  config      : {marker}")


def _materialise_subproject(root: Path, direction: str) -> None:
    """Populate ``root`` with the standard single-direction skeleton.

    Used both by ``lgrlw init`` (without ``--monorepo`` for the legacy
    layout, with ``--monorepo`` for the first child subproject) and by
    ``lgrlw add-direction`` to create additional direction subprojects.
    """
    ensure_dir(root)
    tpl = templates_root()
    copy_tree(tpl / "literature-kb", root / "literature-kb")

    ws_dir = root / "research-workspaces"
    ensure_dir(ws_dir)
    readme = ws_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# research-workspaces/\n\n"
            'Create a new workspace with `lgrlw new-workspace <id> --title "..."`.\n'
            "See `docs/boundary-rules.md` for what may (and may not) live here.\n",
            newline="\n",
            encoding="utf-8",
        )

    dump_config(ProjectConfig(direction=direction), root / PROJECT_MARKER)


__all__ = ["init_command"]
