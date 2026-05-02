"""Shared pytest fixtures for Research-Wiki CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lgrlw.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    """A Typer-compatible CliRunner."""
    return CliRunner()


@pytest.fixture()
def project(tmp_path: Path, runner: CliRunner) -> Path:
    """A freshly initialised Research-Wiki project under ``tmp_path/demo``."""
    target = tmp_path / "demo"
    result = runner.invoke(app, ["init", str(target), "--direction", "test-direction"])
    assert result.exit_code == 0, result.output
    return target
