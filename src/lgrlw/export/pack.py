"""Build a dated, immutable KB snapshot (export pack) for a workspace.

The pack is constructed under
``literature-kb/06_Exports/<workspace>_<YYYY-MM-DD>/`` and simultaneously
mirrored under ``research-workspaces/<workspace>/01_KB_Exports/<same-name>/``
so that the workspace has an append-only, read-only copy of the KB state at
the moment it was invoked.

Policy (v0.1)
-------------

Every pack contains, relative to the KB root:

* ``02_Literature/Papers/`` -- all paper cards
* ``03_Field_Structure/``   -- the user-curated field structure
* ``05_Evidence/``          -- the user-curated evidence / claims / open problems

``01_Raw/`` and ``06_Exports/`` are deliberately excluded: raw PDFs are too
heavy to duplicate and packs must not reference other packs.

A ``export_manifest.json`` at the pack root records every copied file and
its SHA-256, which ``lgrlw lint`` later uses to detect tampering.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from lgrlw import __version__
from lgrlw.fs import ensure_dir, sha256_file
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import ExportManifest

# KB subtrees whitelisted for copying into a pack.
KB_INCLUDE: tuple[str, ...] = (
    "02_Literature/Papers",
    "03_Field_Structure",
    "05_Evidence",
)

MANIFEST_NAME = "export_manifest.json"


def build_export_pack(
    paths: ProjectPaths,
    workspace_id: str,
    *,
    now: datetime | None = None,
) -> Path:
    """Materialise a new export pack for ``workspace_id`` and return its path.

    Raises
    ------
    FileNotFoundError
        The workspace directory does not exist.
    FileExistsError
        An export pack with the same date-stamped name already exists. Packs
        are immutable; delete or rename the existing one if you really need
        to regenerate.
    """
    workspace_root = paths.workspace(workspace_id)
    if not workspace_root.is_dir():
        raise FileNotFoundError(f"workspace does not exist: {workspace_root}")

    stamp_at = now or datetime.now(timezone.utc)
    pack_name = f"{workspace_id}_{stamp_at.strftime('%Y-%m-%d')}"
    pack_dir = paths.kb_exports / pack_name
    if pack_dir.exists():
        raise FileExistsError(f"export pack already exists: {pack_dir}. Packs are immutable.")

    ensure_dir(pack_dir)

    # ------------------------------------------------------------------
    # Copy whitelisted KB subtrees into the pack.
    # ------------------------------------------------------------------
    for rel in KB_INCLUDE:
        src = paths.kb / rel
        if not src.exists():
            continue
        shutil.copytree(src, pack_dir / rel, dirs_exist_ok=False)

    # ------------------------------------------------------------------
    # Hash every file and collect the paper-id list.
    # ------------------------------------------------------------------
    files: dict[str, str] = {}
    paper_ids: list[str] = []
    papers_prefix = "02_Literature/Papers/"

    for f in sorted(pack_dir.rglob("*")):
        if not f.is_file() or f.name == MANIFEST_NAME:
            continue
        rel_posix = f.relative_to(pack_dir).as_posix()
        files[rel_posix] = sha256_file(f)
        if rel_posix.startswith(papers_prefix) and rel_posix.endswith(".md"):
            paper_ids.append(f.stem)

    manifest = ExportManifest(
        tool_version=__version__,
        workspace_id=workspace_id,
        exported_at=stamp_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        kb_root_relative=paths.kb.name,
        pack_dir_relative=f"{paths.kb.name}/06_Exports/{pack_name}",
        paper_ids=sorted(paper_ids),
        files=files,
    )
    # Always write with LF so the manifest itself, and by extension the
    # SHA-256 digests it records for sibling pack files, stay identical on
    # Windows and Linux. See fs.write_frontmatter for the broader rationale.
    (pack_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    # ------------------------------------------------------------------
    # Mirror into the workspace so the writing side has a local copy.
    # ------------------------------------------------------------------
    workspace_mirror_root = paths.workspace_kb_exports(workspace_id)
    ensure_dir(workspace_mirror_root)
    mirror = workspace_mirror_root / pack_name
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(pack_dir, mirror)

    return pack_dir


__all__ = ["KB_INCLUDE", "MANIFEST_NAME", "build_export_pack"]
