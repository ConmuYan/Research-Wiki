"""``lgrlw import-bib`` -- batch-create KB paper cards from a BibTeX file.

The command parses a ``.bib`` file, detects duplicates against the
current KB, optionally matches each entry against a local PDF directory,
and writes a canonical import manifest under
``literature-kb/01_Raw/imports/<run_id>/``. No network calls are made;
per-entry metadata comes from the BibTeX fields themselves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lgrlw.ingest import BibtexParseError
from lgrlw.ingest.manifest import ImportEntryStatus, ImportManifest
from lgrlw.ingest.run import (
    ImportBibError,
    ImportBibRequest,
    OnDuplicate,
    run_import_bib,
)
from lgrlw.monorepo import MonorepoError, resolve_subproject
from lgrlw.schemas import PaperStatus

console = Console()


def import_bib_command(
    bib_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the BibTeX file to import.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root (auto-detect if omitted)."),
    ] = None,
    direction: Annotated[
        str | None,
        typer.Option(
            "--direction",
            help="Monorepo direction slug when --root points at a monorepo umbrella.",
        ),
    ] = None,
    pdf_dir: Annotated[
        Path | None,
        typer.Option(
            "--pdf-dir",
            help=(
                "Local directory to scan for PDFs. Matched by arXiv id, cite key, or "
                "paper-id slug in the filename (substring, case-insensitive)."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Parse and plan without writing anything. The returned manifest is "
                "printed but not persisted."
            ),
        ),
    ] = False,
    on_duplicate: Annotated[
        str,
        typer.Option(
            "--on-duplicate",
            help="How to treat papers already present in the KB: skip|force|fail.",
            case_sensitive=False,
        ),
    ] = "skip",
    default_status: Annotated[
        PaperStatus,
        typer.Option(
            "--default-status",
            help="Publication status applied to each new paper card.",
        ),
    ] = PaperStatus.published,
    tags: Annotated[
        str | None,
        typer.Option(
            "--tags",
            help="Comma-separated tags applied to every created paper card.",
        ),
    ] = None,
) -> None:
    """Create KB paper cards for every entry in a BibTeX file."""
    normalised = on_duplicate.lower()
    if normalised not in ("skip", "force", "fail"):
        console.print("[red]error[/red] --on-duplicate must be one of skip|force|fail")
        raise typer.Exit(code=1)
    mode: OnDuplicate = normalised  # type: ignore[assignment]

    try:
        paths = resolve_subproject(root, direction)
    except MonorepoError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    tag_list = tuple(t.strip() for t in (tags or "").split(",") if t.strip())
    request = ImportBibRequest(
        bib_path=bib_file,
        pdf_dir=pdf_dir,
        dry_run=dry_run,
        on_duplicate=mode,
        default_status=default_status,
        tags=tag_list,
        direction=direction,
    )

    try:
        result = run_import_bib(paths, request)
    except BibtexParseError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ImportBibError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_summary(result.manifest, dry_run=dry_run)

    if not dry_run and result.manifest_path is not None:
        console.print(f"[green]manifest[/green] {result.manifest_path.relative_to(paths.root)}")

    if any(row.status == ImportEntryStatus.skipped_error for row in result.manifest.entries):
        raise typer.Exit(code=1)


def _print_summary(manifest: ImportManifest, *, dry_run: bool) -> None:
    counts = manifest.counts
    table = Table(title="BibTeX import" + (" (dry run)" if dry_run else ""), show_lines=False)
    table.add_column("cite_key")
    table.add_column("status")
    table.add_column("mode")
    table.add_column("paper_id")
    table.add_column("pdf")
    for row in manifest.entries:
        pdf_display = "local" if row.pdf_source == "local" else "-"
        table.add_row(
            row.cite_key or "-",
            row.status.value,
            row.mode or "-",
            row.paper_id or "-",
            pdf_display,
        )
    console.print(table)

    summary = ", ".join(f"{k}={v}" for k, v in counts.items() if v or k == "total")
    console.print(f"[cyan]summary[/cyan] {summary}")


__all__ = ["import_bib_command"]
