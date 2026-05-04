"""Tests for ``lgrlw.ingest.pdf_download`` and the ``--allow-network-pdf`` flag (v0.5.x).

All HTTP traffic is mocked via ``respx`` — no real network calls are made.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter
from lgrlw.ingest.pdf_download import (
    PdfDownloadDisallowedError,
    PdfDownloadError,
    PdfDownloadForbiddenHostError,
    fetch_arxiv_pdf,
    fetch_whitelisted_pdf,
)

MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"


# ---------------------------------------------------------------------------
# fetch_arxiv_pdf
# ---------------------------------------------------------------------------


def test_fetch_arxiv_pdf_requires_opt_in() -> None:
    with pytest.raises(PdfDownloadDisallowedError):
        fetch_arxiv_pdf("2310.11511", allow_network_pdf=False)


@respx.mock
def test_fetch_arxiv_pdf_downloads_from_arxiv_only() -> None:
    route = respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=MINIMAL_PDF,
        headers={"Content-Type": "application/pdf"},
    )
    result = fetch_arxiv_pdf("2310.11511", allow_network_pdf=True)
    assert route.called
    assert result.content == MINIMAL_PDF
    assert result.content_type == "application/pdf"
    assert result.url.startswith("https://arxiv.org/")


@respx.mock
def test_fetch_arxiv_pdf_strips_version_and_url_prefix() -> None:
    route = respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=MINIMAL_PDF, headers={"Content-Type": "application/pdf"}
    )
    fetch_arxiv_pdf("arxiv:2310.11511v3", allow_network_pdf=True)
    fetch_arxiv_pdf("https://arxiv.org/abs/2310.11511", allow_network_pdf=True)
    assert route.call_count == 2


def test_fetch_arxiv_pdf_rejects_non_modern_id() -> None:
    with pytest.raises(PdfDownloadError, match="modern arXiv id"):
        fetch_arxiv_pdf("hep-th/9901001", allow_network_pdf=True)


@respx.mock
def test_fetch_arxiv_pdf_rejects_non_pdf_response() -> None:
    respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=b"<html>rate limited</html>",
        headers={"Content-Type": "text/html"},
    )
    with pytest.raises(PdfDownloadError, match="content-type"):
        fetch_arxiv_pdf("2310.11511", allow_network_pdf=True)


@respx.mock
def test_fetch_arxiv_pdf_rejects_non_pdf_bytes_without_content_type() -> None:
    respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=b"junk",  # no magic bytes
        headers={},
    )
    with pytest.raises(PdfDownloadError, match="%PDF-"):
        fetch_arxiv_pdf("2310.11511", allow_network_pdf=True)


@respx.mock
def test_fetch_arxiv_pdf_wraps_network_error() -> None:
    respx.get("https://arxiv.org/pdf/2310.11511.pdf").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(PdfDownloadError, match="network error"):
        fetch_arxiv_pdf("2310.11511", allow_network_pdf=True)


# ---------------------------------------------------------------------------
# fetch_whitelisted_pdf
# ---------------------------------------------------------------------------


def test_fetch_whitelisted_pdf_rejects_non_whitelisted_hosts() -> None:
    with pytest.raises(PdfDownloadForbiddenHostError):
        fetch_whitelisted_pdf("https://evil.example.com/paper.pdf", allow_network_pdf=True)


@respx.mock
def test_fetch_whitelisted_pdf_accepts_arxiv() -> None:
    respx.get("https://export.arxiv.org/pdf/abcd.pdf").respond(
        content=MINIMAL_PDF, headers={"Content-Type": "application/pdf"}
    )
    result = fetch_whitelisted_pdf("https://export.arxiv.org/pdf/abcd.pdf", allow_network_pdf=True)
    assert result.content == MINIMAL_PDF


# ---------------------------------------------------------------------------
# CLI: add-literature --allow-network-pdf
# ---------------------------------------------------------------------------


@respx.mock
def test_cli_add_literature_allow_network_pdf(project, runner: CliRunner) -> None:  # type: ignore[no-untyped-def]
    route = respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=MINIMAL_PDF, headers={"Content-Type": "application/pdf"}
    )
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Self-RAG",
            "--authors",
            "Akari Asai",
            "--year",
            "2023",
            "--arxiv",
            "2310.11511",
            "--id",
            "asai-2023-self-rag",
            "--allow-network-pdf",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert route.called

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert archive.read_bytes() == MINIMAL_PDF


@respx.mock
def test_cli_add_literature_without_flag_does_not_download(
    project,  # type: ignore[no-untyped-def]
    runner: CliRunner,
) -> None:
    route = respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=MINIMAL_PDF, headers={"Content-Type": "application/pdf"}
    )
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Self-RAG",
            "--authors",
            "Akari Asai",
            "--year",
            "2023",
            "--arxiv",
            "2310.11511",
            "--id",
            "asai-2023-self-rag",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert not route.called

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert not archive.exists()


@respx.mock
def test_cli_add_literature_local_pdf_takes_priority(
    project,  # type: ignore[no-untyped-def]
    runner: CliRunner,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    network_pdf = MINIMAL_PDF + b"NETWORK\n"
    local_pdf_bytes = MINIMAL_PDF + b"LOCAL\n"

    route = respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=network_pdf, headers={"Content-Type": "application/pdf"}
    )

    local_pdf = tmp_path / "local.pdf"
    local_pdf.write_bytes(local_pdf_bytes)

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Self-RAG",
            "--authors",
            "Akari Asai",
            "--year",
            "2023",
            "--arxiv",
            "2310.11511",
            "--id",
            "asai-2023-self-rag",
            "--pdf",
            str(local_pdf),
            "--allow-network-pdf",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert not route.called

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert archive.read_bytes() == local_pdf_bytes


# ---------------------------------------------------------------------------
# CLI: import-bib --allow-network-pdf
# ---------------------------------------------------------------------------


@respx.mock
def test_cli_import_bib_allow_network_pdf_populates_manifest(
    project,  # type: ignore[no-untyped-def]
    runner: CliRunner,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    bib = tmp_path / "refs.bib"
    bib.write_text(
        "@article{asai2023selfrag,\n"
        "  author = {Akari Asai},\n"
        "  title  = {Self-RAG},\n"
        "  year   = {2023},\n"
        "  eprint = {2310.11511},\n"
        "  archiveprefix = {arXiv},\n"
        "}\n",
        encoding="utf-8",
    )
    respx.get("https://arxiv.org/pdf/2310.11511.pdf").respond(
        content=MINIMAL_PDF, headers={"Content-Type": "application/pdf"}
    )

    result = runner.invoke(
        app,
        [
            "import-bib",
            str(bib),
            "--allow-network-pdf",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output

    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    papers = [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"]
    assert len(papers) == 1
    fm, _ = read_frontmatter(papers[0])
    assert fm is not None
    paper_id = fm["id"]

    archive = project / "literature-kb" / "01_Raw" / "pdf" / f"{paper_id}.pdf"
    assert archive.read_bytes() == MINIMAL_PDF
