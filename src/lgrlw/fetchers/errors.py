"""Errors raised by networked literature metadata fetchers."""

from __future__ import annotations


class FetcherError(RuntimeError):
    """Base class for fetcher failures."""


class FetcherNotFoundError(FetcherError):
    """Raised when a remote source has no paper for an identifier."""


__all__ = ["FetcherError", "FetcherNotFoundError"]
