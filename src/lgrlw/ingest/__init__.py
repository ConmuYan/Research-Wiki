"""Deterministic literature ingestion helpers (v0.4+).

The :mod:`lgrlw.ingest` sub-package contains offline, reproducible helpers
that power ``lgrlw import-bib`` and, in later releases, ``lgrlw
attach-pdf``. Everything here is synchronous, network-free, and covered
by unit tests so that ``lgrlw`` can offer a batch-literature workflow
without violating the project's "no hidden network calls" rule.
"""

from __future__ import annotations

from lgrlw.ingest.bibtex import BibEntry, BibtexParseError, parse_bib
from lgrlw.ingest.manifest import (
    ImportEntry,
    ImportEntryStatus,
    ImportManifest,
    new_run_id,
    write_manifest,
)
from lgrlw.ingest.pdf_match import find_pdf_candidate

__all__ = [
    "BibEntry",
    "BibtexParseError",
    "ImportEntry",
    "ImportEntryStatus",
    "ImportManifest",
    "find_pdf_candidate",
    "new_run_id",
    "parse_bib",
    "write_manifest",
]
