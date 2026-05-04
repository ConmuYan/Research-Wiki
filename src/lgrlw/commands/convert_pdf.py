"""``lgrlw convert-pdf`` — render archived PDFs into Markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lgrlw.convert import list_backends
from lgrlw.convert.run import (
    ConvertOutcome,
    convert_paper,
    list_paper_ids_with_pdf,
)
from lgrlw.monorepo import MonorepoError, resolve_subproject

console = Console()


def convert_pdf_command(
    paper_id: Annotated[
        str | None,
        typer.Argument(
            help=("KB paper id. If omitted, either --all must be set, or the command errors out."),
        ),
    ] = None,
    all_papers: Annotated[
        bool,
        typer.Option(
            "--all",
            help=("Convert every paper that has an archived PDF under literature-kb/01_Raw/pdf/."),
        ),
    ] = False,
    backend: Annotated[
        str,
        typer.Option(
            "--backend",
            help=(
                "Converter backend name. `stub` is always available and ships "
                "a placeholder Markdown file. `mineru` requires "
                'pip install "lgrlw[mineru]".'
            ),
        ),
    ] = "stub",
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace an existing output directory for the same paper id.",
        ),
    ] = False,
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root (auto-detect if omitted)."),
    ] = None,
    direction: Annotated[
        str | None,
        typer.Option(
            "--direction",
            help="Monorepo direction slug when --root points at an umbrella.",
        ),
    ] = None,
) -> None:
    """Convert archived PDFs to Markdown using a pluggable backend."""
    available = list_backends()
    if backend not in available:
        console.print(f"[red]error[/red] unknown backend {backend!r}; available: {available}")
        raise typer.Exit(code=1)

    if paper_id is None and not all_papers:
        console.print(
            "[red]error[/red] provide a <paper-id> or --all to convert every paper with a PDF"
        )
        raise typer.Exit(code=1)
    if paper_id is not None and all_papers:
        console.print("[red]error[/red] <paper-id> and --all are mutually exclusive")
        raise typer.Exit(code=1)

    try:
        paths = resolve_subproject(root, direction)
    except MonorepoError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if all_papers:
        ids = list_paper_ids_with_pdf(paths)
        if not ids:
            console.print("[yellow]no archived PDFs found under 01_Raw/pdf/[/yellow]")
            return
    else:
        assert paper_id is not None
        ids = [paper_id]

    outcomes = [convert_paper(paths, paper_id=pid, backend=backend, force=force) for pid in ids]
    _print_outcomes(outcomes, root=paths.root)

    if any(o.status == "skipped_error" for o in outcomes):
        raise typer.Exit(code=1)


def _print_outcomes(outcomes: list[ConvertOutcome], *, root: Path) -> None:
    table = Table(title="convert-pdf", show_lines=False)
    table.add_column("paper_id")
    table.add_column("backend")
    table.add_column("status")
    table.add_column("markdown")
    for outcome in outcomes:
        markdown_display = "-"
        if outcome.markdown_path is not None:
            try:
                markdown_display = str(outcome.markdown_path.relative_to(root))
            except ValueError:
                markdown_display = outcome.markdown_path.name
        table.add_row(
            outcome.paper_id,
            outcome.backend,
            outcome.status,
            markdown_display,
        )
    console.print(table)
    for outcome in outcomes:
        if outcome.status == "skipped_error" and outcome.error:
            console.print(f"[red]{outcome.paper_id}[/red] {outcome.error}")
        elif outcome.status in {"skipped_exists", "skipped_no_pdf"} and outcome.error:
            console.print(f"[yellow]{outcome.paper_id}[/yellow] {outcome.error}")


__all__ = ["convert_pdf_command"]
