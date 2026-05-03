"""Semantic Scholar Graph API metadata fetcher.

The Semantic Scholar (S2) Graph API accepts a wide range of identifier
forms: the canonical 40-char SHA-1 ``paperId``, prefixed aliases like
``DOI:10.xxxx/yyyy`` / ``ARXIV:2310.11511`` / ``CorpusId:215416146``,
and even full Semantic Scholar paper URLs. We pass the user's input to
the API with minimal normalisation (just stripping the known
``https://www.semanticscholar.org/paper/`` URL prefix) and let the API
resolve it. The response's ``paperId`` field is the canonical
lowercase-hex id that we store in frontmatter.

The fetcher honours the ``S2_API_KEY`` environment variable: when set,
the ``x-api-key`` header is attached for the higher polite-pool rate
limit. The key is never printed.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from lgrlw.fetchers.base import BaseFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.schemas import (
    ARXIV_PATTERN,
    DOI_PATTERN,
    SEMANTIC_SCHOLAR_ID_PATTERN,
    PaperKind,
    PaperMetadata,
)

SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"
SEMANTIC_SCHOLAR_FIELDS = "paperId,title,authors,year,venue,externalIds,url"


class SemanticScholarFetcher(BaseFetcher):
    """Fetch canonical paper metadata from the Semantic Scholar Graph API."""

    source = PaperKind.semantic_scholar

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._api_key = api_key if api_key is not None else os.environ.get("S2_API_KEY")

    def fetch(self, identifier: str) -> PaperMetadata:
        lookup = _normalize_identifier(identifier)
        headers = {"x-api-key": self._api_key} if self._api_key else None
        params = {"fields": SEMANTIC_SCHOLAR_FIELDS}
        url = f"{SEMANTIC_SCHOLAR_BASE_URL}/{lookup}"
        try:
            response = self._client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise FetcherError(
                f"Semantic Scholar request failed for id {identifier!r}: {exc}"
            ) from exc

        if response.status_code == 404:
            raise FetcherNotFoundError(f"Semantic Scholar has no paper for id {identifier!r}")
        if response.status_code == 429:
            raise FetcherError(
                "Semantic Scholar rate-limited this request (HTTP 429); "
                "set S2_API_KEY to use the authenticated polite-pool quota"
            )
        if response.status_code >= 400:
            raise FetcherError(
                f"Semantic Scholar returned HTTP {response.status_code} for id {identifier!r}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FetcherError(
                f"Semantic Scholar returned non-JSON response for id {identifier!r}"
            ) from exc

        if not isinstance(payload, dict):
            raise FetcherError(
                f"Semantic Scholar response for id {identifier!r} is not a JSON object"
            )

        return _metadata_from_payload(identifier, payload)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


_SEMANTIC_SCHOLAR_URL_PREFIXES = (
    "https://www.semanticscholar.org/paper/",
    "http://www.semanticscholar.org/paper/",
    "https://semanticscholar.org/paper/",
    "http://semanticscholar.org/paper/",
)


def _normalize_identifier(identifier: str) -> str:
    """Return the value that should be appended to the S2 endpoint URL.

    Accepts:

    * A canonical 40-hex Semantic Scholar paper id.
    * A Semantic Scholar paper URL (everything up to the last path
      segment is stripped; any query string or fragment is discarded).
    * Prefixed forms already recognised by the S2 API: ``DOI:...``,
      ``ARXIV:...``, ``CorpusId:...``, ``MAG:...``, ``ACL:...``,
      ``PMID:...``, ``PMCID:...``, ``URL:...``.
    * A bare DOI or arXiv id, auto-wrapped with the ``DOI:`` / ``ARXIV:``
      prefix so the API can resolve it.
    """
    value = identifier.strip()
    if not value:
        raise FetcherError("empty Semantic Scholar identifier")

    lower = value.lower()
    for prefix in _SEMANTIC_SCHOLAR_URL_PREFIXES:
        if lower.startswith(prefix):
            tail = value[len(prefix) :]
            # Semantic Scholar URLs may include a human-readable slug
            # before the 40-hex id, e.g. ``Self-Rag/<paperId>``. The last
            # '/' segment (stripped of any ?query / #fragment) is the id.
            tail = tail.split("?", 1)[0].split("#", 1)[0]
            last = tail.rstrip("/").split("/")[-1]
            return last

    if _looks_like_prefixed(value):
        return value

    if SEMANTIC_SCHOLAR_ID_PATTERN.fullmatch(value):
        return value

    if DOI_PATTERN.fullmatch(value):
        return f"DOI:{value}"

    if ARXIV_PATTERN.fullmatch(value):
        return f"ARXIV:{value}"

    raise FetcherError(
        f"unrecognised Semantic Scholar identifier {identifier!r}; expected a 40-char "
        "paper id, DOI, arXiv id, or S2 URL / prefixed form"
    )


_SUPPORTED_PREFIXES = (
    "doi:",
    "arxiv:",
    "corpusid:",
    "mag:",
    "acl:",
    "pmid:",
    "pmcid:",
    "url:",
)


def _looks_like_prefixed(value: str) -> bool:
    lower = value.lower()
    return any(lower.startswith(prefix) for prefix in _SUPPORTED_PREFIXES)


def _metadata_from_payload(identifier: str, payload: dict[str, Any]) -> PaperMetadata:
    paper_id = _string(payload.get("paperId"))
    if paper_id is None:
        raise FetcherError(f"Semantic Scholar response for {identifier!r} lacks paperId")
    paper_id = paper_id.lower()
    if not SEMANTIC_SCHOLAR_ID_PATTERN.fullmatch(paper_id):
        raise FetcherError(
            f"Semantic Scholar returned unexpected paperId {paper_id!r} for {identifier!r}"
        )

    title = _string(payload.get("title"))
    authors = _authors(payload.get("authors"))
    year_value = payload.get("year")
    year = year_value if isinstance(year_value, int) else None
    if title is None or not authors:
        raise FetcherError(f"Semantic Scholar response for {identifier!r} lacks required metadata")

    external = payload.get("externalIds")
    doi = _external_id(external, "DOI")
    if doi is not None:
        doi = doi.lower()
        if not DOI_PATTERN.fullmatch(doi):
            doi = None

    arxiv = _external_id(external, "ArXiv")
    if arxiv is not None and not ARXIV_PATTERN.fullmatch(arxiv):
        arxiv = None

    venue = _string(payload.get("venue"))
    url = _string(payload.get("url")) or (f"https://www.semanticscholar.org/paper/{paper_id}")

    return PaperMetadata(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        arxiv_id=arxiv,
        semantic_scholar_id=paper_id,
        url=url,
        source=PaperKind.semantic_scholar,
        raw=payload,
    )


def _string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _string(item.get("name"))
        if name:
            authors.append(name)
    return authors


def _external_id(value: object, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    return _string(value.get(key))


__all__ = [
    "SEMANTIC_SCHOLAR_BASE_URL",
    "SEMANTIC_SCHOLAR_FIELDS",
    "SemanticScholarFetcher",
]
