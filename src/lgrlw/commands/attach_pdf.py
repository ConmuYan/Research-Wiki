"""``lgrlw attach-pdf`` — archive a local PDF against an existing KB paper.

Two modes:

* explicit: ``lgrlw attach-pdf --id <paper-id> <pdf>``
* scan:     ``lgrlw attach-pdf --scan-dir <dir>`` or
            ``lgrlw attach-pdf --scan-incoming``

Both are offline and deterministic. Fuzzy title matching is deferred to
a later release; today's matcher is purely identifier-based.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lgrlw.ingest.attach import (
    AttachOutcome,
    attach_scan,
    attach_single,
)
from lgrlw.monorepo import MonorepoError, resolve_subproject

console = Console()


def attach_pdf_command(
    pdf: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "Path to a local PDF. Required with --id; rejected when "
                "--scan-dir or --scan-incoming is used."
            ),
            exists=False,
            dir_okay=False,
        ),
    ] = None,
    paper_id: Annotated[
        str | None,
        typer.Option(
            "--id",
            help="KB paper id. Enables single-paper mode together with <pdf>.",
        ),
    ] = None,
    scan_dir: Annotated[
        Path | None,
        typer.Option(
            "--scan-dir",
            help=(
                "Scan this directory for *.pdf files and match each against "
                "the KB by filename (paper-id / arXiv id / DOI)."
            ),
        ),
    ] = None,
    scan_incoming: Annotated[
        bool,
        typer.Option(
            "--scan-incoming",
            help=(
                "Shortcut for scanning literature-kb/01_Raw/pdf/_incoming/. "
                "Mutually exclusive with --scan-dir."
            ),
        ),
    ] = False,
    force_pdf: Annotated[
        bool,
        typer.Option(
            "--force-pdf",
            help="Replace an existing archived PDF with the same paper id.",
        ),
    ] = False,
    move: Annotated[
        bool,
        typer.Option(
            "--move",
            help=("Delete the source PDF after a successful archive. Defaults to false (copy)."),
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
    """Archive a local PDF under ``literature-kb/01_Raw/pdf/<id>.pdf``."""
    if scan_dir is not None and scan_incoming:
        console.print("[red]error[/red] --scan-dir and --scan-incoming are mutually exclusive")
        raise typer.Exit(code=1)

    try:
        paths = resolve_subproject(root, direction)
    except MonorepoError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # Determine mode.
    if paper_id is not None or pdf is not None:
        if paper_id is None or pdf is None:
            console.print("[red]error[/red] --id requires a positional PDF path, and vice versa")
            raise typer.Exit(code=1)
        if scan_dir is not None or scan_incoming:
            console.print(
                "[red]error[/red] single-paper mode is incompatible with --scan-dir / --scan-incoming"
            )
            raise typer.Exit(code=1)
        outcome = attach_single(
            paths,
            paper_id=paper_id,
            pdf_path=pdf,
            force_pdf=force_pdf,
            remove_source=move,
        )
        _print_outcomes([outcome], root=paths.root)
        if outcome.status == "skipped_error":
            raise typer.Exit(code=1)
        return

    if scan_incoming:
        scan_dir = paths.kb_raw_pdf_incoming
    if scan_dir is None:
        console.print(
            "[red]error[/red] provide either --id <paper-id> <pdf> or --scan-dir <dir> "
            "(or --scan-incoming)"
        )
        raise typer.Exit(code=1)

    try:
        results = attach_scan(
            paths,
            scan_dir,
            force_pdf=force_pdf,
            remove_source=move,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_outcomes(results, root=paths.root)

    # Non-zero exit only on hard errors; "unmatched" is informational.
    if any(r.status == "skipped_error" for r in results):
        raise typer.Exit(code=1)


def _print_outcomes(results: list[AttachOutcome], *, root: Path) -> None:
    table = Table(title="attach-pdf", show_lines=False)
    table.add_column("source")
    table.add_column("status")
    table.add_column("paper_id")
    table.add_column("reason")
    table.add_column("archive")
    for result in results:
        try:
            source_display = str(result.source.relative_to(root))
        except ValueError:
            source_display = result.source.name
        archive_display = (
            str(result.archived.relative_to(root)) if result.archived is not None else "-"
        )
        table.add_row(
            source_display,
            result.status,
            result.paper_id or "-",
            result.reason,
            archive_display,
        )
    console.print(table)
    for result in results:
        if result.status == "skipped_error" and result.error:
            console.print(f"[red]{result.source.name}[/red] {result.error}")
        elif (result.status == "already_attached" and result.error) or result.status == "unmatched":
            console.print(f"[yellow]{result.source.name}[/yellow] {result.error}")


__all__ = ["attach_pdf_command"]
