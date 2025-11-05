# 项目使用手册（用户与开发者）

## 概述
本项目采用模块化分层（common/modules/server/ui/tests），统一 OOP 接口契约与 CI/CD 流程，支持 ZED 2i 空间映射与投影仪标定两大能力。

## 快速开始
- 环境要求：Windows 11；Python 3.10+；ZED SDK 5.1.0；GPU RTX 3090 Ti。
- 克隆仓库后，本地开发可执行：
  - `.\\scripts\\dev.ps1`（创建虚拟环境、安装依赖、执行风格检查并启动 API）。
- 启动后端 API：
  - `python -m uvicorn src.server.main:app --reload`
- 启动 UI：
  - `python .\\src\\ui\\app.py`

## 模块运行指南
### 空间映射（Pre-scanned point cloud）
- 必须使用模块自带的虚拟环境运行：在 `Pre-scanned point cloud/src/` 中执行：
  - `..\\zed_env\\Scripts\\python.exe spatial_mapping.py --build_mesh --save_texture`
- 输出：`data/` 目录将生成 `.obj/.mtl/.png` 纹理与材质文件；叠加显示绘制所有已映射块（性能受块数影响）。
- Unreal 导入：若使用米为单位，导入时需统一缩放 100 倍（项目默认厘米）。

### 投影标定（Projector-Calibration）
- 运行：在 `Projector-Calibration/` 目录中执行：
  - `python calibrate_optimized.py`（按指引完成拍摄与参数输出）。
- 输出：生成投影-相机标定参数与质量评估报告。

## API 使用
- 健康检查：`GET /health` → `{ "status": "ok" }`
- 映射（Mapping）：
  - `POST /mapping/start` 请求体：`{"build_mesh": true, "save_texture": true}` → 返回 `{ "accepted": true }`。
  - `POST /mapping/stop` → 返回 `{ "saved_files": ["...obj", "...mtl", "...png"] }`。
  - `GET /mapping/status` → 返回 `{ "module": "spatial_mapping", "status": {"state": "RUNNING"} }`。
- 标定（Calibration）：
  - `POST /calibration/run` 请求体：`{"proj_height": 1080, "proj_width": 1920, "rounds": 1}` → 返回 `{ "accepted": true }`。
  - `GET /calibration/result` → 当前返回占位信息（后续解析输出文件）。

PowerShell 调用示例（Windows）：
```powershell
python -m uvicorn src.server.main:app --reload
; Invoke-RestMethod -Uri "http://127.0.0.1:8000/mapping/start" -Method POST -ContentType 'application/json' -Body '{"build_mesh":true,"save_texture":true}'
; Invoke-RestMethod -Uri "http://127.0.0.1:8000/mapping/stop" -Method POST
; Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/run" -Method POST -ContentType 'application/json' -Body '{"proj_height":1080,"proj_width":1920,"rounds":1}'
```

## UI 使用
- 主窗口包含“空间映射”与“投影标定”标签页；操作按钮通过 HTTP 调用后端 API 执行任务；本地模式可走事件总线提升性能。

## 常见问题（FAQ）
- 未生成纹理：请确保启用 `--save_texture` 参数，并在构建网格时启用 `--build_mesh`。
- 叠加显示不一致：已修复为绘制所有块；若块数较多可适当降低更新频率或分辨率以提升性能。
- Pydantic v2 兼容：已使用 `pydantic-settings` 管理 `BaseSettings`；旧版导入将报错。
- 硬件调试：禁止使用 mock，需在真实设备上验证。

## 开发规范
- 提交前：`pre-commit` 会运行 `ruff/black/isort` 与 `pytest -m "not hardware"`（失败阻止提交）。
- CI：在 `windows-latest` 平台运行风格检查与非硬件测试。
- 目录与命名：遵循 PEP8；类 `PascalCase`；函数/变量 `snake_case`；常量大写下划线。
- 文档：新增或修改非 Debug/Test/Temp 文件后，需更新对应目录 `README.md`。

## 目录结构速览
- `src/common`：配置、日志、事件、类型、模块基类、注册中心。
- `src/server`：FastAPI 应用入口与路由。
- `src/ui`：PyQt6 应用入口与窗口。
- `src/modules`：模块包装（空间映射、投影标定）。
- `tests`：Pytest 测试（非硬件）。