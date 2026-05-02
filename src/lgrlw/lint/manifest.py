"""Export-pack manifest integrity: every listed file hashes to its recorded SHA-256."""

from __future__ import annotations

import json

from pydantic import ValidationError

from lgrlw.fs import sha256_file
from lgrlw.paths import ProjectPaths
from lgrlw.schemas import ExportManifest, LintFinding, LintSeverity

RULE_MISSING = "manifest.missing"
RULE_INVALID = "manifest.invalid"
RULE_FILE_MISSING = "manifest.file_missing"
RULE_SHA_MISMATCH = "manifest.sha256_mismatch"
RULE_FILE_EXTRA = "manifest.file_extra"

MANIFEST_NAME = "export_manifest.json"


def check_manifests(paths: ProjectPaths) -> list[LintFinding]:
    """Validate every export pack under ``literature-kb/06_Exports/``."""
    findings: list[LintFinding] = []

    if not paths.kb_exports.is_dir():
        return findings

    for pack_dir in sorted(p for p in paths.kb_exports.iterdir() if p.is_dir()):
        manifest_path = pack_dir / MANIFEST_NAME
        if not manifest_path.is_file():
            findings.append(
                LintFinding(
                    rule=RULE_MISSING,
                    severity=LintSeverity.error,
                    path=str(pack_dir),
                    message=f"export pack is missing {MANIFEST_NAME}",
                )
            )
            continue

        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = ExportManifest.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            findings.append(
                LintFinding(
                    rule=RULE_INVALID,
                    severity=LintSeverity.error,
                    path=str(manifest_path),
                    message=f"export_manifest.json is invalid: {exc}",
                )
            )
            continue

        listed: set[str] = set(manifest.files.keys())
        for rel, expected in manifest.files.items():
            f = pack_dir / rel
            if not f.is_file():
                findings.append(
                    LintFinding(
                        rule=RULE_FILE_MISSING,
                        severity=LintSeverity.error,
                        path=str(f),
                        message=f"manifest lists {rel} but file is missing",
                    )
                )
                continue
            actual = sha256_file(f)
            if actual != expected:
                findings.append(
                    LintFinding(
                        rule=RULE_SHA_MISMATCH,
                        severity=LintSeverity.error,
                        path=str(f),
                        message=(
                            f"sha256 mismatch for {rel} "
                            f"(manifest {expected[:12]}... vs actual {actual[:12]}...)"
                        ),
                        hint="pack contents have been modified after export; regenerate the pack",
                    )
                )

        for f in sorted(pack_dir.rglob("*")):
            if not f.is_file() or f.name == MANIFEST_NAME:
                continue
            rel_posix = f.relative_to(pack_dir).as_posix()
            if rel_posix not in listed:
                findings.append(
                    LintFinding(
                        rule=RULE_FILE_EXTRA,
                        severity=LintSeverity.warning,
                        path=str(f),
                        message=f"{rel_posix} is not listed in {MANIFEST_NAME}",
                    )
                )

    return findings


__all__ = [
    "MANIFEST_NAME",
    "RULE_FILE_EXTRA",
    "RULE_FILE_MISSING",
    "RULE_INVALID",
    "RULE_MISSING",
    "RULE_SHA_MISMATCH",
    "check_manifests",
]
