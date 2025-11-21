# 后端服务（server）

此目录包含 FastAPI 应用与API：
- `main.py`：应用入口与健康检查路由。
- `api/`：依赖、Schema、路由（映射/标定）。
 - 根路径 `/`：已跳转至 `/docs`（Swagger UI），便于非开发者直接使用接口。
 - 表单/文件上传（multipart/form-data）路由需要额外依赖：`python-multipart`。CI 已安装该库，本地开发请执行：

   ```powershell
   python -m pip install python-multipart
   ```

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
   - `POST /ai-image/edit`（multipart）上传图片并提供 `prompt`。可选字段：
     - OpenAI：`size`（默认 `1024x1024`，允许 `256x256/512x512/1024x1024`）。
     - Gemini：`aspect_ratio`（允许 `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9`）、`image_resolution`（允许 `1K/2K/4K`，需大写 K）。
     - 通用：`model`（支持 `gemini-2.5-flash-image`/`gemini-3-pro-image-preview`/`gpt-image-1` 等图像模型）、`provider`（`gemini|openai`，默认保持 `openai` 以兼容既有用例）、`api_key`（覆盖当前进程环境变量）、`api_org_id`（仅 OpenAI，用于组织）。
     支持多图上传字段 `images`（保留左→右的选择顺序），当前后端将以“最新一张”作为实际生成输入。成功返回生成的图片文件路径：`{"accepted": true, "output_file": "data/ai_images/outputs/gen_YYYYmmdd_HHMMSS.png"}`。
     - 保存策略：所有上传图片均保存到 `data/ai_images/uploads`，文件名由存储服务生成且全局唯一（时间戳+序号），便于后续留痕与复现；生成输出统一保存到 `data/ai_images/outputs`（`PNG/JPG`）。
     - 上传数量限制（后端强制）：
       - OpenAI（`gpt-image-1`）：最多 1 张；
       - Gemini 3 Pro Image（`gemini-3-pro-image-preview`）：最多 14 张；
       - Gemini 2.5（含 `gemini-2.5-flash-image`）与其他 Gemini/Imagen：默认最多 16 张；
       超过上限时返回统一错误：`{"accepted": false, "error_code": "TOO_MANY_IMAGES", "error": "..."}`。
   - Key 校验：当 `provider=openai` 时需 `OPENAI_API_KEY`；当 `provider=gemini` 时需 `GEMINI_API_KEY`（或 `GOOGLE_API_KEY`）。组织未验证使用 OpenAI 将映射为 `ORG_NOT_VERIFIED`。
   - `GET /ai-image/status` → 返回模块状态与最近输出文件路径。
- 策略（Policy）：
  - `GET /policy/region/status` → 返回地区策略评估结果（国家/地区代码、城市、是否允许、连通性诊断、原因）。
  - AI 图像生成接口在通过基本入参校验后，会进行地区策略校验：默认严格对齐 OpenAI 官网“支持国家与地区”名单（运行时动态获取并缓存 24h），其他全部阻止；失败返回：`{"accepted": false, "error_code": "REGION_BLOCKED", "error": "Region not allowed: country=XX ..."}`。若需要覆盖或补充，可通过 `.env` 设置 `OPENAI_ALLOWED_COUNTRIES`（逗号分隔 ISO 代码）与 `OPENAI_BLOCKED_SUBDIVISIONS`。

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
   -F "model=gpt-image-1" \
   -F "api_org_id=org_XXXXXXXX" \
   -F "api_key=sk-xxxxx" \
   -F "images=@C:/path/to/img1.png" \
   -F "images=@C:/path/to/img2.png" \
   -F "images=@C:/path/to/img3.png" \
   http://127.0.0.1:8000/ai-image/edit

 # 使用 Gemini 生成/编辑（按选择最新一张作为输入；需 GEMINI_API_KEY）
 curl -X POST \
   -F "prompt=make it look like watercolor" \
   -F "size=1024x1024" \
   -F "model=gemini-2.5-flash-image" \
   -F "provider=gemini" \
   -F "api_key=YOUR_GEMINI_API_KEY" \
   -F "image=@C:/path/to/local.png" \
   http://127.0.0.1:8000/ai-image/edit
```

## 模块注册中心与依赖
- 应用在启动时创建 `ModuleRegistry` 并注册：`spatial_mapping`、`projector_calibration`。
- 路由通过依赖注入（`Depends(get_registry)`) 获取注册中心并调用模块的 `configure()/start()/stop()/status()`。

更新记录：
- 2025-11-21：AI 图像生成统一保存策略（全部上传均保存，文件名唯一），并按提供者限制上传数量（OpenAI=1；Gemini-3-Pro-Image-Preview=14；Gemini-2.5=16）；超限返回 `TOO_MANY_IMAGES`。
- 2025-11-21：AI 图像生成接口新增 Gemini 3 Pro Image（`gemini-3-pro-image-preview`）支持，并增加 `aspect_ratio` 与 `image_resolution` 字段校验；UI 联动输入控件与后端参数保持一致。
- 2025-11-21：AI 图像生成支持双提供者（OpenAI/Gemini），新增 `provider` 字段与 Gemini Key 校验；地区策略按提供者使用对应白名单；新增 Gemini 示例调用。
 - 2025-11-20：新增政策路由 `/policy/region/status` 并在 AI 路由接入地区策略校验（hybrid）；默认严格白名单（官方列表动态获取），VPN 以出口 IP 定位为准。
 - 2025-11-20：格式化与导入顺序统一（black/isort），不涉及业务逻辑；确保本地与 CI 风格检查一致通过。
 - 2025-11-19：风格维护（imports 排序与格式统一），修复 CI isort/black 提示；不涉及业务改动。
 - 2025-11-19：补充表单上传依赖说明（`python-multipart`）。
 - 2025-11-10：风格维护（imports 排序与格式统一），修复 CI 提示的 isort/black 问题；不涉及业务改动。
 - 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
 - 2025-11-05：映射/标定路由接入模块包装类；新增示例请求体与 PowerShell 调用示例。
 - 2025-11-05：新增根路径 `/` 跳转至 `/docs`，解决首页访问无法看到接口文档的问题。