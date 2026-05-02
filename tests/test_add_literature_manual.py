"""Tests for ``lgrlw add-literature --manual``."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter


def _add(runner: CliRunner, project: Path, **overrides: str) -> object:
    """Invoke add-literature with sensible defaults, overridable per-test."""
    args = [
        "add-literature",
        "--manual",
        "--title",
        overrides.pop("title", "Self-RAG: Self-Reflective RAG"),
        "--authors",
        overrides.pop("authors", "Akari Asai, Zeqiu Wu"),
        "--year",
        overrides.pop("year", "2023"),
        "--root",
        str(project),
    ]
    for key, value in overrides.items():
        args.extend([f"--{key}", value])
    return runner.invoke(app, args)


def test_add_manual_writes_paper_card_and_metadata(project: Path, runner: CliRunner) -> None:
    r = _add(
        runner,
        project,
        venue="ICLR 2024",
        arxiv="2310.11511",
        tags="rag,llm,retrieval",
    )
    assert r.exit_code == 0, r.output

    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    papers = [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"]
    assert len(papers) == 1
    paper = papers[0]

    fm, body = read_frontmatter(paper)
    assert fm is not None
    assert fm["type"] == "paper"
    assert fm["title"].startswith("Self-RAG")
    assert fm["authors"] == ["Akari Asai", "Zeqiu Wu"]
    assert fm["year"] == 2023
    assert fm["arxiv_id"] == "2310.11511"
    assert fm["source"] == "manual"
    assert fm["status"] == "published"
    assert fm["tags"] == ["rag", "llm", "retrieval"]
    assert "Self-RAG" in body
    assert "Summary" in body

    meta_dir = project / "literature-kb" / "01_Raw" / "metadata"
    meta_files = [p for p in meta_dir.glob("*.json") if p.stem == fm["id"]]
    assert len(meta_files) == 1
    meta = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert meta["id"] == fm["id"]
    assert meta["year"] == 2023

    log = project / "literature-kb" / "00_System" / "log.md"
    assert log.is_file()
    assert fm["id"] in log.read_text(encoding="utf-8")


def test_add_requires_manual_flag(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(
        app,
        [
            "add-literature",
            "--title",
            "X",
            "--authors",
            "Y",
            "--year",
            "2023",
            "--root",
            str(project),
        ],
    )
    assert r.exit_code != 0
    assert "v0.1" in r.output or "manual" in r.output.lower()


def test_add_rejects_missing_required_fields(project: Path, runner: CliRunner) -> None:
    r = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "X",
            "--root",
            str(project),
        ],
    )
    assert r.exit_code != 0


def test_add_rejects_duplicate_id(project: Path, runner: CliRunner) -> None:
    r1 = _add(runner, project, id="alice-2023-thing", title="Thing", authors="Alice A")
    assert r1.exit_code == 0, r1.output
    r2 = _add(runner, project, id="alice-2023-thing", title="Thing", authors="Alice A")
    assert r2.exit_code != 0
    assert "--force" in r2.output


def test_add_force_replaces_duplicate_id(project: Path, runner: CliRunner) -> None:
    r1 = _add(runner, project, id="alice-2023-thing", title="Original Thing", authors="Alice A")
    assert r1.exit_code == 0, r1.output

    r2 = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Replacement Thing",
            "--authors",
            "Alice A",
            "--year",
            "2023",
            "--id",
            "alice-2023-thing",
            "--force",
            "--root",
            str(project),
        ],
    )
    assert r2.exit_code == 0, r2.output

    paper = project / "literature-kb" / "02_Literature" / "Papers" / "alice-2023-thing.md"
    fm, _ = read_frontmatter(paper)
    assert fm is not None
    assert fm["title"] == "Replacement Thing"

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert "replace id=alice-2023-thing" in log


def test_add_rejects_invalid_doi(project: Path, runner: CliRunner) -> None:
    r = _add(
        runner,
        project,
        doi="not-a-doi",
    )
    assert r.exit_code != 0
