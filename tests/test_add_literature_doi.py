"""Tests for ``lgrlw add-literature --doi``."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fetchers.crossref import CROSSREF_WORKS_URL
from lgrlw.fs import read_frontmatter


def test_add_doi_fetches_crossref_and_writes_entry(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/example").mock(
        return_value=httpx.Response(200, json={"message": _crossref_message()})
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--doi",
            "https://doi.org/10.5555/EXAMPLE",
            "--tags",
            "retrieval,rag",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    assert route.called

    paper = project / "literature-kb" / "02_Literature" / "Papers" / "a-2024-example-paper.md"
    assert paper.is_file()
    fm, body = read_frontmatter(paper)
    assert fm is not None
    assert fm["title"] == "Example Paper"
    assert fm["authors"] == ["Alice A", "Bob B"]
    assert fm["year"] == 2024
    assert fm["venue"] == "ExampleConf"
    assert fm["doi"] == "10.5555/example"
    assert fm["source"] == "crossref"
    assert fm["tags"] == ["retrieval", "rag"]
    assert "Example Paper" in body

    metadata = json.loads(
        (project / "literature-kb" / "01_Raw" / "metadata" / "a-2024-example-paper.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["id"] == "a-2024-example-paper"
    assert metadata["source"] == "crossref"

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert "add-literature doi add id=a-2024-example-paper" in log


def test_add_doi_rejects_manual_metadata_overrides(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--doi",
            "10.5555/example",
            "--title",
            "Hand Override",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "--manual" in result.output


def test_add_doi_fetch_failure_writes_nothing(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/missing").mock(
        return_value=httpx.Response(404, json={"status": "error"})
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--doi",
            "10.5555/missing",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    metadata_dir = project / "literature-kb" / "01_Raw" / "metadata"
    assert [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"] == []
    assert [p for p in metadata_dir.glob("*.json") if p.name != ".gitkeep"] == []


def test_add_doi_rejects_duplicate_without_force(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/example").mock(
        return_value=httpx.Response(200, json={"message": _crossref_message()})
    )

    first = runner.invoke(
        app,
        ["add-literature", "--doi", "10.5555/example", "--root", str(project)],
    )
    second = runner.invoke(
        app,
        ["add-literature", "--doi", "10.5555/example", "--root", str(project)],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code != 0
    assert "--force" in second.output


def test_add_manual_with_doi_remains_manual(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Manual DOI Paper",
            "--authors",
            "Alice A",
            "--year",
            "2024",
            "--doi",
            "10.5555/manual",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    paper = project / "literature-kb" / "02_Literature" / "Papers" / "a-2024-manual-doi-paper.md"
    fm, _ = read_frontmatter(paper)
    assert fm is not None
    assert fm["doi"] == "10.5555/manual"
    assert fm["source"] == "manual"


def _crossref_message() -> dict[str, object]:
    return {
        "title": ["Example Paper"],
        "author": [
            {"given": "Alice", "family": "A"},
            {"given": "Bob", "family": "B"},
        ],
        "published-print": {"date-parts": [[2024, 1, 1]]},
        "container-title": ["ExampleConf"],
        "DOI": "10.5555/example",
        "URL": "https://doi.org/10.5555/example",
    }
