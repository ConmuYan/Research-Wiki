"""Paper id slug generation shared by ``add-literature`` and ``promote``.

Both commands must mint the *same* canonical KB paper id given the same
``(first_author, year, title)`` triple. Otherwise, a paper that was first
registered manually and later promoted from a workspace would end up with
two different cards in the KB. The shared helper lives here so neither
command has to import the other.
"""

from __future__ import annotations

from slugify import slugify

PAPER_SLUG_MAX_LENGTH = 60
PAPER_SLUG_ALLOWED_CHARS = r"[^a-z0-9-]"
PAPER_SLUG_FALLBACK = "paper"


def paper_slug(first_author: str, year: int, title: str) -> str:
    """Return the canonical KB paper id for ``(first_author, year, title)``.

    The format is ``<lastname>-<year>-<title-slug>``, lowercased, with all
    non ``[a-z0-9-]`` characters squashed.
    """
    parts = first_author.replace(",", " ").split()
    last_name = parts[-1] if parts else "anon"
    seed = f"{last_name}-{year}-{title}"
    return (
        slugify(
            seed,
            max_length=PAPER_SLUG_MAX_LENGTH,
            lowercase=True,
            regex_pattern=PAPER_SLUG_ALLOWED_CHARS,
        )
        or PAPER_SLUG_FALLBACK
    )


__all__ = [
    "PAPER_SLUG_ALLOWED_CHARS",
    "PAPER_SLUG_FALLBACK",
    "PAPER_SLUG_MAX_LENGTH",
    "paper_slug",
]
