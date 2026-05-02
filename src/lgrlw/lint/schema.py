"""Frontmatter schema validation for KB papers and workspace paper_status.md."""

from __future__ import annotations

from pydantic import ValidationError

from lgrlw.fs import read_frontmatter
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import (
    LintFinding,
    LintSeverity,
    PaperFrontmatter,
    WorkspacePaperFrontmatter,
)

RULE_PAPER_MISSING = "schema.paper.missing_frontmatter"
RULE_PAPER_TYPE = "schema.paper.type"
RULE_PAPER_VALIDATION = "schema.paper.validation"
RULE_WS_MISSING = "schema.workspace.missing_frontmatter"
RULE_WS_VALIDATION = "schema.workspace.validation"

MAX_ERRORS_PER_MESSAGE = 3


def check_frontmatter_schemas(paths: ProjectPaths) -> list[LintFinding]:
    """Validate every paper card and every workspace paper_status.md."""
    findings: list[LintFinding] = []

    # ------------------------------------------------------------------
    # literature-kb/02_Literature/Papers/*.md
    # ------------------------------------------------------------------
    if paths.kb_papers.is_dir():
        for md in sorted(paths.kb_papers.glob("*.md")):
            fm, _ = read_frontmatter(md)
            if fm is None:
                findings.append(
                    LintFinding(
                        rule=RULE_PAPER_MISSING,
                        severity=LintSeverity.error,
                        path=str(md),
                        message="paper card has no YAML frontmatter",
                        hint="the file must start with `---` and declare `type: paper`",
                    )
                )
                continue

            declared_type = fm.get("type")
            if declared_type != "paper":
                findings.append(
                    LintFinding(
                        rule=RULE_PAPER_TYPE,
                        severity=LintSeverity.error,
                        path=str(md),
                        message=(
                            f"paper frontmatter must declare `type: paper` (got {declared_type!r})"
                        ),
                    )
                )
                # Don't also run the pydantic validation; it will just repeat
                # the type error less clearly.
                continue

            try:
                PaperFrontmatter.model_validate(fm)
            except ValidationError as exc:
                findings.append(
                    LintFinding(
                        rule=RULE_PAPER_VALIDATION,
                        severity=LintSeverity.error,
                        path=str(md),
                        message=f"PaperFrontmatter validation failed: {_short_err(exc)}",
                    )
                )

    # ------------------------------------------------------------------
    # research-workspaces/<id>/00_Project/paper_status.md
    # ------------------------------------------------------------------
    if paths.workspaces.is_dir():
        for ws in sorted(p for p in paths.workspaces.iterdir() if p.is_dir()):
            status_path = ws / "00_Project" / "paper_status.md"
            if not status_path.is_file():
                continue
            fm, _ = read_frontmatter(status_path)
            if fm is None:
                findings.append(
                    LintFinding(
                        rule=RULE_WS_MISSING,
                        severity=LintSeverity.error,
                        path=str(status_path),
                        message="paper_status.md has no YAML frontmatter",
                        hint="regenerate with `lgrlw new-workspace` or fill in by hand",
                    )
                )
                continue
            try:
                WorkspacePaperFrontmatter.model_validate(fm)
            except ValidationError as exc:
                findings.append(
                    LintFinding(
                        rule=RULE_WS_VALIDATION,
                        severity=LintSeverity.error,
                        path=str(status_path),
                        message=f"WorkspacePaperFrontmatter validation failed: {_short_err(exc)}",
                    )
                )

    return findings


def _short_err(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors()[:MAX_ERRORS_PER_MESSAGE]:
        loc = ".".join(str(x) for x in err["loc"]) or "<root>"
        parts.append(f"{loc}: {err['msg']}")
    remaining = len(exc.errors()) - MAX_ERRORS_PER_MESSAGE
    if remaining > 0:
        parts.append(f"(+{remaining} more)")
    return "; ".join(parts)


__all__ = [
    "RULE_PAPER_MISSING",
    "RULE_PAPER_TYPE",
    "RULE_PAPER_VALIDATION",
    "RULE_WS_MISSING",
    "RULE_WS_VALIDATION",
    "check_frontmatter_schemas",
]
