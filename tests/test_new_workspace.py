"""Tests for ``lgrlw new-workspace``."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter


def test_new_paper_workspace_has_valid_status_frontmatter(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(
        app,
        [
            "new-workspace",
            "paper_001",
            "--title",
            "A working title",
            "--root",
            str(project),
        ],
    )
    assert r.exit_code == 0, r.output

    ws = project / "research-workspaces" / "paper_001"
    assert ws.is_dir()
    assert (ws / "00_Project" / "PAPER_AGENTS.md").is_file()
    assert (ws / "01_KB_Exports").is_dir()

    status_path = ws / "00_Project" / "paper_status.md"
    assert status_path.is_file()
    fm, _ = read_frontmatter(status_path)
    assert fm is not None
    assert fm["type"] == "workspace_paper"
    assert fm["id"] == "paper_001"
    assert fm["kind"] == "paper"
    assert fm["title"] == "A working title"
    assert fm["status"] == "drafting"
    # created_on is emitted as an ISO date string.
    assert isinstance(fm["created_on"], str)
    assert len(fm["created_on"]) == len("2026-05-02")


def test_new_idea_workspace(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(
        app,
        [
            "new-workspace",
            "idea_abc",
            "--title",
            "An idea",
            "--kind",
            "idea",
            "--root",
            str(project),
        ],
    )
    assert r.exit_code == 0, r.output
    assert (project / "research-workspaces" / "idea_abc" / "IDEA_AGENTS.md").is_file()


def test_new_workspace_rejects_bad_id(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(
        app,
        [
            "new-workspace",
            "Paper 001!",
            "--title",
            "demo title",
            "--root",
            str(project),
        ],
    )
    assert r.exit_code != 0


def test_new_workspace_refuses_existing(project: Path, runner: CliRunner) -> None:
    args = [
        "new-workspace",
        "paper_001",
        "--title",
        "demo title",
        "--root",
        str(project),
    ]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code != 0
