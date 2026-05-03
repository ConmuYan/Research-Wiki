"""Tests for ``lgrlw add-literature --openalex``."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fetchers.openalex import OPENALEX_WORKS_URL
from lgrlw.fs import read_frontmatter


def test_add_openalex_fetches_metadata_and_writes_entry(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{OPENALEX_WORKS_URL}/W4385545131").mock(
        return_value=httpx.Response(200, json=_openalex_payload())
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--openalex",
            "https://openalex.org/W4385545131",
            "--tags",
            "rag,llm",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    assert route.called

    paper_id = "asai-2023-self-rag"
    paper = project / "literature-kb" / "02_Literature" / "Papers" / f"{paper_id}.md"
    assert paper.is_file()
    fm, body = read_frontmatter(paper)
    assert fm is not None
    assert fm["title"] == "Self-RAG"
    assert fm["authors"] == ["Akari Asai", "Zeqiu Wu"]
    assert fm["year"] == 2023
    assert fm["venue"] == "arXiv (Cornell University)"
    assert fm["openalex_id"] == "W4385545131"
    assert fm["doi"] == "10.48550/arxiv.2310.11511"
    assert fm["source"] == "openalex"
    assert fm["tags"] == ["rag", "llm"]
    assert "Self-RAG" in body

    metadata = json.loads(
        (project / "literature-kb" / "01_Raw" / "metadata" / f"{paper_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["source"] == "openalex"
    assert metadata["openalex_id"] == "W4385545131"

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert f"add-literature openalex add id={paper_id}" in log


def test_add_openalex_rejects_manual_metadata_overrides(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--openalex",
            "W4385545131",
            "--title",
            "Hand Override",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "--manual" in result.output


def test_add_openalex_fetch_failure_writes_nothing(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{OPENALEX_WORKS_URL}/W0000000000").mock(
        return_value=httpx.Response(404, json={"error": "missing"})
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--openalex",
            "W0000000000",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    metadata_dir = project / "literature-kb" / "01_Raw" / "metadata"
    assert [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"] == []
    assert [p for p in metadata_dir.glob("*.json") if p.name != ".gitkeep"] == []


def test_add_doi_arxiv_openalex_are_mutually_exclusive(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--doi",
            "10.5555/example",
            "--openalex",
            "W4385545131",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "exactly one" in result.output


def test_add_manual_with_openalex_remains_manual(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Manual OpenAlex Paper",
            "--authors",
            "Alice A",
            "--year",
            "2024",
            "--openalex",
            "W4385545131",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    paper = (
        project / "literature-kb" / "02_Literature" / "Papers" / "a-2024-manual-openalex-paper.md"
    )
    fm, _ = read_frontmatter(paper)
    assert fm is not None
    assert fm["openalex_id"] == "W4385545131"
    assert fm["source"] == "manual"


def _openalex_payload() -> dict[str, object]:
    return {
        "id": "https://openalex.org/W4385545131",
        "display_name": "Self-RAG",
        "authorships": [
            {"author": {"display_name": "Akari Asai"}},
            {"author": {"display_name": "Zeqiu Wu"}},
        ],
        "publication_year": 2023,
        "primary_location": {"source": {"display_name": "arXiv (Cornell University)"}},
        "doi": "https://doi.org/10.48550/arxiv.2310.11511",
        "ids": {
            "doi": "https://doi.org/10.48550/arxiv.2310.11511",
            "openalex": "https://openalex.org/W4385545131",
        },
    }
