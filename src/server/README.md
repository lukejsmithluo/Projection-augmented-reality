# 后端服务（server）

此目录包含 FastAPI 应用与API：
- `main.py`：应用入口与健康检查路由。
- `api/`：依赖、Schema、路由（映射/标定）。
 - 根路径 `/`：已跳转至 `/docs`（Swagger UI），便于非开发者直接使用接口。

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
 - AI 图像生成（AI Image Generation）：
   - `POST /ai-image/edit`（multipart）上传图片并提供 `prompt`，可选 `size`（默认 `1024x1024`），可选 `api_key`（若提供将覆盖当前进程环境变量）。支持多图上传字段 `images`（保留左→右的选择顺序），当前后端将以“最新一张”作为实际生成输入。成功返回生成的图片文件路径：`{"accepted": true, "output_file": "data/ai_images/outputs/gen_YYYYmmdd_HHMMSS.png"}`。若未配置 `OPENAI_API_KEY`，返回错误：`{"accepted": false, "error_code": "NO_API_KEY", "error": "OPENAI_API_KEY not configured"}`。
   - `GET /ai-image/status` → 返回模块状态与最近输出文件路径。

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
 ; # 设置 OpenAI API Key（推荐使用 .env 文件）
 # 在项目根目录创建 .env 文件，并写入：
 # OPENAI_API_KEY=sk-xxxxx
 ; # 调用 AI 图像编辑接口（multipart）
 $filePath = "C:\\path\\to\\local.png"
 # 单图（兼容旧用法）
 $form = @{ prompt = "make it look like watercolor"; size = "1024x1024"; api_key = "sk-xxxxx"; image = Get-Item $filePath }
 Invoke-WebRequest -Uri "http://127.0.0.1:8000/ai-image/edit" -Method POST -Form $form

 # 多图（建议使用 curl 传多个 -F 参数，更好地保留顺序）：
 curl -X POST \
   -F "prompt=make it look like watercolor" \
   -F "size=1024x1024" \
   -F "api_key=sk-xxxxx" \
   -F "images=@C:/path/to/img1.png" \
   -F "images=@C:/path/to/img2.png" \
   -F "images=@C:/path/to/img3.png" \
   http://127.0.0.1:8000/ai-image/edit
```

## 模块注册中心与依赖
- 应用在启动时创建 `ModuleRegistry` 并注册：`spatial_mapping`、`projector_calibration`。
- 路由通过依赖注入（`Depends(get_registry)`) 获取注册中心并调用模块的 `configure()/start()/stop()/status()`。

更新记录：
- 2025-11-19：风格维护（imports 排序与格式统一），修复 CI isort/black 提示；不涉及业务改动。
- 2025-11-10：风格维护（imports 排序与格式统一），修复 CI 提示的 isort/black 问题；不涉及业务改动。
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
- 2025-11-05：映射/标定路由接入模块包装类；新增示例请求体与 PowerShell 调用示例。
 - 2025-11-05：新增根路径 `/` 跳转至 `/docs`，解决首页访问无法看到接口文档的问题。