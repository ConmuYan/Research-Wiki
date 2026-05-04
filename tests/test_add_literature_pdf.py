"""Tests for ``lgrlw add-literature --pdf`` local PDF attachment (v0.3.1)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n") -> Path:
    path.write_bytes(content)
    return path


def _invoke(runner: CliRunner, project: Path, *extra: str, pdf_path: Path | None = None) -> object:
    args = [
        "add-literature",
        "--manual",
        "--title",
        "Self-RAG: Self-Reflective RAG",
        "--authors",
        "Akari Asai",
        "--year",
        "2023",
        "--id",
        "asai-2023-self-rag",
        "--root",
        str(project),
    ]
    if pdf_path is not None:
        args.extend(["--pdf", str(pdf_path)])
    args.extend(extra)
    return runner.invoke(app, args)


def test_add_literature_pdf_archives_local_file(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf = _make_pdf(tmp_path / "self-rag.pdf")

    r = _invoke(runner, project, pdf_path=pdf)

    assert r.exit_code == 0, r.output

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert archive.is_file()
    assert archive.read_bytes() == pdf.read_bytes()
    assert "pdf" in r.output.lower()

    # Source PDF is never touched.
    assert pdf.is_file()
    assert pdf.read_bytes().startswith(b"%PDF-")


def test_add_literature_pdf_missing_source_errors(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist.pdf"

    r = _invoke(runner, project, pdf_path=missing)

    assert r.exit_code != 0
    assert "does not exist" in r.output.lower()

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert not archive.exists()


def test_add_literature_pdf_rejects_non_pdf_extension(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    not_pdf = tmp_path / "self-rag.txt"
    not_pdf.write_text("not a pdf", encoding="utf-8")

    r = _invoke(runner, project, pdf_path=not_pdf)

    assert r.exit_code != 0
    assert ".pdf" in r.output.lower()


def test_add_literature_pdf_refuses_overwrite_without_force_pdf(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    first = _make_pdf(tmp_path / "v1.pdf", content=b"%PDF-1.4\nfirst\n")
    second = _make_pdf(tmp_path / "v2.pdf", content=b"%PDF-1.4\nsecond\n")

    r1 = _invoke(runner, project, pdf_path=first)
    assert r1.exit_code == 0, r1.output

    r2 = _invoke(runner, project, "--force", pdf_path=second)
    assert r2.exit_code != 0
    assert "--force-pdf" in r2.output

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert archive.read_bytes() == first.read_bytes()


def test_add_literature_pdf_force_pdf_replaces_archive(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    first = _make_pdf(tmp_path / "v1.pdf", content=b"%PDF-1.4\nfirst\n")
    second = _make_pdf(tmp_path / "v2.pdf", content=b"%PDF-1.4\nsecond\n")

    r1 = _invoke(runner, project, pdf_path=first)
    assert r1.exit_code == 0, r1.output

    r2 = _invoke(runner, project, "--force", "--force-pdf", pdf_path=second)
    assert r2.exit_code == 0, r2.output

    archive = project / "literature-kb" / "01_Raw" / "pdf" / "asai-2023-self-rag.pdf"
    assert archive.read_bytes() == second.read_bytes()


def test_add_literature_without_pdf_still_works(project: Path, runner: CliRunner) -> None:
    r = _invoke(runner, project)
    assert r.exit_code == 0, r.output

    pdf_dir = project / "literature-kb" / "01_Raw" / "pdf"
    # Directory may or may not be created by unrelated code, but it must not
    # contain an archived PDF for this paper.
    archived = pdf_dir / "asai-2023-self-rag.pdf"
    assert not archived.exists()
