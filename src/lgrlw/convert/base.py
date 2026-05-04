"""Converter plugin interface for ``lgrlw convert-pdf``.

A converter turns a PDF into Markdown and (optionally) a set of asset
files under an output directory. Converters are registered by name and
looked up via :func:`get_converter`.

The interface is intentionally tiny: one method, ``convert``, returning
a :class:`ConversionResult`. Backends decide whether to delegate to a
local binary, a Python library, or a subprocess — callers never need to
know.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


class ConverterError(RuntimeError):
    """Raised by a converter when the conversion cannot complete."""


class ConverterUnavailableError(ConverterError):
    """Raised when a requested backend is registered but not runnable.

    Typical reason: the optional dependency that backs the converter
    is not installed in the current environment.
    """


@dataclass(frozen=True)
class ConversionResult:
    """Summary of a single ``convert_pdf`` call.

    ``output_dir`` is the directory created under
    ``literature-kb/01_Raw/mineru_md/<paper_id>/``. ``markdown_path``
    is the canonical ``<paper_id>.md`` inside that directory.
    ``extra_files`` lists any additional artifacts written (e.g.
    extracted images or JSON layout dumps).
    """

    paper_id: str
    source_pdf: Path
    output_dir: Path
    markdown_path: Path
    backend: str
    extra_files: list[Path] = field(default_factory=list)


@runtime_checkable
class PdfConverter(Protocol):
    """Pluggable PDF-to-Markdown converter.

    Implementations must be idempotent w.r.t. a given ``(source_pdf,
    output_dir)`` pair: repeated calls with the same arguments produce
    byte-identical Markdown. Non-determinism in backends (timestamps,
    randomised ids) must be normalised out.
    """

    name: str

    def convert(
        self,
        source_pdf: Path,
        output_dir: Path,
        *,
        paper_id: str,
    ) -> ConversionResult:
        """Convert ``source_pdf`` into ``output_dir``.

        ``paper_id`` is passed separately so the markdown filename is
        stable even if callers choose to stage conversions in a temp
        directory before moving them into place.
        """


class ConverterRegistry:
    """In-process registry of converter factories keyed by backend name."""

    def __init__(self) -> None:
        self._factories: dict[str, type[PdfConverter]] = {}

    def register(self, name: str, factory: type[PdfConverter]) -> None:
        self._factories[name] = factory

    def get(self, name: str) -> PdfConverter:
        if name not in self._factories:
            raise ConverterError(
                f"unknown converter backend {name!r}; available: {sorted(self._factories)}"
            )
        factory = self._factories[name]
        return factory()

    def names(self) -> list[str]:
        return sorted(self._factories)


_REGISTRY = ConverterRegistry()


def register_backend(name: str, factory: type[PdfConverter]) -> None:
    """Register a converter factory under ``name``.

    Convention: backends name themselves the same as their optional
    extra. ``stub`` is always available; ``mineru`` is registered only
    when ``pip install "lgrlw[mineru]"`` has been run.
    """
    _REGISTRY.register(name, factory)


def get_converter(name: str) -> PdfConverter:
    """Return a fresh converter instance for ``name``."""
    return _REGISTRY.get(name)


def list_backends() -> list[str]:
    """Return all currently registered backend names."""
    return _REGISTRY.names()


__all__ = [
    "ConversionResult",
    "ConverterError",
    "ConverterRegistry",
    "ConverterUnavailableError",
    "PdfConverter",
    "get_converter",
    "list_backends",
    "register_backend",
]
