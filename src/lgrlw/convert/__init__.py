"""PDF-to-Markdown conversion (v0.5+).

This sub-package exposes a **pluggable converter** abstraction so the
Research-Wiki CLI can ship a zero-dependency default (`stub`) while
allowing heavyweight optional backends such as MinerU
(`pip install "lgrlw[mineru]"`) to register themselves.

Every converter writes its output under
``literature-kb/01_Raw/mineru_md/<paper_id>/`` — one directory per paper
so backends that emit images or other assets can do so cleanly.
"""

from __future__ import annotations

from lgrlw.convert.base import (
    ConversionResult,
    ConverterError,
    ConverterRegistry,
    ConverterUnavailableError,
    PdfConverter,
    get_converter,
    list_backends,
    register_backend,
)
from lgrlw.convert.mineru import MinerUConverter  # noqa: F401 — registers `mineru`
from lgrlw.convert.stub import StubConverter

__all__ = [
    "ConversionResult",
    "ConverterError",
    "ConverterRegistry",
    "ConverterUnavailableError",
    "PdfConverter",
    "StubConverter",
    "get_converter",
    "list_backends",
    "register_backend",
]
