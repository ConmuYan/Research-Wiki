"""Atomic promotion of an accepted workspace paper into the KB.

See ``docs/promotion-protocol.md`` for the user-facing spec. The
implementation is structured as:

1. :func:`_load_workspace_status` -- read and schema-validate
   ``paper_status.md`` frontmatter.
2. :func:`_check_status_preconditions` -- enforce ``status: accepted``,
   non-null promotion fields, and ``doi`` or ``arxiv_id`` presence.
3. :func:`_check_promotion_artifacts` -- enforce
   ``06_Promotion/final_metadata.md``, ``promotion_checklist.md`` and
   ``add_back_to_kb_plan.md`` requirements.
4. :func:`_assemble_kb_frontmatter` -- mint the KB
   :class:`PaperFrontmatter` with ``source: promoted``.
5. :func:`promote_workspace` -- orchestrator. After every check has
   passed, the four KB artefacts (paper card, metadata snapshot, BibTeX
   entry, log line) are written. If any single write fails, all
   artefacts written in this run are unlinked so that promotion stays
   all-or-nothing.
"""

from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from lgrlw._slug import paper_slug
from lgrlw.fs import ensure_dir, read_frontmatter, write_frontmatter
from lgrlw.paths import ProjectPaths
from lgrlw.render.paper_card import render_paper_card
from lgrlw.schemas import (
    PaperFrontmatter,
    PaperKind,
    PaperStatus,
    WorkspacePaperFrontmatter,
    WorkspaceStatus,
)

CHECKBOX_UNTICKED_RE = re.compile(r"^\s*-\s*\[\s\]", re.MULTILINE)
CHECKBOX_TICKED_RE = re.compile(r"^\s*-\s*\[[xX]\]", re.MULTILINE)
URL_OR_PDF_RE = re.compile(r"https?://\S+|\S+\.pdf", re.IGNORECASE)
PLAN_BULLET_RE = re.compile(r"^\s*[-*]\s+\S", re.MULTILINE)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class PromoteError(RuntimeError):
    """Raised when a promote precondition fails or a write step fails."""


@dataclass(frozen=True)
class PromoteResult:
    """Filesystem artefacts produced by a successful promotion."""

    paper_id: str
    paper_card: Path
    metadata_json: Path
    bibtex: Path
    log: Path


def promote_workspace(
    paths: ProjectPaths,
    workspace_id: str,
    *,
    paper_id: str | None = None,
    force: bool = False,
    now: datetime | None = None,
) -> PromoteResult:
    """Atomically promote ``workspace_id`` into the KB.

    Parameters
    ----------
    paths:
        Resolved project paths.
    workspace_id:
        Directory name under ``research-workspaces/``.
    paper_id:
        Optional explicit slug to use for the KB paper card. Defaults to
        the canonical ``<lastname>-<year>-<title>`` slug derived from
        ``paper_status.md`` frontmatter.
    force:
        If ``True``, replace existing KB artefacts for the same paper id.
    now:
        Override the wall-clock used for ``added_on`` and the log
        timestamp. Tests inject a fixed value; production passes ``None``.
    """
    workspace_root = paths.workspace(workspace_id)
    if not workspace_root.is_dir():
        raise PromoteError(f"workspace does not exist: {workspace_root}")

    status_fm = _load_workspace_status(paths, workspace_root)
    _check_status_preconditions(status_fm)
    _check_promotion_artifacts(paths, workspace_root)

    moment = now or datetime.now(timezone.utc)
    kb_fm = _assemble_kb_frontmatter(status_fm, paper_id=paper_id, moment=moment)
    targets = _resolve_targets(paths, kb_fm.id)

    if not force:
        for label, dest in targets.items():
            if label == "log":
                continue
            if dest.exists():
                raise PromoteError(
                    f"refusing to overwrite existing {dest.relative_to(paths.root)};"
                    " re-run with --force to replace"
                )

    artefacts = _build_artefacts(kb_fm)
    _write_atomically(targets, artefacts, workspace_id, moment)

    return PromoteResult(
        paper_id=kb_fm.id,
        paper_card=targets["paper"],
        metadata_json=targets["metadata"],
        bibtex=targets["bibtex"],
        log=targets["log"],
    )


# ---------------------------------------------------------------------------
# Step 1: load & validate paper_status.md
# ---------------------------------------------------------------------------
def _load_workspace_status(paths: ProjectPaths, workspace_root: Path) -> WorkspacePaperFrontmatter:
    status_path = workspace_root / "00_Project" / "paper_status.md"
    if not status_path.is_file():
        raise PromoteError(f"missing {status_path.relative_to(paths.root)}")

    fm_dict, _ = read_frontmatter(status_path)
    if fm_dict is None:
        raise PromoteError(f"{status_path.relative_to(paths.root)} has no YAML frontmatter")

    try:
        return WorkspacePaperFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise PromoteError(
            f"{status_path.relative_to(paths.root)} frontmatter is invalid: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Step 2: enforce status / final-metadata fields on paper_status.md
# ---------------------------------------------------------------------------
def _check_status_preconditions(status_fm: WorkspacePaperFrontmatter) -> None:
    if status_fm.status != WorkspaceStatus.accepted.value:
        raise PromoteError(
            f"paper_status.md status is {status_fm.status!r}; promotion requires status: accepted"
        )

    missing = [
        name
        for name, value in (
            ("final_title", status_fm.final_title),
            ("final_authors", status_fm.final_authors),
            ("venue", status_fm.venue),
            ("year", status_fm.year),
        )
        if value is None or (isinstance(value, list) and not value)
    ]
    if missing:
        raise PromoteError(
            "paper_status.md frontmatter is missing required promotion field(s): "
            + ", ".join(missing)
        )

    if not status_fm.doi and not status_fm.arxiv_id:
        raise PromoteError(
            "paper_status.md frontmatter must set at least one of `doi` or `arxiv_id`"
        )


# ---------------------------------------------------------------------------
# Step 3: enforce 06_Promotion/* artefacts
# ---------------------------------------------------------------------------
def _check_promotion_artifacts(paths: ProjectPaths, workspace_root: Path) -> None:
    promotion_dir = workspace_root / "06_Promotion"

    final_meta = promotion_dir / "final_metadata.md"
    if not final_meta.is_file():
        raise PromoteError(f"missing {final_meta.relative_to(paths.root)}")
    final_meta_text = final_meta.read_text(encoding="utf-8")
    if not URL_OR_PDF_RE.search(final_meta_text):
        raise PromoteError(
            f"{final_meta.relative_to(paths.root)} must reference a "
            "camera-ready PDF path or public-version URL"
        )

    checklist = promotion_dir / "promotion_checklist.md"
    if not checklist.is_file():
        raise PromoteError(f"missing {checklist.relative_to(paths.root)}")
    checklist_text = checklist.read_text(encoding="utf-8")
    if CHECKBOX_UNTICKED_RE.search(checklist_text):
        raise PromoteError(
            f"{checklist.relative_to(paths.root)} has un-ticked checkboxes; "
            "every `- [ ]` must become `- [x]` before promotion"
        )
    if not CHECKBOX_TICKED_RE.search(checklist_text):
        raise PromoteError(
            f"{checklist.relative_to(paths.root)} has no GitHub-style "
            "checkboxes; expected lines like `- [x] ...`"
        )

    plan = promotion_dir / "add_back_to_kb_plan.md"
    if not plan.is_file():
        raise PromoteError(f"missing {plan.relative_to(paths.root)}")
    plan_text = HTML_COMMENT_RE.sub("", plan.read_text(encoding="utf-8"))
    if not PLAN_BULLET_RE.search(plan_text):
        raise PromoteError(
            f"{plan.relative_to(paths.root)} must list at least one intended "
            "field-structure / evidence-map edit as a `- ` bullet"
        )


# ---------------------------------------------------------------------------
# Step 4: assemble the KB-side frontmatter
# ---------------------------------------------------------------------------
def _assemble_kb_frontmatter(
    status_fm: WorkspacePaperFrontmatter,
    *,
    paper_id: str | None,
    moment: datetime,
) -> PaperFrontmatter:
    final_authors = list(status_fm.final_authors or [])
    if not final_authors:
        # _check_status_preconditions already covers this; defensive guard.
        raise PromoteError("paper_status.md final_authors is empty")
    if status_fm.year is None or status_fm.final_title is None:
        raise PromoteError("paper_status.md must define final_title and year before promotion")

    generated_id = paper_id or paper_slug(final_authors[0], status_fm.year, status_fm.final_title)

    try:
        return PaperFrontmatter(
            id=generated_id,
            title=status_fm.final_title,
            authors=final_authors,
            year=status_fm.year,
            venue=status_fm.venue,
            doi=status_fm.doi,
            arxiv_id=status_fm.arxiv_id,
            status=PaperStatus.accepted,
            source=PaperKind.promoted,
            added_on=moment.date(),
            tags=[],
        )
    except ValidationError as exc:
        raise PromoteError(f"failed to assemble KB frontmatter: {exc}") from exc


# ---------------------------------------------------------------------------
# Step 5: write artefacts atomically
# ---------------------------------------------------------------------------
def _resolve_targets(paths: ProjectPaths, paper_id: str) -> dict[str, Path]:
    return {
        "paper": paths.kb_papers / f"{paper_id}.md",
        "metadata": paths.kb_raw_metadata / f"{paper_id}.json",
        "bibtex": paths.kb_raw / "bibtex" / f"{paper_id}.bib",
        "log": paths.kb_system / "log.md",
    }


def _build_artefacts(fm: PaperFrontmatter) -> dict[str, str | dict[str, object]]:
    fm_dict = fm.model_dump(mode="json", exclude_none=True)
    return {
        "frontmatter": fm_dict,
        "body": render_paper_card(fm),
        "metadata_json": json.dumps(fm_dict, indent=2, ensure_ascii=False) + "\n",
        "bibtex": _generate_bibtex(fm) + "\n",
    }


def _write_atomically(
    targets: dict[str, Path],
    artefacts: dict[str, str | dict[str, object]],
    workspace_id: str,
    moment: datetime,
) -> None:
    written: list[Path] = []
    try:
        ensure_dir(targets["paper"].parent)
        ensure_dir(targets["metadata"].parent)
        ensure_dir(targets["bibtex"].parent)
        ensure_dir(targets["log"].parent)

        write_frontmatter(targets["paper"], artefacts["frontmatter"], artefacts["body"])  # type: ignore[arg-type]
        written.append(targets["paper"])

        targets["metadata"].write_text(artefacts["metadata_json"], encoding="utf-8")  # type: ignore[arg-type]
        written.append(targets["metadata"])

        targets["bibtex"].write_text(artefacts["bibtex"], encoding="utf-8")  # type: ignore[arg-type]
        written.append(targets["bibtex"])

        # The log append is the commit step; if it raises, roll back the
        # other three writes so promote stays all-or-nothing.
        _append_log(targets["log"], targets["paper"].stem, workspace_id, moment)
    except OSError as exc:
        for path in written:
            with contextlib.suppress(OSError):
                path.unlink()
        raise PromoteError(f"failed to write promotion artefacts: {exc}") from exc


def _append_log(path: Path, paper_id: str, workspace_id: str, moment: datetime) -> None:
    timestamp = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"- {timestamp}  promote workspace={workspace_id} id={paper_id}\n"
    if path.is_file():
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        path.write_text(f"# KB Log\n\n{entry}", encoding="utf-8")


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------
def _generate_bibtex(fm: PaperFrontmatter) -> str:
    """Return a minimal BibTeX entry derived from a KB paper frontmatter.

    ``@inproceedings`` is used when ``venue`` is set, ``@misc`` otherwise.
    Identifiers (DOI, arXiv id) are recorded so the entry is still useful
    even if the user later replaces it with a hand-curated version.
    """
    entry_type = "inproceedings" if fm.venue else "misc"
    bib_fields: list[tuple[str, str]] = [
        ("title", fm.title),
        ("author", " and ".join(fm.authors)),
        ("year", str(fm.year)),
    ]
    if fm.venue:
        bib_fields.append(("booktitle", fm.venue))
    if fm.doi:
        bib_fields.append(("doi", fm.doi))
    if fm.arxiv_id:
        bib_fields.append(("eprint", fm.arxiv_id))
        bib_fields.append(("archivePrefix", "arXiv"))
    if fm.url:
        bib_fields.append(("url", fm.url))

    rendered = ",\n".join(f"  {key} = {{{value}}}" for key, value in bib_fields)
    return f"@{entry_type}{{{fm.id},\n{rendered}\n}}"


__all__ = [
    "PromoteError",
    "PromoteResult",
    "promote_workspace",
]
