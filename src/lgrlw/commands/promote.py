"""``lgrlw promote`` -- promote an accepted workspace paper into the KB."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from lgrlw.paths import resolve_project
from lgrlw.promote import PromoteError, promote_workspace

console = Console()


def promote_command(
    workspace: Annotated[
        str,
        typer.Argument(
            help="Workspace id (directory name under research-workspaces/).",
            show_default=False,
        ),
    ],
    paper_id: Annotated[
        str | None,
        typer.Option("--id", help="Override the auto-generated KB paper id slug."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite an existing paper card / metadata / bibtex with the same id.",
        ),
    ] = False,
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root (auto-detect if omitted)."),
    ] = None,
) -> None:
    """Promote ``workspace`` from `accepted` workspace status into the KB.

    All preconditions in ``docs/promotion-protocol.md`` are enforced first;
    if any fails the command exits non-zero and writes nothing. On success,
    four artefacts are produced:

    * ``literature-kb/02_Literature/Papers/<id>.md``
    * ``literature-kb/01_Raw/metadata/<id>.json``
    * ``literature-kb/01_Raw/bibtex/<id>.bib``
    * an appended line in ``literature-kb/00_System/log.md``
    """
    paths = resolve_project(root)
    try:
        result = promote_workspace(
            paths,
            workspace,
            paper_id=paper_id,
            force=force,
        )
    except PromoteError as exc:
        # Promote error messages can legitimately contain literal bracketed
        # tokens like `[x]` / `[ ]` when describing checklist checkbox
        # syntax; escape them so Rich does not interpret them as markup.
        console.print(f"[red]error[/red] {escape(str(exc))}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]promoted[/green] {result.paper_id}")
    console.print(f"  card     : {result.paper_card.relative_to(paths.root)}")
    console.print(f"  metadata : {result.metadata_json.relative_to(paths.root)}")
    console.print(f"  bibtex   : {result.bibtex.relative_to(paths.root)}")
    console.print(f"  log      : {result.log.relative_to(paths.root)}")
    console.print(
        "[yellow]reminder[/yellow] apply the field-structure / evidence-map edits "
        "described in 06_Promotion/add_back_to_kb_plan.md as a follow-up commit; "
        "`lgrlw promote` does not do this automatically."
    )


__all__ = ["promote_command"]
