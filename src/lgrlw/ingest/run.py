"""Orchestrator for ``lgrlw import-bib`` (v0.4)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from lgrlw._slug import paper_slug
from lgrlw.commands.add_literature import (
    _archive_pdf,
    _write_literature_entry,
)
from lgrlw.fs import ensure_dir
from lgrlw.ingest.bibtex import BibEntry, parse_bib
from lgrlw.ingest.manifest import (
    ImportEntry,
    ImportEntryStatus,
    ImportManifest,
    new_run_id,
    write_manifest,
)
from lgrlw.ingest.pdf_match import find_pdf_candidate
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import PaperFrontmatter, PaperKind, PaperStatus

OnDuplicate = Literal["skip", "force", "fail"]


class ImportBibError(RuntimeError):
    """Raised by :func:`run_import_bib` when the batch must abort atomically."""


@dataclass(frozen=True)
class ImportBibRequest:
    """Input arguments for a single ``import-bib`` invocation."""

    bib_path: Path
    pdf_dir: Path | None = None
    dry_run: bool = False
    on_duplicate: OnDuplicate = "skip"
    default_status: PaperStatus = PaperStatus.published
    tags: tuple[str, ...] = ()
    direction: str | None = None
    force_pdf: bool = False
    allow_network_pdf: bool = False


@dataclass
class ImportBibResult:
    """Output of :func:`run_import_bib`."""

    manifest: ImportManifest
    manifest_path: Path | None
    source_bib_path: Path | None


def run_import_bib(paths: ProjectPaths, request: ImportBibRequest) -> ImportBibResult:
    """Execute the batch import.

    On ``dry_run=True`` no files under ``literature-kb/`` are created
    (not even the run directory). The returned manifest describes what
    *would* happen.
    """
    entries = parse_bib(request.bib_path)
    now = datetime.now(timezone.utc)
    run_id = new_run_id(now)

    index = _build_duplicate_index(paths)

    if request.on_duplicate == "fail":
        _preflight_duplicate_check(entries, index)

    manifest_entries: list[ImportEntry] = []
    for entry in entries:
        record = _process_entry(
            paths=paths,
            entry=entry,
            index=index,
            request=request,
        )
        manifest_entries.append(record)
        # On a successful non-dry-run import the entry now exists and
        # should block further duplicates inside the same batch.
        if record.status == ImportEntryStatus.imported and record.paper_id:
            _register_entry(index, entry, record.paper_id)

    counts = _tally(manifest_entries)

    manifest = ImportManifest(
        run_id=run_id,
        started_at=now,
        source_bib=str(request.bib_path),
        dry_run=request.dry_run,
        on_duplicate=request.on_duplicate,
        pdf_dir=str(request.pdf_dir) if request.pdf_dir is not None else None,
        direction=request.direction,
        entries=manifest_entries,
        counts=counts,
    )

    if request.dry_run:
        return ImportBibResult(manifest=manifest, manifest_path=None, source_bib_path=None)

    manifest_path = write_manifest(paths, manifest)
    source_bib_path = _archive_source_bib(paths, request.bib_path, run_id)
    # Rewrite manifest with the canonical archived path so future runs
    # can locate the bib even if the original is moved / deleted.
    manifest = manifest.model_copy(update={"source_bib": str(source_bib_path)})
    write_manifest(paths, manifest)

    return ImportBibResult(
        manifest=manifest,
        manifest_path=manifest_path,
        source_bib_path=source_bib_path,
    )


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _process_entry(  # noqa: PLR0912 - the branches are all well-contained ingestion guards
    *,
    paths: ProjectPaths,
    entry: BibEntry,
    index: _DuplicateIndex,
    request: ImportBibRequest,
) -> ImportEntry:
    """Decide how to handle one BibTeX entry and return its manifest row."""
    common = _shared_fields(entry)
    dup = _detect_duplicate(entry, index)
    if dup is not None and request.on_duplicate != "force":
        return ImportEntry(
            **common,
            paper_id=dup,
            status=(
                ImportEntryStatus.would_skip_duplicate
                if request.dry_run
                else ImportEntryStatus.skipped_duplicate
            ),
        )

    # Validate the mandatory manual-mode fields before we try to write.
    missing: list[str] = []
    if not entry.title:
        missing.append("title")
    if not entry.authors:
        missing.append("authors")
    if entry.year is None:
        missing.append("year")
    if missing:
        return ImportEntry(
            **common,
            status=ImportEntryStatus.skipped_error,
            error=f"missing required bib field(s): {', '.join(missing)}",
        )

    assert entry.year is not None  # guaranteed by the missing-field check above
    paper_id = paper_slug(entry.authors[0], entry.year, entry.title)

    mode: Literal["manual", "doi", "arxiv", "openalex", "ss"]
    if entry.arxiv_id:
        mode = "arxiv"
    elif entry.doi:
        mode = "doi"
    elif entry.openalex_id:
        mode = "openalex"
    elif entry.semantic_scholar_id:
        mode = "ss"
    else:
        mode = "manual"

    pdf_path = find_pdf_candidate(entry, request.pdf_dir) if request.pdf_dir is not None else None
    pdf_source: Literal["local", "network", "none"] = "none"
    if pdf_path is not None:
        pdf_source = "local"

    if request.dry_run:
        return ImportEntry(
            **common,
            mode=mode,
            paper_id=paper_id,
            pdf_source=pdf_source,
            status=ImportEntryStatus.would_import,
        )

    try:
        fm = _build_frontmatter(
            entry=entry,
            paper_id=paper_id,
            status=request.default_status,
            tags=list(request.tags),
        )
        pdf_archive = _archive_pdf(
            paths,
            paper_id,
            pdf_path,
            force_pdf=request.force_pdf or request.on_duplicate == "force",
        )
        if pdf_archive is None and request.allow_network_pdf and entry.arxiv_id:
            pdf_archive = _download_arxiv_pdf_to_archive(
                paths,
                paper_id=paper_id,
                arxiv_id=entry.arxiv_id,
                force_pdf=request.force_pdf or request.on_duplicate == "force",
            )
            if pdf_archive is not None:
                pdf_source = "network"
        _write_literature_entry(
            paths,
            fm,
            force=request.on_duplicate == "force",
            source_label=f"bib-{mode}",
            pdf_archive=pdf_archive,
        )
    except Exception as exc:  # surface per-entry failure without aborting the batch
        return ImportEntry(
            **common,
            mode=mode,
            paper_id=paper_id,
            pdf_source=pdf_source,
            status=ImportEntryStatus.skipped_error,
            error=str(exc),
        )

    return ImportEntry(
        **common,
        mode=mode,
        paper_id=paper_id,
        pdf_source=pdf_source,
        pdf_archive=str(pdf_archive) if pdf_archive is not None else None,
        status=ImportEntryStatus.imported,
    )


def _download_arxiv_pdf_to_archive(
    paths: ProjectPaths,
    *,
    paper_id: str,
    arxiv_id: str,
    force_pdf: bool,
) -> Path | None:
    """Fetch ``arxiv_id`` and archive it; returns ``None`` if the archive
    already exists and ``force_pdf`` is false.
    """
    from lgrlw.fs import ensure_dir
    from lgrlw.ingest.pdf_download import fetch_arxiv_pdf

    ensure_dir(paths.kb_raw_pdf)
    destination = paths.kb_raw_pdf / f"{paper_id}.pdf"
    if destination.exists() and not force_pdf:
        return None
    result = fetch_arxiv_pdf(arxiv_id, allow_network_pdf=True)
    destination.write_bytes(result.content)
    return destination


def _shared_fields(entry: BibEntry) -> dict[str, Any]:
    """Return the BibTeX-sourced fields every manifest row inherits.

    Typed as ``dict[str, Any]`` so callers can splat it into
    :class:`ImportEntry` alongside the per-row discriminants (``mode``,
    ``paper_id``, ``status``, ...) without mypy complaining about the
    mixed field types.
    """
    return {
        "cite_key": entry.cite_key,
        "arxiv_id": entry.arxiv_id,
        "doi": entry.doi,
        "openalex_id": entry.openalex_id,
        "semantic_scholar_id": entry.semantic_scholar_id,
        "title": entry.title,
        "authors": list(entry.authors),
        "year": entry.year,
        "venue": entry.venue,
    }


def _build_frontmatter(
    *,
    entry: BibEntry,
    paper_id: str,
    status: PaperStatus,
    tags: list[str],
) -> PaperFrontmatter:
    return PaperFrontmatter(
        id=paper_id,
        title=entry.title,
        authors=entry.authors,
        year=entry.year or 0,
        venue=entry.venue,
        doi=entry.doi,
        arxiv_id=entry.arxiv_id,
        openalex_id=entry.openalex_id,
        semantic_scholar_id=entry.semantic_scholar_id,
        url=entry.url,
        status=status,
        source=PaperKind.manual,
        added_on=date.today(),
        tags=tags,
    )


class _DuplicateIndex:
    """Case-insensitive index of identifiers already present in the KB."""

    __slots__ = ("arxiv", "doi", "openalex", "paper_ids", "ss")

    def __init__(self) -> None:
        self.arxiv: dict[str, str] = {}
        self.doi: dict[str, str] = {}
        self.openalex: dict[str, str] = {}
        self.ss: dict[str, str] = {}
        self.paper_ids: set[str] = set()


def _build_duplicate_index(paths: ProjectPaths) -> _DuplicateIndex:
    """Index existing KB entries by identifier so we can detect duplicates."""
    index = _DuplicateIndex()
    metadata_dir = paths.kb_raw_metadata
    if not metadata_dir.is_dir():
        return index

    for meta_file in metadata_dir.glob("*.json"):
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        paper_id = str(data.get("id") or meta_file.stem)
        index.paper_ids.add(paper_id)
        if arxiv := data.get("arxiv_id"):
            index.arxiv[str(arxiv).lower()] = paper_id
        if doi := data.get("doi"):
            index.doi[str(doi).lower()] = paper_id
        if openalex := data.get("openalex_id"):
            index.openalex[str(openalex)] = paper_id
        if ss := data.get("semantic_scholar_id"):
            index.ss[str(ss).lower()] = paper_id
    return index


def _detect_duplicate(entry: BibEntry, index: _DuplicateIndex) -> str | None:
    if entry.arxiv_id and entry.arxiv_id.lower() in index.arxiv:
        return index.arxiv[entry.arxiv_id.lower()]
    if entry.doi and entry.doi.lower() in index.doi:
        return index.doi[entry.doi.lower()]
    if entry.openalex_id and entry.openalex_id in index.openalex:
        return index.openalex[entry.openalex_id]
    if entry.semantic_scholar_id and entry.semantic_scholar_id.lower() in index.ss:
        return index.ss[entry.semantic_scholar_id.lower()]
    if entry.authors and entry.year is not None and entry.title:
        slug = paper_slug(entry.authors[0], entry.year, entry.title)
        if slug in index.paper_ids:
            return slug
    return None


def _register_entry(index: _DuplicateIndex, entry: BibEntry, paper_id: str) -> None:
    index.paper_ids.add(paper_id)
    if entry.arxiv_id:
        index.arxiv[entry.arxiv_id.lower()] = paper_id
    if entry.doi:
        index.doi[entry.doi.lower()] = paper_id
    if entry.openalex_id:
        index.openalex[entry.openalex_id] = paper_id
    if entry.semantic_scholar_id:
        index.ss[entry.semantic_scholar_id.lower()] = paper_id


def _preflight_duplicate_check(entries: list[BibEntry], index: _DuplicateIndex) -> None:
    duplicates = [e for e in entries if _detect_duplicate(e, index) is not None]
    if duplicates:
        raise ImportBibError(
            f"on_duplicate='fail' and {len(duplicates)} entry(ies) already exist; "
            "the batch has not written anything"
        )


def _tally(entries: list[ImportEntry]) -> dict[str, int]:
    counts: dict[str, int] = {s.value: 0 for s in ImportEntryStatus}
    for row in entries:
        counts[row.status.value] += 1
    counts["total"] = len(entries)
    return counts


def _archive_source_bib(paths: ProjectPaths, source: Path, run_id: str) -> Path:
    run_dir = paths.kb_raw_imports / run_id
    ensure_dir(run_dir)
    destination = run_dir / "source.bib"
    shutil.copyfile(source, destination)
    return destination


__all__ = [
    "ImportBibError",
    "ImportBibRequest",
    "ImportBibResult",
    "OnDuplicate",
    "run_import_bib",
]
