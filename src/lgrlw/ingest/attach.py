"""Local-only helpers for attaching PDFs to existing KB papers (v0.4.x).

`attach-pdf` is the counterpart of `add-literature --pdf`: it takes a
PDF that already exists on disk and archives it under
``literature-kb/01_Raw/pdf/<paper_id>.pdf`` for a paper that is *already
in the KB*. Nothing here touches the network, and no frontmatter is
rewritten — a paper card that exists stays untouched.

Two entry points are exposed:

* :func:`attach_single` — explicit paper id + explicit PDF path.
* :func:`attach_scan`   — walk a directory and auto-match PDFs against
  existing KB papers by filename (paper-id slug, arXiv id, or flattened
  DOI substring).

Both are also exposed via ``lgrlw attach-pdf`` and the MCP
``attach_pdf`` tool so agents can batch-attach a whole inbox.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from lgrlw.fs import ensure_dir
from lgrlw.paths import ProjectPaths

MatchReason = Literal["explicit", "paper_id", "arxiv_id", "doi"]

AttachStatus = Literal[
    "archived",
    "already_attached",
    "unmatched",
    "skipped_error",
]


@dataclass(frozen=True)
class PdfMatch:
    """Where a scanned PDF file was matched to a KB paper."""

    paper_id: str
    source: Path
    reason: MatchReason


@dataclass(frozen=True)
class AttachOutcome:
    """Per-PDF result returned by :func:`attach_single` / :func:`attach_scan`."""

    source: Path
    paper_id: str
    archived: Path | None
    reason: MatchReason
    status: AttachStatus
    error: str | None = None


@dataclass(frozen=True)
class KBPaperIndex:
    """Read-only index of existing KB papers keyed by identifier."""

    paper_ids: frozenset[str]
    by_arxiv: dict[str, str]
    by_doi: dict[str, str]


_ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?!\d)")
_FLAT_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def build_kb_index(paths: ProjectPaths) -> KBPaperIndex:
    """Index every paper under ``literature-kb/01_Raw/metadata`` by id."""
    paper_ids: set[str] = set()
    by_arxiv: dict[str, str] = {}
    by_doi: dict[str, str] = {}

    metadata_dir = paths.kb_raw_metadata
    if metadata_dir.is_dir():
        for meta_file in metadata_dir.glob("*.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            paper_id = str(data.get("id") or meta_file.stem)
            paper_ids.add(paper_id)
            if arxiv := data.get("arxiv_id"):
                by_arxiv[str(arxiv)] = paper_id
            if doi := data.get("doi"):
                by_doi[_flatten(str(doi))] = paper_id

    return KBPaperIndex(
        paper_ids=frozenset(paper_ids),
        by_arxiv=by_arxiv,
        by_doi=by_doi,
    )


def match_pdf_to_paper(pdf: Path, index: KBPaperIndex) -> PdfMatch | None:
    """Return the best deterministic match for ``pdf`` or ``None``.

    Match priority (case-insensitive):

    1. filename stem equals an existing paper id;
    2. filename stem contains an existing paper id as substring;
    3. filename contains an existing paper's arXiv id;
    4. filename (flattened to alphanumerics) contains an existing paper's
       flattened DOI.
    """
    stem_lc = pdf.stem.lower()
    flat_stem = _flatten(stem_lc)

    # 1 + 2. paper_id substring (exact stems are a subset of substring).
    best_match: str | None = None
    best_len = -1
    for paper_id in index.paper_ids:
        pid_lc = paper_id.lower()
        if pid_lc in stem_lc and len(pid_lc) > best_len:
            best_match = paper_id
            best_len = len(pid_lc)
    if best_match is not None:
        return PdfMatch(paper_id=best_match, source=pdf, reason="paper_id")

    # 3. arxiv_id
    arxiv_match = _ARXIV_RE.search(stem_lc)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        if arxiv_id in index.by_arxiv:
            return PdfMatch(
                paper_id=index.by_arxiv[arxiv_id],
                source=pdf,
                reason="arxiv_id",
            )

    # 4. doi (flattened substring)
    for flat_doi, paper_id in index.by_doi.items():
        if flat_doi and flat_doi in flat_stem:
            return PdfMatch(paper_id=paper_id, source=pdf, reason="doi")

    return None


def attach_single(  # noqa: PLR0911 - linear guard chain is clearer than a single return
    paths: ProjectPaths,
    *,
    paper_id: str,
    pdf_path: Path,
    force_pdf: bool,
    remove_source: bool = False,
    reason: MatchReason = "explicit",
) -> AttachOutcome:
    """Archive ``pdf_path`` against ``paper_id``.

    Returns an :class:`AttachOutcome`; does not raise on expected errors
    (missing source, unknown paper, existing archive without
    ``force_pdf``) so callers can aggregate per-PDF results cleanly.
    """
    source = pdf_path.expanduser().resolve()
    paper_card = paths.kb_papers / f"{paper_id}.md"

    if not source.is_file():
        return AttachOutcome(
            source=source,
            paper_id=paper_id,
            archived=None,
            reason=reason,
            status="skipped_error",
            error=f"PDF source does not exist: {source}",
        )
    if source.suffix.lower() != ".pdf":
        return AttachOutcome(
            source=source,
            paper_id=paper_id,
            archived=None,
            reason=reason,
            status="skipped_error",
            error=f"not a .pdf file: {source.name}",
        )
    if not paper_card.is_file():
        return AttachOutcome(
            source=source,
            paper_id=paper_id,
            archived=None,
            reason=reason,
            status="skipped_error",
            error=f"paper {paper_id!r} does not exist in KB",
        )

    ensure_dir(paths.kb_raw_pdf)
    destination = paths.kb_raw_pdf / f"{paper_id}.pdf"

    if destination.exists() and not force_pdf:
        # Same underlying file? Already attached; treat as success.
        if destination.resolve() == source:
            return AttachOutcome(
                source=source,
                paper_id=paper_id,
                archived=destination,
                reason=reason,
                status="already_attached",
            )
        return AttachOutcome(
            source=source,
            paper_id=paper_id,
            archived=destination,
            reason=reason,
            status="already_attached",
            error=("archive already exists; re-run with --force-pdf to replace it"),
        )

    try:
        shutil.copyfile(source, destination)
    except OSError as exc:
        return AttachOutcome(
            source=source,
            paper_id=paper_id,
            archived=None,
            reason=reason,
            status="skipped_error",
            error=f"failed to copy PDF: {exc}",
        )

    if remove_source:
        # Non-fatal: the archive is already in place even if the
        # source delete fails (e.g. a readonly filesystem).
        with contextlib.suppress(OSError):
            source.unlink()

    _append_attach_log(paths, paper_id=paper_id, reason=reason, source=source)

    return AttachOutcome(
        source=source,
        paper_id=paper_id,
        archived=destination,
        reason=reason,
        status="archived",
    )


def attach_scan(
    paths: ProjectPaths,
    scan_dir: Path,
    *,
    force_pdf: bool,
    remove_source: bool,
) -> list[AttachOutcome]:
    """Walk ``scan_dir`` and archive every PDF that matches a KB paper.

    Returns one :class:`AttachOutcome` per ``*.pdf`` found in ``scan_dir``
    (non-recursive). Unmatched PDFs are returned with
    ``status="unmatched"``; the source file is left in place in that case.
    """
    if not scan_dir.is_dir():
        raise FileNotFoundError(f"scan directory does not exist: {scan_dir}")

    index = build_kb_index(paths)
    results: list[AttachOutcome] = []
    for pdf in sorted(scan_dir.glob("*.pdf")):
        if not pdf.is_file():
            continue
        match = match_pdf_to_paper(pdf, index)
        if match is None:
            results.append(
                AttachOutcome(
                    source=pdf,
                    paper_id="",
                    archived=None,
                    reason="explicit",
                    status="unmatched",
                    error="no matching KB paper (paper-id / arXiv id / DOI)",
                )
            )
            continue
        outcome = attach_single(
            paths,
            paper_id=match.paper_id,
            pdf_path=pdf,
            force_pdf=force_pdf,
            remove_source=remove_source,
            reason=match.reason,
        )
        results.append(outcome)
    return results


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _flatten(value: str) -> str:
    """Lower-case and strip every non-alphanumeric character."""
    return _FLAT_NON_ALNUM_RE.sub("", value.lower())


def _append_attach_log(
    paths: ProjectPaths,
    *,
    paper_id: str,
    reason: MatchReason,
    source: Path,
) -> None:
    """Append a single ``attach-pdf`` line to ``00_System/log.md``."""
    log_path = paths.kb_system / "log.md"
    ensure_dir(paths.kb_system)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"- {when} attach-pdf {reason} id={paper_id} src={source.name}\n")


__all__ = [
    "AttachOutcome",
    "AttachStatus",
    "KBPaperIndex",
    "MatchReason",
    "PdfMatch",
    "attach_scan",
    "attach_single",
    "build_kb_index",
    "match_pdf_to_paper",
]
