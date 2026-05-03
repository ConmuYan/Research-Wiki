"""Research-Wiki -- Literature-Grounded Research Lifecycle Wiki.

``LGRLW`` is the protocol; this package (``lgrlw``) is its reference Python
implementation and CLI.

Public surface as of v0.2:

* :func:`lgrlw.cli.app` -- the Typer application (``lgrlw init`` /
  ``new-workspace`` / ``add-literature`` / ``export-pack`` / ``promote`` /
  ``lint``).
* :mod:`lgrlw.schemas` -- pydantic models for KB / workspace frontmatter,
  fetched paper metadata, and export manifests.
* :mod:`lgrlw.paths` -- canonical path resolution for a LGRLW project.
* :mod:`lgrlw.fetchers` -- networked metadata fetchers (Crossref, arXiv,
  OpenAlex, Semantic Scholar) used by ``add-literature``.
* :mod:`lgrlw.promote` -- atomic workspace-to-KB promotion ceremony.

MinerU integration, Zotero sync, MCP servers, and other `Later` roadmap
items remain deferred and are deliberately not imported here.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.2.0"
