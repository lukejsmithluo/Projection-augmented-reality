# 项目根目录说明

本仓库包含两个主要子模块：
- `Pre-scanned point cloud/`：ZED 2i 空间映射相关代码与虚拟环境
- `procam-calibration/`：投影-相机标定与质量检测工具

## Git忽略策略
 已在根目录配置 `.gitignore`，以确保不会将临时或体积巨大的文件提交到版本库：
- 忽略 `Pre-scanned point cloud/zed_env/` 虚拟环境目录（用户指定）
- 忽略 `Pre-scanned point cloud/data/` 的映射输出产物（大型 `.obj/.mtl/.png` 等）
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

## 路径与匹配说明
- `.gitignore` 使用 **相对路径** 与 **通配符**，在Windows下亦需使用 **正斜杠** `/`
- 通过 `procam-calibration/**/capture_*/` 规则可匹配子目录中所有 `capture_*`

如需新增忽略规则，请在根目录 `.gitignore` 中追加相应条目，避免分散配置导致维护困难。

更新记录：
- 2025-11-05：完善 `.gitignore`，新增 `Pre-scanned point cloud/data/` 与 `.ruff_cache/` 忽略，避免上传大体积产物与工具缓存。
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