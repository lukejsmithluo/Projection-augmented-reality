# 路由（routes）

此目录包含各模块的 FastAPI 路由文件：
- `mapping_routes.py`：空间映射模块端点（POST `/mapping/start`、POST `/mapping/stop`、GET `/mapping/status`）。
- `calibration_routes.py`：投影标定模块端点（POST `/calibration/run`、GET `/calibration/result`）。
- `ai_image_routes.py`：AI 图像生成端点（GET `/ai-image/status`、POST `/ai-image/edit`）。

维护记录：
- 2025-11-21：AI 图像端点补充可选字段 `model` 与 `api_org_id`，并在 403 场景将组织未验证映射为 `ORG_NOT_VERIFIED`；文档与示例同步更新。
- 2025-11-19：风格维护（isort 导入顺序修复），不改动业务逻辑。

> 说明：遵循项目“模块接口契约”，路由仅通过模块注册中心 `ModuleRegistry` 对外调用模块接口，不直接耦合核心实现。