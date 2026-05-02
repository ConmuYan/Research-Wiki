"""Tests for ``lgrlw export-pack``."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import sha256_file


def _seed_project(project: Path, runner: CliRunner) -> str:
    """Create a workspace and two literature entries; return workspace id."""
    runner.invoke(
        app,
        ["new-workspace", "paper_001", "--title", "working title", "--root", str(project)],
    )
    runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "First paper",
            "--authors",
            "Alice A",
            "--year",
            "2020",
            "--root",
            str(project),
        ],
    )
    runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Second paper",
            "--authors",
            "Bob B",
            "--year",
            "2021",
            "--root",
            str(project),
        ],
    )
    return "paper_001"


def test_export_pack_builds_manifest_and_mirror(project: Path, runner: CliRunner) -> None:
    workspace_id = _seed_project(project, runner)
    r = runner.invoke(app, ["export-pack", workspace_id, "--root", str(project)])
    assert r.exit_code == 0, r.output

    exports = list((project / "literature-kb" / "06_Exports").iterdir())
    pack_dirs = [p for p in exports if p.is_dir()]
    assert len(pack_dirs) == 1
    pack = pack_dirs[0]
    assert pack.name.startswith(workspace_id + "_")

    manifest_path = pack / "export_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["workspace_id"] == workspace_id
    assert manifest["schema_version"] == "1.0.0"
    assert len(manifest["paper_ids"]) == 2
    assert len(manifest["files"]) >= 2
    _assert_manifest_paths_are_relative_posix(manifest)

    # Every listed SHA-256 matches the on-disk file.
    for rel, expected in manifest["files"].items():
        actual = sha256_file(pack / rel)
        assert actual == expected, f"sha256 mismatch for {rel}"

    # A bit-identical mirror lands in the workspace.
    mirror = project / "research-workspaces" / workspace_id / "01_KB_Exports" / pack.name
    assert mirror.is_dir()
    assert (mirror / "export_manifest.json").is_file()


def test_export_pack_fails_for_missing_workspace(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(app, ["export-pack", "does_not_exist", "--root", str(project)])
    assert r.exit_code != 0


def test_export_pack_refuses_same_day_collision(project: Path, runner: CliRunner) -> None:
    workspace_id = _seed_project(project, runner)
    r1 = runner.invoke(app, ["export-pack", workspace_id, "--root", str(project)])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["export-pack", workspace_id, "--root", str(project)])
    assert r2.exit_code != 0


def _assert_manifest_paths_are_relative_posix(manifest: dict[str, object]) -> None:
    paths = [
        str(manifest["kb_root_relative"]),
        str(manifest["pack_dir_relative"]),
        *[str(p) for p in dict(manifest["files"])],
    ]
    for rel in paths:
        assert rel
        assert "\\" not in rel
        assert not rel.startswith("/")
        assert not re.match(r"^[A-Za-z]:", rel)
        assert not any(part in {"", ".", ".."} for part in rel.split("/"))
