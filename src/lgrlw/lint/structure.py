"""Structural invariants of a Research-Wiki project root."""

from __future__ import annotations

from lgrlw.paths import PROJECT_MARKER, ProjectPaths
from lgrlw.schemas import LintFinding, LintSeverity

RULE_ROOT = "structure.project_root"


def check_structure(paths: ProjectPaths) -> list[LintFinding]:
    """Verify the project root has the mandatory three-space layout."""
    findings: list[LintFinding] = []

    if not paths.config_file.is_file():
        findings.append(
            LintFinding(
                rule=RULE_ROOT,
                severity=LintSeverity.error,
                path=str(paths.root),
                message=f"project root is missing {PROJECT_MARKER}",
                hint="run `lgrlw init <dir> --direction <slug>` to bootstrap",
            )
        )

    if not paths.kb.is_dir():
        findings.append(
            LintFinding(
                rule=RULE_ROOT,
                severity=LintSeverity.error,
                path=str(paths.kb),
                message=f"missing {paths.kb.name}/ directory",
                hint="restore from templates/literature-kb or re-run `lgrlw init --force`",
            )
        )

    if not paths.workspaces.is_dir():
        findings.append(
            LintFinding(
                rule=RULE_ROOT,
                severity=LintSeverity.error,
                path=str(paths.workspaces),
                message=f"missing {paths.workspaces.name}/ directory",
                hint="create an empty research-workspaces/ or re-run `lgrlw init --force`",
            )
        )

    return findings


__all__ = ["RULE_ROOT", "check_structure"]
