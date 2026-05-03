"""Research-Wiki -- Literature-Grounded Research Lifecycle Wiki.

``LGRLW`` is the protocol; this package (``lgrlw``) is its reference Python
implementation and CLI.

Public surface as of v0.3 (in development on ``develop/v0.3``):

* :func:`lgrlw.cli.app` -- the Typer application (``lgrlw init`` /
  ``new-workspace`` / ``add-literature`` / ``export-pack`` / ``promote`` /
  ``lint`` / ``add-direction`` / ``mcp serve``).
* :mod:`lgrlw.schemas` -- pydantic models for KB / workspace frontmatter,
  fetched paper metadata, and export manifests.
* :mod:`lgrlw.paths` -- canonical path resolution for a LGRLW project,
  including monorepo support (``directions/<slug>/``).
* :mod:`lgrlw.fetchers` -- networked metadata fetchers (Crossref, arXiv,
  OpenAlex, Semantic Scholar) used by ``add-literature``.
* :mod:`lgrlw.promote` -- atomic workspace-to-KB promotion ceremony.
* :mod:`lgrlw.mcp` -- optional Model Context Protocol server exposing
  every CLI command and read-only KB / workspace resources. Requires the
  ``[mcp]`` extra (``pip install "lgrlw[mcp]"``).

MinerU integration, Zotero sync, and other `Later` roadmap items remain
deferred and are deliberately not imported here.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.3.0.dev0"
