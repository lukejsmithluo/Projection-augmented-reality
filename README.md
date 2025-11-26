# 项目根目录说明

本仓库包含两个主要子模块：
- `Pre-scanned point cloud/`：ZED 2i 空间映射相关代码与虚拟环境
- `procam-calibration/`：投影-相机标定与质量检测工具

## Git忽略策略
 已在根目录配置 `.gitignore`，以确保不会将临时或体积巨大的文件提交到版本库：
- 允许提交 `Pre-scanned point cloud/zed_env/` 虚拟环境目录（用户要求）；为避免通用 `zed_env/` 忽略规则影响，已在 `.gitignore` 中添加显式取消忽略 `!/Pre-scanned point cloud/zed_env/`
- 跟踪 `Pre-scanned point cloud/data/` 中的资产文件（`.obj/.mtl/.png`），其余内容默认忽略
- 忽略 `procam-calibration/` 下所有以 `capture_` 开头的目录（用户指定），包括子目录中的 `capture_*`，且**递归忽略其所有内容**（已添加 `capture_*/` 与 `capture_*/**` 规则）
 - 忽略 `procam-calibration/graycode_pattern/` 目录及其所有内容（含子目录匹配规则）
- 忽略通用虚拟环境、Python缓存、IDE配置、操作系统隐藏文件等
 - 新增忽略工具缓存：`.ruff_cache/`

若某些目录或文件已被提交过版本库，需要执行以下命令从跟踪中移除：
```
# 仅从Git索引中移除，不删除本地文件
git rm -r --cached "Pre-scanned point cloud/zed_env"
git rm -r --cached procam-calibration/capture_*
 git rm -r --cached procam-calibration/graycode_pattern
```

如需将 `Pre-scanned point cloud/zed_env/` 提交到仓库，请在更新 `.gitignore` 后执行：
```
# 确保已取消忽略并强制添加到索引
git add -f "Pre-scanned point cloud/zed_env"
git commit -m "Track module venv: Pre-scanned point cloud/zed_env"
git push
```

注意：提交完整虚拟环境可能显著增加仓库体积；若后续希望优化，可考虑使用 Git LFS 管理大二进制文件，或改为维护精确的 `requirements.txt`/`environment.yml`。

## 路径与匹配说明
- `.gitignore` 使用 **相对路径** 与 **通配符**，在Windows下亦需使用 **正斜杠** `/`
- 通过 `procam-calibration/**/capture_*/` 规则可匹配子目录中所有 `capture_*`

如需新增忽略规则，请在根目录 `.gitignore` 中追加相应条目，避免分散配置导致维护困难。

更新记录：
- 2025-11-05：完善 `.gitignore`，新增 `Pre-scanned point cloud/data/` 与 `.ruff_cache/` 忽略，避免上传大体积产物与工具缓存。
- 2025-11-10：调整忽略策略，允许提交 `Pre-scanned point cloud/data/` 下的 `.obj/.mtl/.png` 资产文件；其余仍忽略以控制仓库体积。
 - 2025-11-26：应用户要求，允许提交 `Pre-scanned point cloud/zed_env/` 虚拟环境目录；在 `.gitignore` 中添加 `!/Pre-scanned point cloud/zed_env/` 显式取消忽略。
## 框架初始化（2025-11-05）

为支持模块化架构与CI/CD，新增以下目录与文件：
- `src/common/`：基础设施（配置、日志、事件、类型、模块基类、注册中心）。
- `src/server/`：FastAPI 应用入口与API路由（映射/标定），提供 `/health`。
- `src/ui/`：PyQt6 UI骨架（Tab界面）。
- `src/modules/`：模块包装（预扫描点云、投影标定）。
- `tests/`：基础单元测试（注册中心、健康检查）。
- `.pre-commit-config.yaml`：本地提交时运行 `pytest -m "not hardware"`，失败阻止提交。
- `.github/workflows/ci.yml`：GitHub Actions 在 Windows 上运行非硬件测试。
- `scripts/dev.ps1`：开发便捷脚本（PowerShell）。

 请根据项目规则，后续新增或修改非 Debug/Test/Temp 文件时，务必同步更新对应目录的 `README.md`。

## 可复现环境（Reproducible Environment）
为确保他人能够在 Windows 11 上完整复现本项目，提供两套方式：

- 根环境（后端 + UI）：使用项目根目录的 `requirements.txt`（已固定版本）
- 预扫描模块（ZED 2i 空间映射）：直接使用仓库中的 `Pre-scanned point cloud/zed_env/`，或按需从 `requirements.txt` 重新构建

步骤（PowerShell）：
```
# 1) 创建并激活根虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 升级pip并安装固定依赖
python -m pip install -U pip; python -m pip install -r requirements.txt

# 3) （可选）运行后端服务
python -m uvicorn src.server.main:create_app --factory --reload

# 4) （可选）运行非硬件测试
python -m pytest -m "not hardware"
```

预扫描模块（ZED）环境选项：
- 直接使用已提交的 `Pre-scanned point cloud/zed_env/`（推荐，体积较大）
- 重新构建：
```
# 1) 创建并激活 zed_env（路径与项目规则一致）
python -m venv "Pre-scanned point cloud/zed_env"
& "Pre-scanned point cloud/zed_env/Scripts/python.exe" -m pip install -U pip
& "Pre-scanned point cloud/zed_env/Scripts/python.exe" -m pip install -r "Pre-scanned point cloud/requirements.txt"

# 2) 安装 ZED Python SDK（pyzed）
#   注意：pyzed 不在 PyPI 发布，需安装 ZED SDK 5.1.0 后，使用官方提供的本地 wheel 文件
#   示例：
#   & "Pre-scanned point cloud/zed_env/Scripts/pip.exe" install C:\path\to\pyzed-5.1-cp310-cp310-win_amd64.whl

# 3) 运行空间映射（必须在 zed_env 中运行）
& "Pre-scanned point cloud/zed_env/Scripts/python.exe" "Pre-scanned point cloud/src/spatial_mapping.py"
```

说明与注意：
- `pyzed` 依赖真实硬件与 ZED SDK 安装；CI 中不运行相关测试（`-m "not hardware"`）。
- 所有 PowerShell 命令使用分号 `;` 串联，不使用 `&&`。
- 若你希望减少仓库体积，可考虑使用 Git LFS 管理大体积产物。

## 风格检查启用（CI & 本地）
- 已在 CI 中启用 `ruff/black/isort` 风格检查（作用范围：`src/`、`tests/`、`scripts/`、`.trae/`）。
- 本地通过 `pre-commit` 自动运行风格检查与非硬件测试，失败阻止提交。

## 项目使用手册
- 详见 `docs/USER_MANUAL.md`（中文），包含快速开始、API/UI 说明、模块运行指南、常见问题与开发规范。
 - 若你只是想在浏览器上使用接口（无需了解代码），可参考：`docs/WEB_API_USAGE.md`（通过 `/docs` 交互文档直接调用接口）。

## 一键启动后端服务（适合非开发者）
在项目根目录运行：
```
python main.py
```
启动后访问：`http://127.0.0.1:8000/docs`（Swagger UI，可在线执行请求）。

可选环境变量：
- `API_HOST`（默认 `127.0.0.1`）
- `API_PORT`（默认 `8000`）
- `API_RELOAD`（默认启用；设置为 `0` 或 `false` 关闭热重载）

开发者启动方式（手动设置 PYTHONPATH）：
```
$env:PYTHONPATH = (Resolve-Path .).Path
python -m uvicorn src.server.main:create_app --factory --reload
```
