"""Zero-dependency placeholder converter.

The ``stub`` backend writes a deterministic Markdown placeholder that
records the archived PDF path and flags the conversion as pending. It
exists so ``lgrlw convert-pdf`` works out-of-the-box without MinerU or
any heavyweight dependency, and so tests can exercise the full
pipeline in CI.

The stub does **not** attempt to read the PDF. A real backend such as
:mod:`lgrlw.convert.mineru` parses the document and replaces the
placeholder on a subsequent ``--force`` call.
"""

from __future__ import annotations

from pathlib import Path

from lgrlw.convert.base import ConversionResult, register_backend

STUB_PLACEHOLDER_HEADER = "<!-- lgrlw: pdf conversion pending -->"


class StubConverter:
    """A converter that writes a fixed placeholder regardless of input."""

    name = "stub"

    def convert(
        self,
        source_pdf: Path,
        output_dir: Path,
        *,
        paper_id: str,
    ) -> ConversionResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{paper_id}.md"
        body = (
            f"{STUB_PLACEHOLDER_HEADER}\n"
            f"# {paper_id}\n\n"
            f"Source PDF: `{source_pdf.name}`\n\n"
            "## Status\n\n"
            "This is a stub placeholder produced by `lgrlw convert-pdf --backend stub`.\n"
            'Re-run with `--backend mineru` (after `pip install "lgrlw[mineru]"`) to\n'
            "produce the full Markdown rendering of the PDF.\n"
        )
        markdown_path.write_text(body, encoding="utf-8", newline="\n")
        return ConversionResult(
            paper_id=paper_id,
            source_pdf=source_pdf,
            output_dir=output_dir,
            markdown_path=markdown_path,
            backend=self.name,
            extra_files=[],
        )


register_backend(StubConverter.name, StubConverter)


__all__ = ["STUB_PLACEHOLDER_HEADER", "StubConverter"]
