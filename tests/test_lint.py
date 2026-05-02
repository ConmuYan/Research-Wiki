"""Tests for ``lgrlw lint``."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app


def _add_one_paper(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "A paper",
            "--authors",
            "X Y",
            "--year",
            "2020",
            "--root",
            str(project),
        ],
    )


def test_lint_passes_on_fresh_project(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code == 0, r.output


def test_lint_accepts_root_option(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(app, ["lint", "--root", str(project)])
    assert r.exit_code == 0, r.output


def test_lint_passes_after_full_mvp_loop(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)])

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code == 0, r.output


def test_lint_catches_workspace_reference_in_kb(project: Path, runner: CliRunner) -> None:
    polluted = project / "literature-kb" / "03_Field_Structure" / "Polluted.md"
    polluted.write_text(
        "# polluted\n\nSee [my idea](../../research-workspaces/paper_001/foo.md).\n",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "workspace_reference_in_kb" in r.output


def test_lint_catches_paper_without_frontmatter(project: Path, runner: CliRunner) -> None:
    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    (papers_dir / "bogus.md").write_text("# this has no frontmatter\n", encoding="utf-8")
    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "schema.paper.missing_frontmatter" in r.output


def test_lint_catches_workspace_only_status_in_kb(project: Path, runner: CliRunner) -> None:
    _add_one_paper(project, runner)
    paper = next(
        p
        for p in (project / "literature-kb" / "02_Literature" / "Papers").glob("*.md")
        if p.name != ".gitkeep"
    )
    text = paper.read_text(encoding="utf-8")
    # Corrupt the status line to a workspace-only value.
    corrupted = text.replace("status: published", "status: under_review")
    paper.write_text(corrupted, encoding="utf-8")

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "workspace_status_in_kb" in r.output or "schema.paper.validation" in r.output


def test_lint_catches_manifest_tampering(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    assert runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)]).exit_code == 0

    pack = next(p for p in (project / "literature-kb" / "06_Exports").iterdir() if p.is_dir())
    paper_in_pack = next((pack / "02_Literature" / "Papers").glob("*.md"))
    paper_in_pack.write_text(
        paper_in_pack.read_text(encoding="utf-8") + "\n<!-- tamper -->\n",
        encoding="utf-8",
    )

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "sha256_mismatch" in r.output


def test_lint_catches_missing_manifest(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)])

    pack = next(p for p in (project / "literature-kb" / "06_Exports").iterdir() if p.is_dir())
    (pack / "export_manifest.json").unlink()

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "manifest.missing" in r.output


def test_lint_allows_00_system_references_to_workspaces(project: Path, runner: CliRunner) -> None:
    """The KB's own tooling docs legitimately mention the workspaces path."""
    # The bundled template already contains such references; the fresh
    # project must lint clean regardless.
    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code == 0, r.output


def test_lint_accepts_published_accepted_preprint_statuses(
    project: Path, runner: CliRunner
) -> None:
    for status in ("published", "accepted", "preprint"):
        runner.invoke(
            app,
            [
                "add-literature",
                "--manual",
                "--title",
                f"paper {status}",
                "--authors",
                "X Y",
                "--year",
                "2023",
                "--status",
                status,
                "--id",
                f"x-2023-{status}",
                "--root",
                str(project),
            ],
        )
    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code == 0, r.output


def test_lint_catches_manifest_json_corruption(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)])

    pack = next(p for p in (project / "literature-kb" / "06_Exports").iterdir() if p.is_dir())
    manifest_path = pack / "export_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Introduce a sha256 field that doesn't match the actual file contents.
    first_key = next(iter(data["files"]))
    data["files"][first_key] = "0" * 64
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "sha256_mismatch" in r.output


def test_lint_fails_on_warning_only_findings(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)])

    pack = next(p for p in (project / "literature-kb" / "06_Exports").iterdir() if p.is_dir())
    (pack / "extra.md").write_text("# extra\n", encoding="utf-8")

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "manifest.file_extra" in r.output
    assert "0 error(s), 1 warning(s)" in r.output


def test_lint_rejects_manifest_absolute_or_drive_paths(project: Path, runner: CliRunner) -> None:
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "demo title", "--root", str(project)],
    )
    _add_one_paper(project, runner)
    runner.invoke(app, ["export-pack", "paper_001", "--root", str(project)])

    pack = next(p for p in (project / "literature-kb" / "06_Exports").iterdir() if p.is_dir())
    manifest_path = pack / "export_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["files"]["C:/absolute/evil.md"] = "0" * 64
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    r = runner.invoke(app, ["lint", str(project)])
    assert r.exit_code != 0
    assert "manifest.invalid" in r.output
