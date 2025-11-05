# [Script] 开发脚本：初始化环境与运行服务（使用完可删除）
$ErrorActionPreference = "Stop";
python -m venv .venv;
.\.venv\Scripts\python.exe -m pip install --upgrade pip;
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn pytest httpx pydantic pydantic-settings PyQt6;
# 风格工具与pre-commit
.\.venv\Scripts\python.exe -m pip install ruff black isort pre-commit;
.\.venv\Scripts\pre-commit.exe install;

Write-Host "Running style checks...";
ruff check src tests scripts .trae;
black --check src tests scripts .trae;
isort --check-only src tests scripts .trae;

Write-Host "Starting API server...";
.\.venv\Scripts\python.exe -m uvicorn src.server.main:app --reload;