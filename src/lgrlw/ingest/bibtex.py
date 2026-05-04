"""Offline BibTeX parser used by ``lgrlw import-bib``.

The parser is deliberately conservative: it only exposes the fields
Research-Wiki cares about (title, authors, year, venue, doi, arxiv id,
OpenAlex id, Semantic Scholar id, URL, abstract). It relies on the
``bibtexparser`` package which ships via the optional ``[bib]`` extra
(``pip install "lgrlw[bib]"``).

No network I/O is performed. Every function is pure and deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class BibtexParseError(RuntimeError):
    """Raised when the BibTeX file cannot be opened or parsed."""


@dataclass(frozen=True)
class BibEntry:
    """Normalised view of a BibTeX entry.

    ``raw_fields`` preserves the original (lower-cased) field map so
    callers can surface unknown fields in diagnostics without having to
    re-parse the file.
    """

    cite_key: str
    entry_type: str
    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    openalex_id: str | None
    semantic_scholar_id: str | None
    url: str | None
    abstract: str | None
    raw_fields: dict[str, str] = field(default_factory=dict)


# Matches the canonical arXiv id used since 2007 (YYMM.NNNNN[ vN]).
# We accept an optional leading ``arXiv:`` and an optional version suffix.
_ARXIV_RE = re.compile(
    r"(?:arxiv:\s*)?(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)

# Old-style arXiv ids (hep-th/9901001 et al.). We capture the full id.
_OLD_ARXIV_RE = re.compile(
    r"\b([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?",
)

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")

_OPENALEX_RE = re.compile(r"\b(W\d+)\b")

_S2_HEX_RE = re.compile(r"\b([0-9a-f]{40})\b")


def parse_bib(path: Path) -> list[BibEntry]:
    """Parse ``path`` into a list of :class:`BibEntry` objects.

    Unknown entry fields are preserved verbatim in :attr:`BibEntry.raw_fields`.
    Missing required fields (title, authors) surface as empty strings /
    empty lists rather than exceptions — the orchestrator is responsible
    for deciding how to report them.
    """
    try:
        import bibtexparser
    except ImportError as exc:  # pragma: no cover - exercised only when extra missing
        raise BibtexParseError(
            "lgrlw import-bib requires the optional `bibtexparser` dependency. "
            'Install it with: pip install "lgrlw[bib]"'
        ) from exc

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise BibtexParseError(f"cannot read BibTeX file {path}: {exc}") from exc

    try:
        db = bibtexparser.loads(text)
    except Exception as exc:  # bibtexparser raises bare Exceptions in some cases
        raise BibtexParseError(f"cannot parse BibTeX file {path}: {exc}") from exc

    entries: list[BibEntry] = []
    for raw in db.entries:
        entries.append(_normalise_entry(raw))
    return entries


def _normalise_entry(raw: dict[str, Any]) -> BibEntry:
    """Turn a raw bibtexparser record into a :class:`BibEntry`."""
    # bibtexparser lower-cases all field names already, but ``ID`` / ``ENTRYTYPE``
    # are special markers that it leaves in upper-case.
    cite_key = str(raw.get("ID", "")).strip()
    entry_type = str(raw.get("ENTRYTYPE", "misc")).strip().lower() or "misc"

    # Preserve the original field map minus the two markers above.
    raw_fields = {
        k: str(v).strip() for k, v in raw.items() if k not in {"ID", "ENTRYTYPE"} and v is not None
    }

    title = _clean_braces(raw_fields.get("title", ""))
    authors = _split_authors(raw_fields.get("author", ""))
    year = _parse_year(raw_fields.get("year", ""))
    venue = (
        _clean_braces(
            raw_fields.get("journal")
            or raw_fields.get("booktitle")
            or raw_fields.get("publisher")
            or ""
        )
        or None
    )
    abstract = _clean_braces(raw_fields.get("abstract", "")) or None
    url = raw_fields.get("url") or None

    doi = _extract_doi(raw_fields)
    arxiv_id = _extract_arxiv(raw_fields)
    openalex_id = _extract_openalex(raw_fields)
    semantic_scholar_id = _extract_ss(raw_fields)

    return BibEntry(
        cite_key=cite_key,
        entry_type=entry_type,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        arxiv_id=arxiv_id,
        openalex_id=openalex_id,
        semantic_scholar_id=semantic_scholar_id,
        url=url,
        abstract=abstract,
        raw_fields=raw_fields,
    )


def _clean_braces(value: str) -> str:
    """Strip LaTeX brace protection and collapse whitespace."""
    if not value:
        return ""
    # Remove only the outermost brace pairs that BibTeX uses for
    # case-preservation; keep inner brace content intact.
    cleaned = value.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1].strip()
    # Drop single-character brace groups introduced for case protection
    # (e.g. "{S}elf-RAG" -> "Self-RAG").
    cleaned = re.sub(r"\{([^{}]*)\}", r"\1", cleaned)
    return cleaned


def _split_authors(raw: str) -> list[str]:
    """Turn BibTeX ``Last, First and Other, Name`` into a list of names."""
    raw = _clean_braces(raw)
    if not raw:
        return []

    # BibTeX author lists are separated by the word "and" with surrounding whitespace.
    names_raw = re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)
    authors: list[str] = []
    for raw_name in names_raw:
        name = raw_name.strip()
        if not name:
            continue
        if "," in name:
            # "Last, First Middle" -> "First Middle Last"
            last, _, first = name.partition(",")
            normalised = f"{first.strip()} {last.strip()}".strip()
        else:
            normalised = name
        # Collapse any leftover whitespace.
        normalised = re.sub(r"\s+", " ", normalised)
        if normalised:
            authors.append(normalised)
    return authors


def _parse_year(raw: str) -> int | None:
    raw = raw.strip().strip("{}").strip()
    if not raw:
        return None
    match = re.search(r"(\d{4})", raw)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_doi(fields: dict[str, str]) -> str | None:
    candidate = fields.get("doi", "").strip()
    if candidate:
        candidate = candidate.split()[0].rstrip(",.;")
        # Allow both "10.xxxx/..." and "https://doi.org/10.xxxx/..." forms.
        match = _DOI_RE.search(candidate)
        if match:
            return match.group(1)
    for key in ("url", "note"):
        value = fields.get(key, "")
        match = _DOI_RE.search(value)
        if match:
            return match.group(1)
    return None


def _extract_arxiv(fields: dict[str, str]) -> str | None:
    """Locate an arXiv id across common BibTeX conventions."""
    # Most reliable: explicit eprint field with archivePrefix=arXiv.
    archive_prefix = fields.get("archiveprefix", "").lower()
    eprint = fields.get("eprint", "").strip()
    if eprint and (not archive_prefix or archive_prefix == "arxiv"):
        found = _match_arxiv_id(eprint)
        if found:
            return found

    # URL-based hints: https://arxiv.org/abs/2310.11511 .
    for key in ("url", "journal", "note", "howpublished"):
        value = fields.get(key, "")
        if not value:
            continue
        if "arxiv" in value.lower():
            found = _match_arxiv_id(value)
            if found:
                return found

    return None


def _match_arxiv_id(text: str) -> str | None:
    match = _ARXIV_RE.search(text)
    if match:
        return match.group(1)
    old = _OLD_ARXIV_RE.search(text)
    if old:
        return old.group(1)
    return None


def _extract_openalex(fields: dict[str, str]) -> str | None:
    candidate = fields.get("openalex", "").strip()
    if candidate:
        match = _OPENALEX_RE.search(candidate)
        if match:
            return match.group(1)
    for key in ("url", "note"):
        value = fields.get(key, "")
        if "openalex" in value.lower():
            match = _OPENALEX_RE.search(value)
            if match:
                return match.group(1)
    return None


def _extract_ss(fields: dict[str, str]) -> str | None:
    """Look for a 40-char Semantic Scholar paper id in explicit fields."""
    for key in ("semantic_scholar", "semanticscholar", "s2id", "s2_paper_id"):
        value = fields.get(key, "")
        match = _S2_HEX_RE.search(value)
        if match:
            return match.group(1)
    for key in ("url", "note"):
        value = fields.get(key, "")
        if "semanticscholar" in value.lower():
            match = _S2_HEX_RE.search(value)
            if match:
                return match.group(1)
    return None


__all__ = [
    "BibEntry",
    "BibtexParseError",
    "parse_bib",
]
