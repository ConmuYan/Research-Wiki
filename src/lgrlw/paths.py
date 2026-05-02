"""Canonical filesystem layout of a Research-Wiki project.

A project is any directory that contains a ``.lgrlw.toml`` marker file. All
path accessors return deterministic sub-paths relative to that root.

The layout is::

    <root>/
        .lgrlw.toml                 # project marker + config
        literature-kb/              # public literature (KB)
            00_System/
            01_Raw/
                bibtex/ pdf/ mineru_md/ metadata/
            02_Literature/Papers/
            03_Field_Structure/
            04_Concepts/
            05_Evidence/
            06_Exports/
        research-workspaces/        # private ideas / manuscripts / reviews
            <workspace_id>/
                00_Project/
                01_KB_Exports/
                ...
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_MARKER = ".lgrlw.toml"


@dataclass(frozen=True)
class ProjectPaths:
    """Deterministic path accessors for a LGRLW project root."""

    root: Path
    kb_name: str = "literature-kb"
    workspaces_name: str = "research-workspaces"

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------
    @property
    def config_file(self) -> Path:
        return self.root / PROJECT_MARKER

    @property
    def kb(self) -> Path:
        return self.root / self.kb_name

    @property
    def workspaces(self) -> Path:
        return self.root / self.workspaces_name

    # ------------------------------------------------------------------
    # KB subdirectories
    # ------------------------------------------------------------------
    @property
    def kb_system(self) -> Path:
        return self.kb / "00_System"

    @property
    def kb_raw(self) -> Path:
        return self.kb / "01_Raw"

    @property
    def kb_raw_metadata(self) -> Path:
        return self.kb_raw / "metadata"

    @property
    def kb_papers(self) -> Path:
        return self.kb / "02_Literature" / "Papers"

    @property
    def kb_field_structure(self) -> Path:
        return self.kb / "03_Field_Structure"

    @property
    def kb_concepts(self) -> Path:
        return self.kb / "04_Concepts"

    @property
    def kb_evidence(self) -> Path:
        return self.kb / "05_Evidence"

    @property
    def kb_exports(self) -> Path:
        return self.kb / "06_Exports"

    # ------------------------------------------------------------------
    # Workspace subdirectories
    # ------------------------------------------------------------------
    def workspace(self, workspace_id: str) -> Path:
        return self.workspaces / workspace_id

    def workspace_kb_exports(self, workspace_id: str) -> Path:
        return self.workspace(workspace_id) / "01_KB_Exports"


def find_project_root(start: Path) -> Path:
    """Walk upward from ``start`` until a ``.lgrlw.toml`` is found."""
    start = start.resolve()
    for parent in [start, *start.parents]:
        if (parent / PROJECT_MARKER).is_file():
            return parent
    raise FileNotFoundError(f"No {PROJECT_MARKER} found searching upward from {start}.")


def resolve_project(root: Path | None) -> ProjectPaths:
    """Return a :class:`ProjectPaths` for ``root`` (or auto-detected cwd).

    Parameters
    ----------
    root:
        If None, walks upward from the current working directory looking
        for a ``.lgrlw.toml``. Otherwise ``root`` must already be a
        Research-Wiki project root.
    """
    if root is None:
        resolved = find_project_root(Path.cwd())
    else:
        resolved = root.resolve()
        if not (resolved / PROJECT_MARKER).is_file():
            raise FileNotFoundError(
                f"{resolved} is not a Research-Wiki project (missing {PROJECT_MARKER})."
            )
    return ProjectPaths(root=resolved)


__all__ = [
    "PROJECT_MARKER",
    "ProjectPaths",
    "find_project_root",
    "resolve_project",
]
