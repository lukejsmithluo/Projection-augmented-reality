# 后端服务（server）

此目录包含 FastAPI 应用与API：
- `main.py`：应用入口与健康检查路由。
- `api/`：依赖、Schema、路由（映射/标定）。

运行示例：
 ```powershell
 python -m uvicorn src.server.main:app --reload
 ```

## API 路由与示例
- 映射（Mapping）：
  - `POST /mapping/start` 请求体示例：`{"build_mesh": true, "save_texture": true}` → 返回 `{"accepted": true}`。
  - `POST /mapping/stop` → 返回保存的文件列表：`{"saved_files": [".../mesh.obj", ".../mesh.mtl", ".../texture.png"]}`。
  - `GET /mapping/status` → 返回模块状态：`{"module": "spatial_mapping", "status": {"state": "RUNNING"}}`。
- 标定（Calibration）：
  - `POST /calibration/run` 请求体示例：`{"proj_height": 1080, "proj_width": 1920, "rounds": 1}` → 返回 `{"accepted": true}`。
  - `GET /calibration/result` → 当前返回占位信息（后续解析输出文件）。

在 Windows PowerShell 中调用示例：
```powershell
# 启动后端服务
python -m uvicorn src.server.main:app --reload
; # 开始映射
Invoke-RestMethod -Uri "http://127.0.0.1:8000/mapping/start" -Method POST -ContentType 'application/json' -Body '{"build_mesh":true,"save_texture":true}'
; # 停止映射并获取文件
Invoke-RestMethod -Uri "http://127.0.0.1:8000/mapping/stop" -Method POST
; # 运行标定
Invoke-RestMethod -Uri "http://127.0.0.1:8000/calibration/run" -Method POST -ContentType 'application/json' -Body '{"proj_height":1080,"proj_width":1920,"rounds":1}'
```

## 模块注册中心与依赖
- 应用在启动时创建 `ModuleRegistry` 并注册：`spatial_mapping`、`projector_calibration`。
- 路由通过依赖注入（`Depends(get_registry)`) 获取注册中心并调用模块的 `configure()/start()/stop()/status()`。

更新记录：
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
- 2025-11-05：映射/标定路由接入模块包装类；新增示例请求体与 PowerShell 调用示例。