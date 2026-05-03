"""Pydantic v2 frontmatter schemas for KB, workspace, exports, and lint.

These schemas are the single source of truth for what constitutes a valid
Research-Wiki entry. The JSON Schemas under ``schemas/`` in the repository
are generated-by-hand mirrors of these pydantic models and are kept in sync
by convention (see :doc:`AGENTS.md` section 1.2).
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Regular expressions reused by validators and by the add-literature slug
# generator. Kept module-level so tests can import them.
# ---------------------------------------------------------------------------
PAPER_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
WORKSPACE_ID_PATTERN = re.compile(r"^[a-z0-9_](?:[a-z0-9_-]*)?$")
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")
# arXiv: new-style 2310.11511 or 2310.11511v2, or legacy cat/0701001
ARXIV_PATTERN = re.compile(r"^(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$")
# OpenAlex Work IDs: capital-W followed by a numeric tail.
OPENALEX_ID_PATTERN = re.compile(r"^W\d+$")
# Semantic Scholar paper IDs: canonical 40-char SHA-1 hex, lowercase.
SEMANTIC_SCHOLAR_ID_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


# ---------------------------------------------------------------------------
# KB literature
# ---------------------------------------------------------------------------
class PaperKind(str, Enum):
    """How a paper was ingested into the KB."""

    manual = "manual"
    arxiv = "arxiv"
    openalex = "openalex"
    semantic_scholar = "semantic_scholar"
    crossref = "crossref"
    doi = "doi"
    promoted = "promoted"  # promoted from an accepted workspace paper


class PaperStatus(str, Enum):
    """Publication status of a literature entry."""

    published = "published"
    accepted = "accepted"
    preprint = "preprint"


class PaperFrontmatter(BaseModel):
    """YAML frontmatter of ``literature-kb/02_Literature/Papers/<id>.md``.

    The ``type: paper`` discriminator is enforced so that boundary-lint can
    tell at a glance whether a markdown file in the KB is a legitimate paper
    card or a workspace page that leaked in.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)

    type: Literal["paper"] = "paper"
    id: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3)
    authors: list[str] = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    url: str | None = None
    status: PaperStatus = PaperStatus.published
    source: PaperKind = PaperKind.manual
    added_on: date
    tags: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not PAPER_ID_PATTERN.fullmatch(v):
            raise ValueError(f"invalid paper id {v!r}; must match {PAPER_ID_PATTERN.pattern}")
        return v

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, v: str | None) -> str | None:
        if v is not None and not DOI_PATTERN.fullmatch(v):
            raise ValueError(f"invalid DOI {v!r}")
        return v

    @field_validator("arxiv_id")
    @classmethod
    def _validate_arxiv(cls, v: str | None) -> str | None:
        if v is not None and not ARXIV_PATTERN.fullmatch(v):
            raise ValueError(f"invalid arXiv id {v!r}")
        return v

    @field_validator("openalex_id")
    @classmethod
    def _validate_openalex(cls, v: str | None) -> str | None:
        if v is not None and not OPENALEX_ID_PATTERN.fullmatch(v):
            raise ValueError(f"invalid OpenAlex id {v!r}; must match {OPENALEX_ID_PATTERN.pattern}")
        return v

    @field_validator("semantic_scholar_id")
    @classmethod
    def _validate_semantic_scholar(cls, v: str | None) -> str | None:
        if v is not None and not SEMANTIC_SCHOLAR_ID_PATTERN.fullmatch(v):
            raise ValueError(
                f"invalid Semantic Scholar paper id {v!r}; "
                f"must match {SEMANTIC_SCHOLAR_ID_PATTERN.pattern}"
            )
        return v

    @field_validator("authors")
    @classmethod
    def _validate_authors(cls, v: list[str]) -> list[str]:
        cleaned = [a.strip() for a in v if a and a.strip()]
        if not cleaned:
            raise ValueError("authors must contain at least one non-empty name")
        return cleaned


class PaperMetadata(BaseModel):
    """Canonical metadata returned by networked literature fetchers."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)

    title: str = Field(min_length=3)
    authors: list[str] = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2100)
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    url: str | None = None
    abstract: str | None = None
    source: PaperKind
    raw: dict[str, Any] | None = None

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, v: str | None) -> str | None:
        if v is not None and not DOI_PATTERN.fullmatch(v):
            raise ValueError(f"invalid DOI {v!r}")
        return v

    @field_validator("arxiv_id")
    @classmethod
    def _validate_arxiv(cls, v: str | None) -> str | None:
        if v is not None and not ARXIV_PATTERN.fullmatch(v):
            raise ValueError(f"invalid arXiv id {v!r}")
        return v

    @field_validator("openalex_id")
    @classmethod
    def _validate_openalex(cls, v: str | None) -> str | None:
        if v is not None and not OPENALEX_ID_PATTERN.fullmatch(v):
            raise ValueError(f"invalid OpenAlex id {v!r}; must match {OPENALEX_ID_PATTERN.pattern}")
        return v

    @field_validator("semantic_scholar_id")
    @classmethod
    def _validate_semantic_scholar(cls, v: str | None) -> str | None:
        if v is not None and not SEMANTIC_SCHOLAR_ID_PATTERN.fullmatch(v):
            raise ValueError(
                f"invalid Semantic Scholar paper id {v!r}; "
                f"must match {SEMANTIC_SCHOLAR_ID_PATTERN.pattern}"
            )
        return v

    @field_validator("authors")
    @classmethod
    def _validate_authors(cls, v: list[str]) -> list[str]:
        cleaned = [a.strip() for a in v if a and a.strip()]
        if not cleaned:
            raise ValueError("authors must contain at least one non-empty name")
        return cleaned


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------
class WorkspaceKind(str, Enum):
    paper = "paper"
    idea = "idea"


class WorkspaceStatus(str, Enum):
    """Lifecycle status of a workspace paper (S3 -> S8)."""

    drafting = "drafting"
    experimenting = "experimenting"
    writing = "writing"
    submitted = "submitted"
    under_review = "under_review"
    major_revision = "major_revision"
    minor_revision = "minor_revision"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class WorkspacePaperFrontmatter(BaseModel):
    """Frontmatter of ``research-workspaces/<id>/00_Project/paper_status.md``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)

    type: Literal["workspace_paper"] = "workspace_paper"
    id: str = Field(min_length=2, max_length=80)
    kind: WorkspaceKind = WorkspaceKind.paper
    title: str = Field(min_length=3)
    status: WorkspaceStatus = WorkspaceStatus.drafting
    created_on: date
    # Promotion fields (only required once status == accepted; validated by
    # `lgrlw promote` in v0.2, not by lint in v0.1).
    final_title: str | None = None
    final_authors: list[str] | None = None
    venue: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    doi: str | None = None
    arxiv_id: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not WORKSPACE_ID_PATTERN.fullmatch(v):
            raise ValueError(
                f"invalid workspace id {v!r}; must match {WORKSPACE_ID_PATTERN.pattern}"
            )
        return v


# ---------------------------------------------------------------------------
# Export manifest
# ---------------------------------------------------------------------------
class ExportManifest(BaseModel):
    """Immutable manifest at the root of every export pack.

    A manifest records every file copied into the pack together with its
    SHA-256 digest, so that lint can later verify the pack has not been
    tampered with or partially re-synced.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    tool_version: str
    workspace_id: str
    exported_at: str  # ISO 8601 UTC, e.g. "2026-05-02T09:30:00Z"
    kb_root_relative: str
    pack_dir_relative: str
    paper_ids: list[str]
    files: dict[str, str]  # pack-relative POSIX path -> sha256 hex

    @field_validator("kb_root_relative", "pack_dir_relative")
    @classmethod
    def _validate_relative_posix_path(cls, v: str) -> str:
        _ensure_relative_posix_path(v)
        return v

    @field_validator("files")
    @classmethod
    def _validate_files(cls, v: dict[str, str]) -> dict[str, str]:
        for path, digest in v.items():
            _ensure_relative_posix_path(path)
            if not SHA256_PATTERN.fullmatch(digest):
                raise ValueError(f"invalid sha256 digest for {path!r}")
        return v


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------
class ProjectConfig(BaseModel):
    """Parsed contents of ``.lgrlw.toml``'s ``[project]`` table.

    Two layouts are supported:

    * **Single-direction** (``monorepo = false``, the default and the
      v0.1/v0.2 layout). The project root holds ``literature-kb/`` and
      ``research-workspaces/`` directly, plus this marker file.
    * **Monorepo** (``monorepo = true``, introduced in v0.3). The
      project root holds a ``directions/`` directory with one
      single-direction subproject per child slug. ``directions`` lists
      every slug that lives under ``directions/``. Each subproject has
      its own standard single-direction ``.lgrlw.toml``.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    # 1.0.0 = v0.1/v0.2 single-direction layout.
    # 1.1.0 = v0.3 monorepo umbrella layout.
    schema_version: Literal["1.0.0", "1.1.0"] = "1.0.0"
    direction: str = Field(min_length=1)
    kb_name: str = "literature-kb"
    workspaces_name: str = "research-workspaces"
    monorepo: bool = False
    directions: list[str] = Field(default_factory=list)

    @field_validator("directions")
    @classmethod
    def _validate_directions(cls, v: list[str]) -> list[str]:
        cleaned = [d.strip() for d in v if d and d.strip()]
        for slug in cleaned:
            if not PAPER_ID_PATTERN.fullmatch(slug):
                raise ValueError(
                    f"invalid direction slug {slug!r}; must match {PAPER_ID_PATTERN.pattern}"
                )
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("monorepo `directions` must not contain duplicate slugs")
        return cleaned


def _ensure_relative_posix_path(value: str) -> None:
    if not value:
        raise ValueError("manifest paths must be non-empty")
    if "\\" in value:
        raise ValueError(f"manifest path {value!r} must use POSIX '/' separators")
    if value.startswith("/") or WINDOWS_DRIVE_PATTERN.match(value):
        raise ValueError(f"manifest path {value!r} must be relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"manifest path {value!r} must not contain empty, '.' or '..' segments")


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------
class LintSeverity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


class LintFinding(BaseModel):
    """A single boundary / schema / manifest violation."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    rule: str
    severity: LintSeverity = LintSeverity.error
    path: str
    message: str
    hint: str | None = None


__all__ = [
    "ARXIV_PATTERN",
    "DOI_PATTERN",
    "OPENALEX_ID_PATTERN",
    "PAPER_ID_PATTERN",
    "SEMANTIC_SCHOLAR_ID_PATTERN",
    "SHA256_PATTERN",
    "WINDOWS_DRIVE_PATTERN",
    "WORKSPACE_ID_PATTERN",
    "ExportManifest",
    "LintFinding",
    "LintSeverity",
    "PaperFrontmatter",
    "PaperKind",
    "PaperMetadata",
    "PaperStatus",
    "ProjectConfig",
    "WorkspaceKind",
    "WorkspacePaperFrontmatter",
    "WorkspaceStatus",
]
