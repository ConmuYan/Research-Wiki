"""Filesystem helpers: hashing, directory copy, and YAML frontmatter I/O.

Frontmatter semantics
---------------------

A markdown file starts with frontmatter iff its first line is ``---``. The
frontmatter block ends at the next line that is exactly ``---`` by itself.
Anything after that delimiter is the markdown body. This mirrors Obsidian /
Jekyll / Hugo conventions and is what Research-Wiki commits to.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_DELIMITER = "---"


# ---------------------------------------------------------------------------
# Hashing and directory ops
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy ``src`` onto ``dst``, merging into existing dirs."""
    shutil.copytree(src, dst, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# YAML frontmatter
# ---------------------------------------------------------------------------
def read_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Return ``(frontmatter_dict_or_None, body)`` for the markdown at ``path``.

    If the file has no frontmatter, the returned dict is None and the body
    is the entire file contents.
    """
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:  # noqa: PLR0911
    """Pure-function variant of :func:`read_frontmatter` for testing."""
    # Normalise line endings so the parser behaves the same on Windows.
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalised.startswith(FRONTMATTER_DELIMITER):
        return None, text

    # Strip the opening `---\n`
    after_open = normalised[len(FRONTMATTER_DELIMITER) :]
    if after_open.startswith("\n"):
        after_open = after_open[1:]
    else:
        # A file starting with `---xyz` (no newline) is not a frontmatter file.
        return None, text

    # Find the closing `\n---` line.
    needle = "\n" + FRONTMATTER_DELIMITER
    end = after_open.find(needle)
    if end == -1:
        return None, text

    yaml_block = after_open[:end]
    # Ensure the closing delimiter is followed by EOF or a newline.
    after_close = after_open[end + len(needle) :]
    if after_close and not after_close.startswith("\n"):
        return None, text
    if after_close.startswith("\n"):
        after_close = after_close[1:]

    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None, text

    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, text

    return data, after_close


def write_frontmatter(path: Path, data: dict[str, Any], body: str) -> None:
    """Write ``data`` as YAML frontmatter followed by ``body`` to ``path``.

    Always writes with LF line endings (``newline="\\n"``) regardless of the
    host OS, so that SHA-256 hashes recorded in export-pack manifests stay
    stable across Windows and Linux. Without this, Python on Windows would
    translate each ``\\n`` into ``\\r\\n`` at write time, and any reader on
    a Linux CI (where git stores LF) would re-compute a different digest.
    """
    yaml_block = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip("\n")
    content = f"{FRONTMATTER_DELIMITER}\n{yaml_block}\n{FRONTMATTER_DELIMITER}\n"
    body_clean = body.lstrip("\n")
    if body_clean:
        content += "\n" + body_clean
        if not content.endswith("\n"):
            content += "\n"
    path.write_text(content, encoding="utf-8", newline="\n")


__all__ = [
    "FRONTMATTER_DELIMITER",
    "copy_tree",
    "ensure_dir",
    "parse_frontmatter",
    "read_frontmatter",
    "sha256_file",
    "write_frontmatter",
]
