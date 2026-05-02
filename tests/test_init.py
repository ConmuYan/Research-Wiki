"""Tests for ``lgrlw init``."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.config import load_config


def test_init_creates_three_space_layout(tmp_path: Path, runner: CliRunner) -> None:
    target = tmp_path / "proj"
    result = runner.invoke(app, ["init", str(target), "--direction", "efficient-llm-inference"])
    assert result.exit_code == 0, result.output

    assert (target / ".lgrlw.toml").is_file()
    assert (target / "literature-kb").is_dir()
    assert (target / "literature-kb" / "00_System" / "KB_AGENTS.md").is_file()
    assert (target / "literature-kb" / "03_Field_Structure" / "Overview.md").is_file()
    assert (target / "literature-kb" / "05_Evidence" / "Evidence_Map.md").is_file()
    assert (target / "literature-kb" / "02_Literature" / "Papers").is_dir()
    assert (target / "literature-kb" / "06_Exports").is_dir()

    assert (target / "research-workspaces").is_dir()
    assert (target / "research-workspaces" / "README.md").is_file()


def test_init_writes_valid_config(tmp_path: Path, runner: CliRunner) -> None:
    target = tmp_path / "proj"
    runner.invoke(app, ["init", str(target), "--direction", "my-area"])
    cfg = load_config(target / ".lgrlw.toml")
    assert cfg.direction == "my-area"
    assert cfg.kb_name == "literature-kb"
    assert cfg.workspaces_name == "research-workspaces"


def test_init_refuses_existing_project(tmp_path: Path, runner: CliRunner) -> None:
    target = tmp_path / "proj"
    r1 = runner.invoke(app, ["init", str(target), "--direction", "x"])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["init", str(target), "--direction", "x"])
    assert r2.exit_code != 0
    assert "already hosts" in r2.output.lower() or "already" in r2.output.lower()


def test_init_force_reinit(tmp_path: Path, runner: CliRunner) -> None:
    target = tmp_path / "proj"
    runner.invoke(app, ["init", str(target), "--direction", "x"])
    r = runner.invoke(app, ["init", str(target), "--direction", "x", "--force"])
    assert r.exit_code == 0
