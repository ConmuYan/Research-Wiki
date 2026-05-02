"""Locate bundled template / schema resources in both editable and wheel installs.

Resolution order:

1. Installed wheel: ``<site-packages>/lgrlw/_templates`` (populated at build
   time via ``[tool.hatch.build.targets.wheel.force-include]`` in
   ``pyproject.toml``).
2. Editable / dev install: fall back to ``<repo-root>/templates``.

The same logic applies to ``schemas``. Both directories are considered
authoritative; the repository tree under ``templates/`` and ``schemas/`` is
treated as *canonical* and the wheel copy is merely a deployment artefact.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def _package_data(subdir: str) -> Path | None:
    """Return the on-disk Path of ``lgrlw/<subdir>`` if it exists."""
    try:
        pkg = files("lgrlw")
    except ModuleNotFoundError:  # pragma: no cover - extreme edge case
        return None
    candidate = pkg.joinpath(subdir)
    try:
        # ``Traversable.is_dir`` is present since Python 3.12; fall back
        # to constructing a Path and checking filesystem state otherwise.
        if hasattr(candidate, "is_dir") and candidate.is_dir():
            return Path(str(candidate))
    except (OSError, TypeError):
        pass
    as_path = Path(str(candidate))
    return as_path if as_path.is_dir() else None


def _dev_fallback(subdir_in_pkg: str, repo_subdir: str, sentinel: str) -> Path | None:
    """Walk upward from this file to find ``<repo>/<repo_subdir>/<sentinel>``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / repo_subdir
        if (candidate / sentinel).exists():
            return candidate
    # Fallback: accept the directory even without a sentinel.
    for parent in here.parents:
        candidate = parent / repo_subdir
        if candidate.is_dir():
            return candidate
    return None


def templates_root() -> Path:
    """Return the directory that contains bundled skeleton templates.

    Must satisfy ``(<result>/literature-kb).is_dir()``.
    """
    pkg = _package_data("_templates")
    if pkg is not None and (pkg / "literature-kb").is_dir():
        return pkg
    dev = _dev_fallback("_templates", "templates", "literature-kb")
    if dev is not None:
        return dev
    raise RuntimeError(
        "Cannot locate Research-Wiki templates. Expected either "
        "<site-packages>/lgrlw/_templates/ or <repo>/templates/."
    )


def schemas_root() -> Path:
    """Return the directory that contains bundled JSON schemas."""
    pkg = _package_data("_schemas")
    if pkg is not None:
        return pkg
    dev = _dev_fallback("_schemas", "schemas", "paper.schema.json")
    if dev is not None:
        return dev
    raise RuntimeError(
        "Cannot locate Research-Wiki schemas. Expected either "
        "<site-packages>/lgrlw/_schemas/ or <repo>/schemas/."
    )


__all__ = ["schemas_root", "templates_root"]
