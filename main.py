#!/usr/bin/env python3
"""
Launcher for starting the FastAPI server so non-developers can use
the web API at `http://127.0.0.1:8000/docs` with a single command.

Usage:
    python main.py

Environment overrides (optional):
    API_HOST   - default "127.0.0.1"
    API_PORT   - default "8000"
    API_RELOAD - "1"/"true" to enable reload (default enabled)

Notes:
    - Ensures PYTHONPATH includes the repository root so imports work.
    - Requires `uvicorn`. If missing, install via:
        python -m pip install "uvicorn[standard]"
"""

import os
import sys
from importlib.util import find_spec


def ensure_pythonpath() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    existing = os.environ.get("PYTHONPATH")
    if existing:
        parts = existing.split(os.pathsep)
        if root not in parts:
            os.environ["PYTHONPATH"] = root + os.pathsep + existing
    else:
        os.environ["PYTHONPATH"] = root


def main() -> None:
    ensure_pythonpath()

    if find_spec("uvicorn") is None:
        print(
            "ERROR: 'uvicorn' is not installed. Install it with: \n"
            "    python -m pip install \"uvicorn[standard]\"",
            file=sys.stderr,
        )
        sys.exit(1)

    # Lazy import after PYTHONPATH is set
    import uvicorn

    host = os.environ.get("API_HOST", "127.0.0.1")
    port_str = os.environ.get("API_PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        print(f"WARN: Invalid API_PORT '{port_str}', falling back to 8000")
        port = 8000

    reload_env = os.environ.get("API_RELOAD", "1").lower()
    reload_enabled = reload_env not in ("0", "false")

    print(
        f"Starting FastAPI at http://{host}:{port} (reload={'on' if reload_enabled else 'off'})"
    )

    # Use factory string to avoid import-time issues and honor reload
    uvicorn.run(
        "src.server.main:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()