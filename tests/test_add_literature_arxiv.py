"""Tests for ``lgrlw add-literature --arxiv``."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fetchers.arxiv import ARXIV_QUERY_URL
from lgrlw.fs import read_frontmatter


def test_add_arxiv_fetches_metadata_and_writes_entry(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(ARXIV_QUERY_URL, params={"id_list": "2310.11511"}).mock(
        return_value=httpx.Response(200, text=_arxiv_feed())
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--arxiv",
            "https://arxiv.org/abs/2310.11511",
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
    assert fm["venue"] == "arXiv preprint"
    assert fm["arxiv_id"] == "2310.11511"
    assert fm["source"] == "arxiv"
    assert fm["tags"] == ["rag", "llm"]
    assert "Self-RAG" in body

    metadata = json.loads(
        (project / "literature-kb" / "01_Raw" / "metadata" / f"{paper_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["source"] == "arxiv"
    assert metadata["arxiv_id"] == "2310.11511"

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert f"add-literature arxiv add id={paper_id}" in log


def test_add_arxiv_rejects_manual_metadata_overrides(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--arxiv",
            "2310.11511",
            "--title",
            "Hand Override",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "--manual" in result.output


def test_add_arxiv_fetch_failure_writes_nothing(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(ARXIV_QUERY_URL, params={"id_list": "2310.00000"}).mock(
        return_value=httpx.Response(200, text=_arxiv_empty_feed())
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--arxiv",
            "2310.00000",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    metadata_dir = project / "literature-kb" / "01_Raw" / "metadata"
    assert [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"] == []
    assert [p for p in metadata_dir.glob("*.json") if p.name != ".gitkeep"] == []


def test_add_doi_and_arxiv_without_manual_are_mutually_exclusive(
    project: Path, runner: CliRunner
) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--doi",
            "10.5555/example",
            "--arxiv",
            "2310.11511",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "exactly one" in result.output


def test_add_manual_with_arxiv_remains_manual(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Manual arXiv Paper",
            "--authors",
            "Alice A",
            "--year",
            "2024",
            "--arxiv",
            "2310.11511",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    paper = project / "literature-kb" / "02_Literature" / "Papers" / "a-2024-manual-arxiv-paper.md"
    fm, _ = read_frontmatter(paper)
    assert fm is not None
    assert fm["arxiv_id"] == "2310.11511"
    assert fm["source"] == "manual"


def _arxiv_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2310.11511</id>
    <updated>2023-10-18T00:00:00Z</updated>
    <published>2023-10-18T00:00:00Z</published>
    <title>Self-RAG</title>
    <summary>Example abstract.</summary>
    <author><name>Akari Asai</name></author>
    <author><name>Zeqiu Wu</name></author>
    <arxiv:primary_category term="cs.CL" />
  </entry>
</feed>
"""


def _arxiv_empty_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" />
"""
