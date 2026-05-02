"""Invariant checks for a Research-Wiki project.

Each submodule contributes a pure, deterministic check function that returns
a list of :class:`lgrlw.schemas.LintFinding`. :func:`run_all` runs every
check in a fixed order; :func:`format_findings` renders the results as
human-friendly text.

Boundary / schema / manifest rules can only *strengthen* over time (see
AGENTS.md section 1.3). Any relaxation requires a test and a changelog entry.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path

from lgrlw.lint.boundary import check_boundary
from lgrlw.lint.manifest import check_manifests
from lgrlw.lint.schema import check_frontmatter_schemas
from lgrlw.lint.structure import check_structure
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import LintFinding


def run_all(paths: ProjectPaths) -> list[LintFinding]:
    """Run every invariant check in a deterministic order."""
    findings: list[LintFinding] = []
    findings.extend(check_structure(paths))
    # Later checks may assume the structure is valid; guard by bailing
    # early only on fatal structural errors.
    findings.extend(check_frontmatter_schemas(paths))
    findings.extend(check_boundary(paths))
    findings.extend(check_manifests(paths))
    return findings


def format_findings(
    findings: Iterable[LintFinding],
    *,
    project_root: Path | None = None,
) -> str:
    """Render findings as a plain-text report, one block per finding."""
    lines: list[str] = []
    for f in findings:
        displayed_path = f.path
        if project_root is not None:
            with suppress(ValueError):
                displayed_path = str(Path(f.path).relative_to(project_root))
        lines.append(f"{f.severity.upper():7}  {f.rule:40}  {displayed_path}")
        lines.append(f"         {f.message}")
        if f.hint:
            lines.append(f"         hint: {f.hint}")
    return "\n".join(lines)


__all__ = [
    "check_boundary",
    "check_frontmatter_schemas",
    "check_manifests",
    "check_structure",
    "format_findings",
    "run_all",
]
