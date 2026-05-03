"""arXiv metadata fetcher."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from lgrlw.fetchers.base import BaseFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.schemas import ARXIV_PATTERN, DOI_PATTERN, PaperKind, PaperMetadata

ARXIV_QUERY_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivFetcher(BaseFetcher):
    """Fetch canonical paper metadata from the arXiv Atom API."""

    source = PaperKind.arxiv

    def __init__(self, client: httpx.Client | None = None, *, timeout: float = 10.0) -> None:
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def fetch(self, identifier: str) -> PaperMetadata:
        arxiv_id = _normalize_arxiv_id(identifier)
        try:
            response = self._client.get(ARXIV_QUERY_URL, params={"id_list": arxiv_id})
        except httpx.HTTPError as exc:
            raise FetcherError(f"arXiv request failed for id {arxiv_id!r}: {exc}") from exc

        if response.status_code >= 400:
            raise FetcherError(f"arXiv returned HTTP {response.status_code} for id {arxiv_id!r}")

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise FetcherError(f"arXiv returned malformed XML for id {arxiv_id!r}") from exc

        entries = root.findall(_atom("entry"))
        if not entries:
            raise FetcherNotFoundError(f"arXiv has no entry for id {arxiv_id!r}")

        return _metadata_from_entry(arxiv_id, entries[0])

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def _normalize_arxiv_id(identifier: str) -> str:
    value = identifier.strip()
    lower = value.lower()
    for prefix in (
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://www.arxiv.org/abs/",
        "http://www.arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/pdf/",
        "https://www.arxiv.org/pdf/",
        "http://www.arxiv.org/pdf/",
    ):
        if lower.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.lower().startswith("arxiv:"):
        value = value[6:]
    value = value.split("?", 1)[0].split("#", 1)[0].strip()
    if value.lower().endswith(".pdf"):
        value = value[:-4]
    if not ARXIV_PATTERN.fullmatch(value):
        raise FetcherError(f"invalid arXiv id {identifier!r}")
    return value


def _metadata_from_entry(arxiv_id: str, entry: ET.Element) -> PaperMetadata:
    title = _clean_text(_text(entry, _atom("title")))
    authors_raw = [
        _clean_text(_text(author, _atom("name"))) for author in entry.findall(_atom("author"))
    ]
    authors = [author for author in authors_raw if author is not None]
    published = _text(entry, _atom("published"))
    year = _year(published)
    if title is None or not authors or year is None:
        raise FetcherError(f"arXiv response for id {arxiv_id!r} lacks required metadata")

    entry_url = _text(entry, _atom("id")) or f"https://arxiv.org/abs/{arxiv_id}"
    doi = _clean_text(_text(entry, _arxiv("doi")))
    journal_ref = _clean_text(_text(entry, _arxiv("journal_ref")))
    primary_category = entry.find(_arxiv("primary_category"))
    primary_category_term = primary_category.get("term") if primary_category is not None else None

    return PaperMetadata(
        title=title,
        authors=authors,
        year=year,
        venue=journal_ref or "arXiv preprint",
        doi=doi if doi and DOI_PATTERN.fullmatch(doi) else None,
        arxiv_id=arxiv_id,
        url=_https_url(entry_url),
        abstract=_clean_text(_text(entry, _atom("summary"))),
        source=PaperKind.arxiv,
        raw={
            "entry_id": entry_url,
            "published": published,
            "updated": _text(entry, _atom("updated")),
            "primary_category": primary_category_term,
        },
    )


def _atom(tag: str) -> str:
    return f"{{{ATOM_NS}}}{tag}"


def _arxiv(tag: str) -> str:
    return f"{{{ARXIV_NS}}}{tag}"


def _text(element: ET.Element, path: str) -> str | None:
    child = element.find(path)
    if child is None or child.text is None:
        return None
    return child.text


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _year(value: str | None) -> int | None:
    if value is None or len(value) < 4 or not value[:4].isdigit():
        return None
    return int(value[:4])


def _https_url(value: str) -> str:
    if value.startswith("http://"):
        return "https://" + value[len("http://") :]
    return value


__all__ = ["ARXIV_QUERY_URL", "ArxivFetcher"]
