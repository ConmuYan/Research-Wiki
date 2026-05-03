"""Multi-direction monorepo helpers (v0.3).

A Research-Wiki project can take one of two shapes:

* **Single-direction** (legacy, v0.1/v0.2). The project root holds
  ``literature-kb/`` and ``research-workspaces/`` directly. This is the
  default layout produced by ``lgrlw init <path>`` without
  ``--monorepo``.
* **Monorepo** (v0.3). The project root holds a ``directions/``
  directory; each child ``directions/<slug>/`` is itself a complete
  single-direction subproject (with its own ``.lgrlw.toml`` marker,
  ``literature-kb/``, and ``research-workspaces/``). The umbrella
  ``.lgrlw.toml`` at the monorepo root has ``[project] monorepo = true``
  and ``directions = ["a", "b", ...]`` listing every child slug.

This module is the single place that distinguishes the two layouts.
Every project-scoped CLI command resolves its working ``ProjectPaths``
through :func:`resolve_subproject` so the same backend code path
(``commands/*.py``, ``lint/``, ``promote/``, ``export/``) handles both
layouts transparently.
"""

from __future__ import annotations

from pathlib import Path

from lgrlw.config import load_config
from lgrlw.paths import PROJECT_MARKER, ProjectPaths, find_project_root
from lgrlw.schemas import ProjectConfig

MONOREPO_DIR = "directions"


class MonorepoError(RuntimeError):
    """Raised when monorepo resolution fails (missing direction, slug clash, ...)."""


def is_monorepo_root(root: Path) -> bool:
    """Return True iff ``root/.lgrlw.toml`` declares ``monorepo = true``.

    Returns False if the marker is missing, unreadable, or declares a
    single-direction layout.
    """
    marker = root / PROJECT_MARKER
    if not marker.is_file():
        return False
    try:
        cfg = load_config(marker)
    except (OSError, ValueError):
        return False
    return cfg.monorepo


def load_monorepo_config(root: Path) -> ProjectConfig:
    """Read and validate the monorepo umbrella ``.lgrlw.toml``.

    Raises :class:`MonorepoError` if ``root`` is not actually a monorepo
    umbrella.
    """
    cfg = load_config(root / PROJECT_MARKER)
    if not cfg.monorepo:
        raise MonorepoError(
            f"{root / PROJECT_MARKER} is not a monorepo umbrella (set [project] monorepo = true)"
        )
    return cfg


def direction_root(monorepo_root: Path, direction: str) -> Path:
    """Return the on-disk path of ``directions/<direction>/`` under ``monorepo_root``.

    Existence is *not* checked here; callers compose this with
    :func:`load_subproject` when they need a validated subproject.
    """
    return monorepo_root / MONOREPO_DIR / direction


def list_directions(monorepo_root: Path) -> list[str]:
    """Return the validated direction slug list from the umbrella ``.lgrlw.toml``."""
    return list(load_monorepo_config(monorepo_root).directions)


def detect_direction_from_cwd(monorepo_root: Path, cwd: Path) -> str | None:
    """Infer which direction subproject contains ``cwd``, if any.

    Returns the direction slug (a single segment under
    ``directions/``) when ``cwd`` sits inside ``monorepo_root /
    directions/<slug>/``. Returns ``None`` otherwise.
    """
    try:
        rel = cwd.resolve().relative_to(monorepo_root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2 or parts[0] != MONOREPO_DIR:
        return None
    return parts[1]


def resolve_subproject(
    root: Path | None,
    direction: str | None,
    *,
    cwd: Path | None = None,
) -> ProjectPaths:
    """Return the :class:`ProjectPaths` for one direction subproject.

    The resolution order is:

    1. If ``root`` is given, it is treated as the explicit project root.
       Otherwise the function walks upward from ``cwd`` (or
       ``Path.cwd()``) looking for the nearest ``.lgrlw.toml``.
    2. If the resolved root is a single-direction project, ``direction``
       must be ``None`` (or match the single direction's slug, in which
       case the subproject root is the resolved root itself); otherwise
       :class:`MonorepoError` is raised.
    3. If the resolved root is a monorepo umbrella:

       * If ``direction`` is given, ``directions/<direction>/`` is
         returned (provided it exists in the umbrella's
         ``directions`` list and on disk).
       * If ``direction`` is omitted, the function tries to infer it
         from ``cwd``; failing that, raises
         :class:`MonorepoError` with a helpful message.

    The returned :class:`ProjectPaths` is *always* a
    single-direction subproject, so every backend (lint / promote /
    export / add-literature) can keep operating on a vanilla
    ``ProjectPaths`` with no monorepo awareness.
    """
    cwd_resolved = (cwd or Path.cwd()).resolve()
    if root is None:
        try:
            resolved = find_project_root(cwd_resolved)
        except FileNotFoundError as exc:
            raise MonorepoError(str(exc)) from exc
    else:
        resolved = root.resolve()
        if not (resolved / PROJECT_MARKER).is_file():
            raise MonorepoError(
                f"{resolved} is not a Research-Wiki project (missing {PROJECT_MARKER})"
            )

    cfg = load_config(resolved / PROJECT_MARKER)

    if not cfg.monorepo:
        if direction is not None and direction != cfg.direction:
            raise MonorepoError(
                f"{resolved} is a single-direction project (direction={cfg.direction!r}); "
                f"--direction {direction!r} is not applicable"
            )
        return ProjectPaths(
            root=resolved,
            kb_name=cfg.kb_name,
            workspaces_name=cfg.workspaces_name,
        )

    chosen = direction or detect_direction_from_cwd(resolved, cwd_resolved)
    if chosen is None:
        directions = ", ".join(cfg.directions) or "<none yet>"
        raise MonorepoError(
            f"{resolved} is a monorepo (directions: {directions}); "
            "pass --direction <slug> or run from inside directions/<slug>/"
        )
    if chosen not in cfg.directions:
        directions = ", ".join(cfg.directions) or "<none yet>"
        raise MonorepoError(
            f"unknown direction {chosen!r}; {resolved / PROJECT_MARKER} lists [{directions}]"
        )

    sub_root = direction_root(resolved, chosen)
    if not (sub_root / PROJECT_MARKER).is_file():
        raise MonorepoError(f"direction {chosen!r} is missing {PROJECT_MARKER} at {sub_root}")

    sub_cfg = load_config(sub_root / PROJECT_MARKER)
    return ProjectPaths(
        root=sub_root,
        kb_name=sub_cfg.kb_name,
        workspaces_name=sub_cfg.workspaces_name,
    )


def iter_subprojects(monorepo_root: Path) -> list[ProjectPaths]:
    """Return :class:`ProjectPaths` for every direction in a monorepo.

    Used by ``lgrlw lint`` to walk every subproject when invoked at the
    monorepo umbrella level. Order matches ``directions`` in the
    umbrella ``.lgrlw.toml``.
    """
    cfg = load_monorepo_config(monorepo_root)
    out: list[ProjectPaths] = []
    for slug in cfg.directions:
        sub_root = direction_root(monorepo_root, slug)
        if not (sub_root / PROJECT_MARKER).is_file():
            raise MonorepoError(
                f"direction {slug!r} listed in umbrella but missing {PROJECT_MARKER} at {sub_root}"
            )
        sub_cfg = load_config(sub_root / PROJECT_MARKER)
        out.append(
            ProjectPaths(
                root=sub_root,
                kb_name=sub_cfg.kb_name,
                workspaces_name=sub_cfg.workspaces_name,
            )
        )
    return out


__all__ = [
    "MONOREPO_DIR",
    "MonorepoError",
    "detect_direction_from_cwd",
    "direction_root",
    "is_monorepo_root",
    "iter_subprojects",
    "list_directions",
    "load_monorepo_config",
    "resolve_subproject",
]
