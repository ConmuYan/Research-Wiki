"""Base class for networked literature metadata fetchers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lgrlw.schemas import PaperKind, PaperMetadata


class BaseFetcher(ABC):
    """Abstract interface implemented by every networked fetcher."""

    source: PaperKind

    @abstractmethod
    def fetch(self, identifier: str) -> PaperMetadata:
        """Return canonical metadata for ``identifier``."""


__all__ = ["BaseFetcher"]
