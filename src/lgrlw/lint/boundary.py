"""Three-space boundary checks.

The KB is *public literature*. Nothing that is currently a workspace artefact
-- idea, hypothesis, experiment, rebuttal, unaccepted contribution -- may
live inside ``literature-kb/`` or be referenced from a KB page.

In v0.1 we enforce:

1. **No reference to research-workspaces/ from any KB markdown.** A link like
   ``../research-workspaces/paper_001/...`` inside the KB is always a
   pollution bug.
2. **No workspace-only frontmatter type inside the KB.** ``type:
   workspace_paper``, ``type: idea``, ``type: experiment``, ``type:
   rebuttal`` are invalid as KB frontmatter.
3. **No workspace-only status value inside the KB.** A KB page using a
   :class:`~lgrlw.schemas.WorkspaceStatus` value that is *not* also a
   :class:`~lgrlw.schemas.PaperStatus` value (e.g. ``drafting``,
   ``under_review``, ``rejected``) is flagged.

Export packs under ``literature-kb/06_Exports/`` are exempt from (1)-(3):
they are frozen snapshots and boundary-checking their contents a second time
would be redundant (the contents already passed the check when they were in
the live KB, and the manifest lint verifies they have not been tampered with).

``literature-kb/00_System/`` is exempt from rule (1) only. Its files are KB
*tooling* documentation (KB_AGENTS.md, export_protocol.md, &hellip;) that
legitimately describe the workspace layout *by name*. They carry no
frontmatter, so rules (2) and (3) do not apply regardless.
"""

from __future__ import annotations

import re

from lgrlw.fs import read_frontmatter
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import LintFinding, LintSeverity, PaperStatus, WorkspaceStatus

RULE_REF = "boundary.workspace_reference_in_kb"
RULE_TYPE = "boundary.workspace_frontmatter_in_kb"
RULE_STATUS = "boundary.workspace_status_in_kb"

# Any reference to the workspaces tree from within the KB is forbidden.
# We match both relative forms (../research-workspaces/...) and the bare
# segment (research-workspaces/...).
_WORKSPACE_REF_RE = re.compile(r"(?:(?:\.\./)+|/|^|\s|\(|\[|\"|')research-workspaces/")

# Frontmatter `type:` values that never belong in the KB.
_WORKSPACE_ONLY_TYPES = frozenset({"workspace_paper", "idea", "experiment", "rebuttal"})

# WorkspaceStatus values that are *not* simultaneously a valid PaperStatus.
_KB_FORBIDDEN_STATUSES = frozenset(
    {ws.value for ws in WorkspaceStatus} - {ps.value for ps in PaperStatus}
)


def check_boundary(paths: ProjectPaths) -> list[LintFinding]:
    """Return one or more findings per KB markdown file that violates the boundary."""
    findings: list[LintFinding] = []

    if not paths.kb.is_dir():
        return findings

    for md in sorted(paths.kb.rglob("*.md")):
        # Export packs are immutable snapshots; exempted from boundary lint.
        if _is_inside(md, paths.kb_exports):
            continue

        text = md.read_text(encoding="utf-8", errors="replace")

        # Rule 1: no reference to the workspaces tree.
        # 00_System/ hosts KB tooling docs that legitimately name the
        # workspace layout (KB_AGENTS.md, export_protocol.md, ...).
        if not _is_inside(md, paths.kb_system) and _WORKSPACE_REF_RE.search(text):
            findings.append(
                LintFinding(
                    rule=RULE_REF,
                    severity=LintSeverity.error,
                    path=str(md),
                    message=("KB page references the research-workspaces/ tree"),
                    hint=(
                        "the KB must never link to workspace content; "
                        "only accepted papers may return via `lgrlw promote`"
                    ),
                )
            )

        # Rule 2 & 3: forbidden frontmatter type / status.
        fm, _ = read_frontmatter(md)
        if fm is None:
            continue

        declared_type = fm.get("type")
        if isinstance(declared_type, str) and declared_type in _WORKSPACE_ONLY_TYPES:
            findings.append(
                LintFinding(
                    rule=RULE_TYPE,
                    severity=LintSeverity.error,
                    path=str(md),
                    message=(f"KB page has workspace-only frontmatter type={declared_type!r}"),
                    hint="workspace pages belong in research-workspaces/<id>/, not in the KB",
                )
            )

        declared_status = fm.get("status")
        if isinstance(declared_status, str) and declared_status in _KB_FORBIDDEN_STATUSES:
            findings.append(
                LintFinding(
                    rule=RULE_STATUS,
                    severity=LintSeverity.error,
                    path=str(md),
                    message=(f"KB page has workspace-only status={declared_status!r}"),
                    hint=(
                        "KB pages use PaperStatus (published / accepted / preprint); "
                        "WorkspaceStatus values must stay inside research-workspaces/"
                    ),
                )
            )

    return findings


def _is_inside(path, parent) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


__all__ = ["RULE_REF", "RULE_STATUS", "RULE_TYPE", "check_boundary"]
