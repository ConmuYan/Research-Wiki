"""OpenAlex Works metadata fetcher."""

from __future__ import annotations

import os
from typing import Any

import httpx

from lgrlw.fetchers.base import BaseFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.schemas import DOI_PATTERN, OPENALEX_ID_PATTERN, PaperKind, PaperMetadata

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexFetcher(BaseFetcher):
    """Fetch canonical paper metadata from the OpenAlex Works endpoint."""

    source = PaperKind.openalex

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        mailto: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._mailto = mailto if mailto is not None else os.environ.get("OPENALEX_EMAIL")

    def fetch(self, identifier: str) -> PaperMetadata:
        openalex_id = _normalize_openalex_id(identifier)
        params = {"mailto": self._mailto} if self._mailto else None
        try:
            response = self._client.get(
                f"{OPENALEX_WORKS_URL}/{openalex_id}",
                params=params,
            )
        except httpx.HTTPError as exc:
            raise FetcherError(f"OpenAlex request failed for id {openalex_id!r}: {exc}") from exc

        if response.status_code == 404:
            raise FetcherNotFoundError(f"OpenAlex has no work for id {openalex_id!r}")
        if response.status_code >= 400:
            raise FetcherError(
                f"OpenAlex returned HTTP {response.status_code} for id {openalex_id!r}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FetcherError(
                f"OpenAlex returned non-JSON response for id {openalex_id!r}"
            ) from exc

        if not isinstance(payload, dict):
            raise FetcherError(f"OpenAlex response for id {openalex_id!r} is not a JSON object")

        return _metadata_from_payload(openalex_id, payload)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


_DEFAULT_OPENALEX_PREFIXES = (
    "https://openalex.org/",
    "http://openalex.org/",
    "https://www.openalex.org/",
    "http://www.openalex.org/",
    "https://api.openalex.org/works/",
    "http://api.openalex.org/works/",
)


def _normalize_openalex_id(identifier: str) -> str:
    value = identifier.strip()
    lower = value.lower()
    for prefix in _DEFAULT_OPENALEX_PREFIXES:
        if lower.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.lower().startswith("openalex:"):
        value = value[len("openalex:") :]
    value = value.strip()
    if value[:1].lower() == "w":
        value = "W" + value[1:]
    if not OPENALEX_ID_PATTERN.fullmatch(value):
        raise FetcherError(f"invalid OpenAlex id {identifier!r}")
    return value


def _metadata_from_payload(openalex_id: str, payload: dict[str, Any]) -> PaperMetadata:
    title = _string(payload.get("display_name") or payload.get("title"))
    authors = _authors(payload.get("authorships"))
    year_value = payload.get("publication_year")
    year = year_value if isinstance(year_value, int) else None
    if title is None or not authors or year is None:
        raise FetcherError(f"OpenAlex response for id {openalex_id!r} lacks required metadata")

    doi = _doi(payload)
    venue = _venue(payload)
    url = (
        _string(payload.get("doi"))
        or (f"https://doi.org/{doi}" if doi else None)
        or _string(payload.get("id"))
    )

    return PaperMetadata(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        openalex_id=openalex_id,
        url=url,
        source=PaperKind.openalex,
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
        name: str | None = None
        author = item.get("author")
        if isinstance(author, dict):
            name = _string(author.get("display_name"))
        if name is None:
            name = _string(item.get("raw_author_name"))
        if name:
            authors.append(name)
    return authors


def _venue(payload: dict[str, Any]) -> str | None:
    primary_location = payload.get("primary_location")
    if isinstance(primary_location, dict):
        source = primary_location.get("source")
        if isinstance(source, dict):
            name = _string(source.get("display_name"))
            if name:
                return name
    host_venue = payload.get("host_venue")
    if isinstance(host_venue, dict):
        return _string(host_venue.get("display_name"))
    return None


def _doi(payload: dict[str, Any]) -> str | None:
    candidate = _string(payload.get("doi"))
    if candidate is None:
        ids = payload.get("ids")
        if isinstance(ids, dict):
            candidate = _string(ids.get("doi"))
    if candidate is None:
        return None
    candidate = candidate.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix) :]
            break
    return candidate if DOI_PATTERN.fullmatch(candidate) else None


__all__ = ["OPENALEX_WORKS_URL", "OpenAlexFetcher"]
