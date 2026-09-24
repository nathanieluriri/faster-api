from __future__ import annotations

import os
import sys
from pathlib import Path


def project_python(root: Path | None = None) -> str:
    """The interpreter that has the project's dependencies: the active virtualenv, a local .venv/venv, or ours."""
    root = root or Path.cwd()
    candidates = []
    if os.environ.get("VIRTUAL_ENV"):
        candidates.append(Path(os.environ["VIRTUAL_ENV"]))
    candidates += [root / ".venv", root / "venv"]
    for env in candidates:
        for python in (env / "bin" / "python", env / "Scripts" / "python.exe"):
            if python.exists():
                return str(python)
    return sys.executable
