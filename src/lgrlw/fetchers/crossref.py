"""Crossref DOI metadata fetcher."""

from __future__ import annotations

import os
from typing import Any

import httpx

from lgrlw.fetchers.base import BaseFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.schemas import DOI_PATTERN, PaperKind, PaperMetadata

CROSSREF_WORKS_URL = "https://api.crossref.org/works"


class CrossrefFetcher(BaseFetcher):
    """Fetch canonical paper metadata from Crossref's works endpoint."""

    source = PaperKind.crossref

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        mailto: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._mailto = mailto if mailto is not None else os.environ.get("CROSSREF_MAILTO")

    def fetch(self, identifier: str) -> PaperMetadata:
        doi = _normalize_doi(identifier)
        params = {"mailto": self._mailto} if self._mailto else None
        try:
            response = self._client.get(f"{CROSSREF_WORKS_URL}/{doi}", params=params)
        except httpx.HTTPError as exc:
            raise FetcherError(f"Crossref request failed for DOI {doi!r}: {exc}") from exc

        if response.status_code == 404:
            raise FetcherNotFoundError(f"Crossref has no work for DOI {doi!r}")
        if response.status_code >= 400:
            raise FetcherError(f"Crossref returned HTTP {response.status_code} for DOI {doi!r}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise FetcherError(f"Crossref returned non-JSON response for DOI {doi!r}") from exc

        message = payload.get("message")
        if not isinstance(message, dict):
            raise FetcherError(f"Crossref response for DOI {doi!r} is missing message")

        return _metadata_from_message(doi, message)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


_DEFAULT_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
)


def _normalize_doi(identifier: str) -> str:
    value = identifier.strip()
    for prefix in _DEFAULT_DOI_PREFIXES:
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.lower().startswith("doi:"):
        value = value[4:]
    value = value.strip().lower()
    if not DOI_PATTERN.fullmatch(value):
        raise FetcherError(f"invalid DOI {identifier!r}")
    return value


def _metadata_from_message(doi: str, message: dict[str, Any]) -> PaperMetadata:
    title = _first_string(message.get("title"))
    authors = _authors(message.get("author"))
    year = _year(message)
    if title is None or not authors or year is None:
        raise FetcherError(f"Crossref response for DOI {doi!r} lacks required metadata")

    venue = _first_string(message.get("container-title")) or _first_string(
        message.get("short-container-title")
    )
    url = _string(message.get("URL")) or f"https://doi.org/{doi}"

    return PaperMetadata(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        abstract=_string(message.get("abstract")),
        source=PaperKind.crossref,
        raw=message,
    )


def _first_string(value: object) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors = []
    for item in value:
        if not isinstance(item, dict):
            continue
        given = _string(item.get("given")) or ""
        family = _string(item.get("family")) or ""
        name = " ".join(part for part in (given, family) if part).strip()
        if not name:
            name = _string(item.get("name")) or ""
        if name:
            authors.append(name)
    return authors


def _year(message: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        value = message.get(key)
        if not isinstance(value, dict):
            continue
        date_parts = value.get("date-parts")
        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
            and isinstance(date_parts[0][0], int)
        ):
            return date_parts[0][0]
    return None


__all__ = ["CROSSREF_WORKS_URL", "CrossrefFetcher"]
