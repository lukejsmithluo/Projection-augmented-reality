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
    try:
        uvicorn.run(
            "src.server.main:create_app",
            factory=True,
            host=host,
            port=port,
            reload=reload_enabled,
        )
    except OSError as e:
        # Windows-specific: WinError 10013 (permission denied / excluded port range)
        winerr = getattr(e, "winerror", None)
        if winerr == 10013:
            print(
                "\nERROR: WinError 10013 — 端口或套接字权限受限。\n"
                "可能原因：\n"
                " - 该端口被系统保留或策略排除（excluded port range）\n"
                " - 防火墙/杀毒软件阻止 Python 监听\n"
                " - 企业安全策略限制本地监听\n",
                file=sys.stderr,
            )
            # Simple fallback: try alternative port if environment allows
            fallback_ports = [18000, 9000]
            for fp in fallback_ports:
                print(f"尝试回退端口 {fp}...", file=sys.stderr)
                try:
                    uvicorn.run(
                        "src.server.main:create_app",
                        factory=True,
                        host=host,
                        port=fp,
                        reload=reload_enabled,
                    )
                    return
                except OSError as e2:
                    if getattr(e2, "winerror", None) == 10013:
                        continue
                    raise

            print(
                "\n仍失败。请尝试以下操作：\n"
                " 1) 更换端口运行：在PowerShell中执行\n"
                "    $env:API_PORT='18000'; python main.py\n"
                " 2) 检查Windows防火墙，允许当前Python可执行文件的入站连接\n"
                " 3) 以管理员身份运行 PowerShell（可能有企业策略限制）\n"
                " 4) 查看系统保留端口：\n"
                "    netsh int ipv4 show excludedportrange protocol=tcp\n"
                " 5) 若为公司设备，联系IT解除本机监听限制或指定允许端口\n",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            # Re-raise non-10013 errors
            raise


if __name__ == "__main__":
    main()
