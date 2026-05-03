"""Tests for ``lgrlw promote``.

Each test starts from the ``paper_workspace`` fixture, which sets up a
fresh Research-Wiki project plus a workspace whose
``paper_status.md`` / ``06_Promotion/*`` files satisfy *every* promote
precondition. Failure-mode tests then mutate exactly one input and
confirm the promotion command rejects it with a non-zero exit and writes
nothing to the KB.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter, write_frontmatter

WORKSPACE_NAME = "paper_acceptme"
EXPECTED_PAPER_ID = "a-2026-accept-me-paper"


@pytest.fixture()
def paper_workspace(project: Path, runner: CliRunner) -> Path:
    """A workspace that already satisfies every promote precondition."""
    result = runner.invoke(
        app,
        [
            "new-workspace",
            WORKSPACE_NAME,
            "--title",
            "Accept Me Paper",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output

    ws = project / "research-workspaces" / WORKSPACE_NAME

    status_path = ws / "00_Project" / "paper_status.md"
    status_fm, status_body = read_frontmatter(status_path)
    assert status_fm is not None
    status_fm.update(
        {
            "status": "accepted",
            "final_title": "Accept Me Paper",
            "final_authors": ["Alice A", "Bob B"],
            "venue": "ICLR 2026",
            "year": 2026,
            "doi": "10.5555/example",
        }
    )
    write_frontmatter(status_path, status_fm, status_body)

    promotion = ws / "06_Promotion"
    (promotion / "final_metadata.md").write_text(
        "# Final metadata\n\nCamera-ready PDF: https://example.com/papers/accept-me.pdf\n",
        encoding="utf-8",
    )

    checklist_path = promotion / "promotion_checklist.md"
    checklist_text = checklist_path.read_text(encoding="utf-8")
    checklist_path.write_text(checklist_text.replace("- [ ]", "- [x]"), encoding="utf-8")

    (promotion / "add_back_to_kb_plan.md").write_text(
        "# Add-back-to-KB plan\n\n"
        "- Update 03_Field_Structure/method_taxonomy.md to reference our method.\n"
        "- Append a claim to 05_Evidence/claims.md citing this paper.\n",
        encoding="utf-8",
    )

    return ws


def _invoke_promote(runner: CliRunner, project: Path, *extra: str) -> tuple[int, str]:
    result = runner.invoke(
        app,
        ["promote", WORKSPACE_NAME, "--root", str(project), *extra],
    )
    return result.exit_code, result.output


def _kb_artefacts(project: Path, paper_id: str = EXPECTED_PAPER_ID) -> dict[str, Path]:
    kb = project / "literature-kb"
    return {
        "card": kb / "02_Literature" / "Papers" / f"{paper_id}.md",
        "metadata": kb / "01_Raw" / "metadata" / f"{paper_id}.json",
        "bibtex": kb / "01_Raw" / "bibtex" / f"{paper_id}.bib",
        "log": kb / "00_System" / "log.md",
    }


def _assert_no_kb_artefacts(project: Path) -> None:
    artefacts = _kb_artefacts(project)
    for path in (artefacts["card"], artefacts["metadata"], artefacts["bibtex"]):
        assert not path.exists(), f"unexpected artefact survived: {path}"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_promote_happy_path_writes_all_artefacts(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    exit_code, output = _invoke_promote(runner, project)
    assert exit_code == 0, output
    assert "promoted" in output
    assert "add_back_to_kb_plan.md" in output  # follow-up reminder

    artefacts = _kb_artefacts(project)
    fm, body = read_frontmatter(artefacts["card"])
    assert fm is not None
    assert fm["title"] == "Accept Me Paper"
    assert fm["authors"] == ["Alice A", "Bob B"]
    assert fm["year"] == 2026
    assert fm["venue"] == "ICLR 2026"
    assert fm["doi"] == "10.5555/example"
    assert fm["status"] == "accepted"
    assert fm["source"] == "promoted"
    assert "Accept Me Paper" in body

    metadata = json.loads(artefacts["metadata"].read_text(encoding="utf-8"))
    assert metadata["source"] == "promoted"
    assert metadata["doi"] == "10.5555/example"

    bibtex = artefacts["bibtex"].read_text(encoding="utf-8")
    assert bibtex.startswith(f"@inproceedings{{{EXPECTED_PAPER_ID},")
    assert "title = {Accept Me Paper}" in bibtex
    assert "author = {Alice A and Bob B}" in bibtex
    assert "booktitle = {ICLR 2026}" in bibtex
    assert "doi = {10.5555/example}" in bibtex

    log = artefacts["log"].read_text(encoding="utf-8")
    assert f"promote workspace={WORKSPACE_NAME} id={EXPECTED_PAPER_ID}" in log


def test_promote_workspace_is_left_untouched(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    before = status_path.read_text(encoding="utf-8")

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code == 0, output

    after = status_path.read_text(encoding="utf-8")
    assert before == after


def test_promote_kb_passes_lint_after_promotion(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    exit_code, output = _invoke_promote(runner, project)
    assert exit_code == 0, output

    lint_result = runner.invoke(app, ["lint", "--root", str(project)])
    assert lint_result.exit_code == 0, lint_result.output


# ---------------------------------------------------------------------------
# Precondition rejections
# ---------------------------------------------------------------------------
def test_promote_rejects_status_not_accepted(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm["status"] = "writing"
    write_frontmatter(status_path, fm, body)

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "status: accepted" in output
    _assert_no_kb_artefacts(project)


def test_promote_rejects_missing_final_title(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm.pop("final_title", None)
    write_frontmatter(status_path, fm, body)

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "final_title" in output
    _assert_no_kb_artefacts(project)


def test_promote_rejects_missing_doi_and_arxiv_id(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm.pop("doi", None)
    fm.pop("arxiv_id", None)
    write_frontmatter(status_path, fm, body)

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "doi" in output and "arxiv_id" in output
    _assert_no_kb_artefacts(project)


def test_promote_rejects_final_metadata_without_url_or_pdf(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    final_meta = paper_workspace / "06_Promotion" / "final_metadata.md"
    final_meta.write_text("# Final metadata\n\nNo links here yet.\n", encoding="utf-8")

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "camera-ready" in output.lower() or "pdf" in output.lower()
    _assert_no_kb_artefacts(project)


def test_promote_rejects_unticked_checklist(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    checklist = paper_workspace / "06_Promotion" / "promotion_checklist.md"
    text = checklist.read_text(encoding="utf-8")
    # Re-introduce one un-ticked box.
    text = text.replace("- [x] Taxonomy impact", "- [ ] Taxonomy impact", 1)
    checklist.write_text(text, encoding="utf-8")

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "checkbox" in output.lower()
    # Regression guard: Rich console must not interpret the literal `[x]`
    # token in the error message as a markup tag and silently eat it.
    assert "[x]" in output
    assert "[ ]" in output
    _assert_no_kb_artefacts(project)


def test_promote_rejects_checklist_with_no_checkboxes(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    checklist = paper_workspace / "06_Promotion" / "promotion_checklist.md"
    checklist.write_text("# Promotion checklist\n\nNo boxes here.\n", encoding="utf-8")

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "checkbox" in output.lower()
    _assert_no_kb_artefacts(project)


def test_promote_rejects_empty_add_back_plan(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    plan = paper_workspace / "06_Promotion" / "add_back_to_kb_plan.md"
    plan.write_text(
        "# Add-back-to-KB plan\n\nNo concrete edits planned yet.\n",
        encoding="utf-8",
    )

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "bullet" in output.lower() or "field-structure" in output.lower()
    _assert_no_kb_artefacts(project)


def test_promote_rejects_missing_workspace(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(app, ["promote", "no_such_workspace", "--root", str(project)])
    assert result.exit_code != 0
    assert "workspace does not exist" in result.output


# ---------------------------------------------------------------------------
# --id and --force behaviours
# ---------------------------------------------------------------------------
def test_promote_honours_id_override(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    custom = "alice-2026-custom-promo-id"

    exit_code, output = _invoke_promote(runner, project, "--id", custom)
    assert exit_code == 0, output

    artefacts = _kb_artefacts(project, paper_id=custom)
    assert artefacts["card"].is_file()
    assert artefacts["metadata"].is_file()
    assert artefacts["bibtex"].is_file()
    fm, _ = read_frontmatter(artefacts["card"])
    assert fm is not None
    assert fm["id"] == custom


def test_promote_without_force_refuses_overwrite(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    first_exit, first_output = _invoke_promote(runner, project)
    assert first_exit == 0, first_output

    second_exit, second_output = _invoke_promote(runner, project)
    assert second_exit != 0
    assert "--force" in second_output


def test_promote_force_replaces_existing(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    fixed_id = "alice-2026-accept-me"
    first_exit, first_output = _invoke_promote(runner, project, "--id", fixed_id)
    assert first_exit == 0, first_output

    # Mutate venue. We pin the slug via --id so both runs target the same
    # KB artefacts; without that, changing final_title would also change
    # the auto-generated slug and we would write to a different file.
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm["venue"] = "ICLR 2026 (camera-ready)"
    write_frontmatter(status_path, fm, body)

    second_exit, second_output = _invoke_promote(runner, project, "--id", fixed_id, "--force")
    assert second_exit == 0, second_output

    artefacts = _kb_artefacts(project, paper_id=fixed_id)
    fm_after, _ = read_frontmatter(artefacts["card"])
    assert fm_after is not None
    assert fm_after["venue"] == "ICLR 2026 (camera-ready)"

    log = artefacts["log"].read_text(encoding="utf-8")
    # Two log lines: original promote + replacement promote, same id.
    assert log.count(f"promote workspace={WORKSPACE_NAME} id={fixed_id}") == 2


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------
def test_promote_failure_leaves_no_partial_artefacts(
    project: Path, runner: CliRunner, paper_workspace: Path
) -> None:
    # Break the doi to force PaperFrontmatter validation to fail *after*
    # the precondition checks pass and inside _assemble_kb_frontmatter.
    status_path = paper_workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm["doi"] = "definitely-not-a-doi"
    write_frontmatter(status_path, fm, body)

    exit_code, output = _invoke_promote(runner, project)
    assert exit_code != 0
    assert "frontmatter" in output.lower() or "doi" in output.lower()
    _assert_no_kb_artefacts(project)
