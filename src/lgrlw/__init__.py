"""Research-Wiki -- Literature-Grounded Research Lifecycle Wiki.

``LGRLW`` is the protocol; this package (``lgrlw``) is its reference Python
implementation and CLI.

Public surface in v0.1 MVP:

* :func:`lgrlw.cli.app` -- the Typer application.
* :mod:`lgrlw.schemas` -- pydantic models for KB / workspace frontmatter and
  export manifests.
* :mod:`lgrlw.paths` -- canonical path resolution for a LGRLW project.

Networked fetchers, ``promote``, and MinerU integration are planned for v0.2+
and are deliberately not imported here.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.2.0.dev0"
