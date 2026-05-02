"""Allow ``python -m lgrlw`` as an alternative to the installed ``lgrlw`` script."""

from __future__ import annotations

from lgrlw.cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
