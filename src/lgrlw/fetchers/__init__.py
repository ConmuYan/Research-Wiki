"""Networked metadata fetchers for v0.2 literature ingestion."""

from __future__ import annotations

from lgrlw.fetchers.arxiv import ArxivFetcher
from lgrlw.fetchers.base import BaseFetcher
from lgrlw.fetchers.crossref import CrossrefFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.fetchers.openalex import OpenAlexFetcher
from lgrlw.fetchers.semanticscholar import SemanticScholarFetcher

__all__ = [
    "ArxivFetcher",
    "BaseFetcher",
    "CrossrefFetcher",
    "FetcherError",
    "FetcherNotFoundError",
    "OpenAlexFetcher",
    "SemanticScholarFetcher",
]
