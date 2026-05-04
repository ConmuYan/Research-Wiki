"""Orchestrator used by ``lgrlw convert-pdf`` and MCP ``convert_pdf``."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from lgrlw.convert.base import (
    ConversionResult,
    ConverterError,
    ConverterUnavailableError,
    get_converter,
)
from lgrlw.fs import ensure_dir
from lgrlw.paths import ProjectPaths

ConvertStatus = Literal["converted", "skipped_exists", "skipped_no_pdf", "skipped_error"]


@dataclass(frozen=True)
class ConvertOutcome:
    """Per-paper result of a convert-pdf run."""

    paper_id: str
    backend: str
    status: ConvertStatus
    output_dir: Path | None
    markdown_path: Path | None
    source_pdf: Path | None
    error: str | None = None


def convert_paper(
    paths: ProjectPaths,
    *,
    paper_id: str,
    backend: str,
    force: bool,
) -> ConvertOutcome:
    """Convert the archived PDF for ``paper_id`` via ``backend``.

    Returns a :class:`ConvertOutcome`. Does not raise for expected
    conditions (missing PDF, existing output without ``force``, backend
    unavailable) so batch callers can aggregate outcomes cleanly. A
    genuine :class:`ConverterError` from the backend is captured in
    ``error`` with ``status="skipped_error"``.
    """
    source_pdf = paths.kb_raw_pdf / f"{paper_id}.pdf"
    if not source_pdf.is_file():
        return ConvertOutcome(
            paper_id=paper_id,
            backend=backend,
            status="skipped_no_pdf",
            output_dir=None,
            markdown_path=None,
            source_pdf=None,
            error=f"no archived PDF at {source_pdf}",
        )

    output_dir = paths.kb_raw_mineru_md / paper_id
    if output_dir.exists() and not force:
        markdown = output_dir / f"{paper_id}.md"
        return ConvertOutcome(
            paper_id=paper_id,
            backend=backend,
            status="skipped_exists",
            output_dir=output_dir,
            markdown_path=markdown if markdown.is_file() else None,
            source_pdf=source_pdf,
            error="output already exists; re-run with --force to replace it",
        )

    # --force: wipe the previous output dir so backends that emit
    # multiple files do not get mixed with a previous run.
    if output_dir.exists() and force:
        shutil.rmtree(output_dir)

    try:
        converter = get_converter(backend)
    except ConverterError as exc:
        return ConvertOutcome(
            paper_id=paper_id,
            backend=backend,
            status="skipped_error",
            output_dir=None,
            markdown_path=None,
            source_pdf=source_pdf,
            error=str(exc),
        )

    try:
        result: ConversionResult = converter.convert(source_pdf, output_dir, paper_id=paper_id)
    except ConverterUnavailableError as exc:
        return ConvertOutcome(
            paper_id=paper_id,
            backend=backend,
            status="skipped_error",
            output_dir=None,
            markdown_path=None,
            source_pdf=source_pdf,
            error=str(exc),
        )
    except ConverterError as exc:
        return ConvertOutcome(
            paper_id=paper_id,
            backend=backend,
            status="skipped_error",
            output_dir=output_dir,
            markdown_path=None,
            source_pdf=source_pdf,
            error=str(exc),
        )

    _append_convert_log(paths, paper_id=paper_id, backend=backend)

    return ConvertOutcome(
        paper_id=paper_id,
        backend=backend,
        status="converted",
        output_dir=result.output_dir,
        markdown_path=result.markdown_path,
        source_pdf=source_pdf,
    )


def list_paper_ids_with_pdf(paths: ProjectPaths) -> list[str]:
    """Return every ``paper_id`` that has an archived PDF under 01_Raw/pdf."""
    if not paths.kb_raw_pdf.is_dir():
        return []
    return sorted(p.stem for p in paths.kb_raw_pdf.glob("*.pdf") if p.is_file())


# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------


def _append_convert_log(
    paths: ProjectPaths,
    *,
    paper_id: str,
    backend: str,
) -> None:
    """Append a ``convert-pdf`` line to ``00_System/log.md``."""
    log_path = paths.kb_system / "log.md"
    ensure_dir(paths.kb_system)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"- {when} convert-pdf backend={backend} id={paper_id}\n")


__all__ = [
    "ConvertOutcome",
    "ConvertStatus",
    "convert_paper",
    "list_paper_ids_with_pdf",
]
