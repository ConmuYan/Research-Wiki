"""Tests for v0.3 multi-direction monorepo support."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.config import load_config


def test_init_monorepo_creates_umbrella_and_first_direction(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    root = tmp_path / "repo"
    result = runner.invoke(app, ["init", str(root), "--direction", "alpha", "--monorepo"])
    assert result.exit_code == 0, result.output

    umbrella = load_config(root / ".lgrlw.toml")
    assert umbrella.monorepo is True
    assert umbrella.schema_version == "1.1.0"
    assert umbrella.directions == ["alpha"]

    sub = root / "directions" / "alpha"
    assert (sub / ".lgrlw.toml").is_file()
    assert (sub / "literature-kb" / "00_System" / "KB_AGENTS.md").is_file()
    assert (sub / "research-workspaces" / "README.md").is_file()

    child = load_config(sub / ".lgrlw.toml")
    assert child.monorepo is False
    assert child.direction == "alpha"


def test_add_direction_registers_and_materialises_second_subproject(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    root = tmp_path / "repo"
    assert (
        runner.invoke(app, ["init", str(root), "--direction", "alpha", "--monorepo"]).exit_code == 0
    )

    result = runner.invoke(app, ["add-direction", "beta", "--root", str(root)])
    assert result.exit_code == 0, result.output

    cfg = load_config(root / ".lgrlw.toml")
    assert cfg.directions == ["alpha", "beta"]
    assert (root / "directions" / "beta" / "literature-kb").is_dir()
    assert (root / "directions" / "beta" / "research-workspaces").is_dir()


def test_project_scoped_commands_accept_direction_selector(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    root = tmp_path / "repo"
    assert (
        runner.invoke(app, ["init", str(root), "--direction", "alpha", "--monorepo"]).exit_code == 0
    )
    assert runner.invoke(app, ["add-direction", "beta", "--root", str(root)]).exit_code == 0

    ws = runner.invoke(
        app,
        [
            "new-workspace",
            "paper_001",
            "--title",
            "Monorepo Paper",
            "--root",
            str(root),
            "--direction",
            "beta",
        ],
    )
    assert ws.exit_code == 0, ws.output

    add = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "A Beta Paper",
            "--authors",
            "Ada Lovelace",
            "--year",
            "2024",
            "--id",
            "lovelace-2024-beta-paper",
            "--root",
            str(root),
            "--direction",
            "beta",
        ],
    )
    assert add.exit_code == 0, add.output

    beta = root / "directions" / "beta"
    alpha = root / "directions" / "alpha"
    assert (
        beta / "literature-kb" / "02_Literature" / "Papers" / "lovelace-2024-beta-paper.md"
    ).is_file()
    assert not (
        alpha / "literature-kb" / "02_Literature" / "Papers" / "lovelace-2024-beta-paper.md"
    ).exists()

    lint_one = runner.invoke(app, ["lint", "--root", str(root), "--direction", "beta"])
    assert lint_one.exit_code == 0, lint_one.output

    lint_all = runner.invoke(app, ["lint", "--root", str(root)])
    assert lint_all.exit_code == 0, lint_all.output


def test_lint_monorepo_reports_prefixed_direction_paths(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    root = tmp_path / "repo"
    assert (
        runner.invoke(app, ["init", str(root), "--direction", "alpha", "--monorepo"]).exit_code == 0
    )

    polluted = (
        root / "directions" / "alpha" / "literature-kb" / "03_Field_Structure" / "Polluted.md"
    )
    polluted.write_text(
        "# polluted\n\nSee ../../research-workspaces/paper_001/foo.md.\n",
        encoding="utf-8",
        newline="\n",
    )

    result = runner.invoke(app, ["lint", "--root", str(root)])
    assert result.exit_code != 0
    assert "boundary.workspace_reference_in_kb" in result.output
    assert "directions" in result.output
    assert "alpha" in result.output
    assert "Polluted.md" in result.output
