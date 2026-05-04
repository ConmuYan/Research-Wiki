"""Whitelisted, opt-in PDF downloading (v0.5.x).

The rest of `lgrlw` is deliberately offline. This module is the **only**
place where lgrlw fetches PDF bytes over the network, and even here:

* every caller must explicitly opt in via ``allow_network_pdf=True``;
* only a fixed whitelist of hostnames is permitted (``arxiv.org`` only
  in v0.5.x; more Open-Access hosts arrive in later releases behind the
  same flag);
* no HTML is followed, no redirects outside the whitelist are allowed;
* every fetch has a deterministic timeout and surfaces a typed
  :class:`PdfDownloadError` on failure.

The actual HTTP call lives in :func:`_fetch` which is the single
``httpx`` entry point and is covered by ``respx``-mocked tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

import httpx

_DEFAULT_TIMEOUT: Final[float] = 30.0

_ARXIV_ID_RE: Final = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")

_ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "arxiv.org",
        "export.arxiv.org",
    }
)


class PdfDownloadError(RuntimeError):
    """Raised when a whitelisted PDF download cannot complete."""


class PdfDownloadDisallowedError(PdfDownloadError):
    """Raised when a network PDF fetch is attempted without the opt-in flag."""


class PdfDownloadForbiddenHostError(PdfDownloadError):
    """Raised when the target URL's host is not on the whitelist."""


@dataclass(frozen=True)
class DownloadResult:
    """Successful PDF download payload returned by the fetchers."""

    url: str
    content: bytes
    content_type: str


def fetch_arxiv_pdf(
    arxiv_id: str,
    *,
    allow_network_pdf: bool,
    timeout: float = _DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> DownloadResult:
    """Fetch the canonical ``arxiv.org/pdf/<id>.pdf`` for ``arxiv_id``.

    ``allow_network_pdf`` must be explicitly set to ``True`` by the
    caller. Without it the function raises
    :class:`PdfDownloadDisallowedError` — the intent is to make every
    network PDF fetch visible in CLI help, MCP tool arguments, and
    review diffs.
    """
    if not allow_network_pdf:
        raise PdfDownloadDisallowedError(
            "network PDF download is disabled; pass --allow-network-pdf "
            "(CLI) or allow_network_pdf=true (MCP) to opt in"
        )

    normalised = _normalise_arxiv_id(arxiv_id)
    url = f"https://arxiv.org/pdf/{normalised}.pdf"
    return _fetch(url, timeout=timeout, client=client)


def fetch_whitelisted_pdf(
    url: str,
    *,
    allow_network_pdf: bool,
    timeout: float = _DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> DownloadResult:
    """Fetch ``url`` if its host is on the whitelist.

    Used by future Open-Access flows. Today the whitelist is limited to
    ``arxiv.org`` / ``export.arxiv.org`` so callers must either go
    through :func:`fetch_arxiv_pdf` or bring their own PDF via
    ``attach-pdf``.
    """
    if not allow_network_pdf:
        raise PdfDownloadDisallowedError(
            "network PDF download is disabled; pass --allow-network-pdf "
            "(CLI) or allow_network_pdf=true (MCP) to opt in"
        )

    host = (urlparse(url).hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise PdfDownloadForbiddenHostError(
            f"refusing to download from {host!r}; only {sorted(_ALLOWED_HOSTS)} are allowed"
        )
    return _fetch(url, timeout=timeout, client=client)


def allowed_hosts() -> frozenset[str]:
    """Return the current download whitelist (kept stable for tests)."""
    return _ALLOWED_HOSTS


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _normalise_arxiv_id(raw: str) -> str:
    """Accept a bare id, versioned id, ``arxiv:`` alias, or abs URL.

    Returns the canonical ``YYYY.NNNNN`` form (without version suffix).
    """
    candidate = raw.strip()
    if not candidate:
        raise PdfDownloadError("arxiv id is empty")

    # Accept full URLs (https://arxiv.org/abs/2310.11511) by extracting
    # the trailing id.
    if "/" in candidate:
        candidate = candidate.rstrip("/").rsplit("/", 1)[-1]

    # Drop the informal ``arXiv:`` prefix that shows up in BibTeX and
    # some Semantic Scholar payloads.
    if candidate.lower().startswith("arxiv:"):
        candidate = candidate.split(":", 1)[1]

    match = _ARXIV_ID_RE.match(candidate)
    if not match:
        raise PdfDownloadError(f"not a modern arXiv id: {raw!r}; expected YYYY.NNNNN[vN]")
    return match.group(1)


def _fetch(
    url: str,
    *,
    timeout: float,
    client: httpx.Client | None,
) -> DownloadResult:
    """Centralised HTTP entry point: one place to mock in tests."""
    owned_client = client is None
    http_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        try:
            response = http_client.get(
                url,
                headers={
                    "User-Agent": "lgrlw/0.5 (+https://github.com/ConmuYan/Research-Wiki)",
                    "Accept": "application/pdf",
                },
            )
        except httpx.HTTPError as exc:
            raise PdfDownloadError(f"network error fetching {url}: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise PdfDownloadError(f"unexpected HTTP status {response.status_code} fetching {url}")

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type and content_type != "application/pdf":
            raise PdfDownloadError(
                f"{url} returned content-type {content_type!r}, expected application/pdf"
            )
        # Some mirrors omit content-type entirely; fall back to magic-bytes check.
        content = response.content
        if not content.startswith(b"%PDF-"):
            raise PdfDownloadError(
                f"{url} returned {len(content)} bytes that do not start with %PDF-"
            )

        final_host = (urlparse(str(response.url)).hostname or "").lower()
        if final_host and final_host not in _ALLOWED_HOSTS:
            raise PdfDownloadForbiddenHostError(
                f"redirected to disallowed host {final_host!r} while fetching {url}"
            )
        return DownloadResult(
            url=str(response.url),
            content=content,
            content_type=content_type or "application/pdf",
        )
    finally:
        if owned_client:
            http_client.close()


__all__ = [
    "DownloadResult",
    "PdfDownloadDisallowedError",
    "PdfDownloadError",
    "PdfDownloadForbiddenHostError",
    "allowed_hosts",
    "fetch_arxiv_pdf",
    "fetch_whitelisted_pdf",
]
