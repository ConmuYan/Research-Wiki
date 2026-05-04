"""Schema and I/O helpers for ``01_Raw/imports/<run_id>/`` manifests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lgrlw.fs import ensure_dir
from lgrlw.paths import ProjectPaths


class ImportEntryStatus(str, Enum):
    """Outcome of a single BibTeX entry during an import run."""

    imported = "imported"
    skipped_duplicate = "skipped_duplicate"
    skipped_error = "skipped_error"
    would_import = "would_import"
    would_skip_duplicate = "would_skip_duplicate"


class ImportEntry(BaseModel):
    """Per-entry audit record stored inside an import manifest."""

    model_config = ConfigDict(extra="forbid")

    cite_key: str
    mode: Literal["manual", "doi", "arxiv", "openalex", "ss"] | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    paper_id: str | None = None
    pdf_source: Literal["local", "network", "none"] = "none"
    pdf_archive: str | None = None
    status: ImportEntryStatus
    error: str | None = None


class ImportManifest(BaseModel):
    """Top-level manifest describing one ``lgrlw import-bib`` invocation."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    run_id: str
    started_at: datetime
    source_bib: str
    dry_run: bool = False
    on_duplicate: Literal["skip", "force", "fail"] = "skip"
    pdf_dir: str | None = None
    direction: str | None = None
    entries: list[ImportEntry] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


def new_run_id(now: datetime | None = None) -> str:
    """Return a sortable, microsecond-precise ``bib_import`` run id.

    Microsecond precision makes back-to-back invocations (test suites,
    agent retries) produce distinct run directories under
    ``literature-kb/01_Raw/imports/`` without extra collision handling.
    """
    when = now or datetime.now(timezone.utc)
    return when.strftime("%Y%m%d_%H%M%S_%f_bib_import")


def write_manifest(paths: ProjectPaths, manifest: ImportManifest) -> Path:
    """Persist ``manifest`` under ``kb_raw_imports/<run_id>/manifest.json``.

    Returns the path to the written manifest. The containing directory
    is created on demand.
    """
    run_dir = paths.kb_raw_imports / manifest.run_id
    ensure_dir(run_dir)
    manifest_path = run_dir / "manifest.json"

    payload = manifest.model_dump(mode="json", exclude_none=False)
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


__all__ = [
    "ImportEntry",
    "ImportEntryStatus",
    "ImportManifest",
    "new_run_id",
    "write_manifest",
]
