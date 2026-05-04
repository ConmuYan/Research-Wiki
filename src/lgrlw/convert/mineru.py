"""MinerU-backed PDF-to-Markdown converter (optional, v0.5).

MinerU (https://github.com/opendatalab/MinerU) is a third-party PDF
extraction toolkit. It is **not** a runtime dependency of ``lgrlw``:
users who want MinerU output install it through the ``mineru`` extra
(``pip install "lgrlw[mineru]"``) or bring their own ``magic-pdf``
installation.

This module registers the ``mineru`` backend eagerly (so callers can
discover it via :func:`lgrlw.convert.list_backends`) but defers the
actual import of :mod:`magic_pdf` to ``convert`` time. If MinerU is not
importable at that point the converter raises
:class:`~lgrlw.convert.base.ConverterUnavailableError` with a clear hint.
"""

from __future__ import annotations

from pathlib import Path

from lgrlw.convert.base import (
    ConversionResult,
    ConverterError,
    ConverterUnavailableError,
    register_backend,
)

_INSTALL_HINT = (
    'install the optional extra with: pip install "lgrlw[mineru]" '
    "(or install MinerU\u2019s magic-pdf yourself)"
)


class MinerUConverter:
    """Delegate conversion to MinerU\u2019s ``magic-pdf`` Python API.

    The converter is intentionally lazy: importing the class does not
    import MinerU. Only :meth:`convert` touches the optional dependency,
    so ``lgrlw --help`` stays fast and tests that only exercise the stub
    backend do not pay the MinerU import cost.
    """

    name = "mineru"

    def convert(
        self,
        source_pdf: Path,
        output_dir: Path,
        *,
        paper_id: str,
    ) -> ConversionResult:
        try:
            # Keep the import inside ``convert`` so the plugin is only
            # loaded when actually invoked. See the module docstring for
            # why this is required.
            import magic_pdf  # noqa: F401
        except ImportError as exc:
            raise ConverterUnavailableError(
                f"MinerU is not installed in this environment; {_INSTALL_HINT}"
            ) from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{paper_id}.md"

        # The MinerU public API stabilises around a one-shot
        # ``convert_to_markdown`` helper. We do not hard-bind against a
        # particular release here; instead we fail loudly if the API we
        # expect is not present. Users with bespoke MinerU wrappers can
        # subclass this converter and override the call.
        try:
            from magic_pdf.pipe.UNIPipe import UNIPipe
        except ImportError as exc:  # pragma: no cover - requires a real mineru install
            raise ConverterUnavailableError(
                "MinerU is installed but does not expose the expected API "
                "(magic_pdf.pipe.UNIPipe). Please upgrade MinerU or pin "
                "lgrlw[mineru] to a compatible version."
            ) from exc

        try:  # pragma: no cover - requires a real mineru install
            pipe = UNIPipe(source_pdf.read_bytes(), {"_pdf_type": "", "model_list": []})
            pipe.pipe_classify()
            pipe.pipe_parse()
            markdown = pipe.pipe_mk_markdown(str(output_dir), drop_mode="none")
            markdown_path.write_text(
                markdown if isinstance(markdown, str) else "\n".join(markdown),
                encoding="utf-8",
                newline="\n",
            )
        except Exception as exc:  # pragma: no cover - requires a real mineru install
            raise ConverterError(f"MinerU conversion failed: {exc}") from exc

        extras = [p for p in output_dir.iterdir() if p.is_file() and p != markdown_path]
        return ConversionResult(
            paper_id=paper_id,
            source_pdf=source_pdf,
            output_dir=output_dir,
            markdown_path=markdown_path,
            backend=self.name,
            extra_files=sorted(extras),
        )


register_backend(MinerUConverter.name, MinerUConverter)


__all__ = ["MinerUConverter"]
