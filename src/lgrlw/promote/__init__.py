"""Promotion ceremony: workspace -> KB transition for accepted papers.

The implementation lives in :mod:`lgrlw.promote.run`; this package is the
public surface used by :mod:`lgrlw.commands.promote`.
"""

from __future__ import annotations

from lgrlw.promote.run import (
    PromoteError,
    PromoteResult,
    promote_workspace,
)

__all__ = ["PromoteError", "PromoteResult", "promote_workspace"]
