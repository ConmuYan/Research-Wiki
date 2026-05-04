"""Deterministic local PDF matching helpers used by batch ingestion.

``find_pdf_candidate`` walks a user-supplied directory and returns the
best-matching PDF for a :class:`~lgrlw.ingest.bibtex.BibEntry`, using
three filename heuristics (arXiv id, cite key, paper id slug). It never
touches the network.
"""

from __future__ import annotations

from pathlib import Path

from lgrlw._slug import paper_slug
from lgrlw.ingest.bibtex import BibEntry


def find_pdf_candidate(entry: BibEntry, pdf_dir: Path) -> Path | None:
    """Return a PDF matching ``entry`` inside ``pdf_dir`` or ``None``.

    Matching priority:

    1. filename (stem, case-insensitive) equals / contains the arXiv id;
    2. filename equals / contains the BibTeX cite key;
    3. filename equals / contains the canonical paper-id slug derived
       from the first author, year, and title.

    No fuzzy title matching is performed here. v0.4.x adds that via the
    ``lgrlw attach-pdf`` command where user confirmation makes fuzzy
    matches safe.
    """
    if not pdf_dir.is_dir():
        return None

    candidates = [p for p in pdf_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if not candidates:
        return None

    # Build ordered list of identifiers. Empty strings are filtered out.
    identifiers: list[str] = []
    if entry.arxiv_id:
        identifiers.append(entry.arxiv_id)
        # Some downloads drop the dot (e.g. ``2310_11511.pdf``). Tolerate it.
        identifiers.append(entry.arxiv_id.replace(".", "_"))
    if entry.cite_key:
        identifiers.append(entry.cite_key)
    if entry.authors and entry.year is not None and entry.title:
        slug = paper_slug(entry.authors[0], entry.year, entry.title)
        identifiers.append(slug)

    identifiers_lc = [i.lower() for i in identifiers if i]

    for identifier in identifiers_lc:
        for candidate in candidates:
            stem = candidate.stem.lower()
            if stem == identifier or identifier in stem:
                return candidate

    return None


__all__ = ["find_pdf_candidate"]
