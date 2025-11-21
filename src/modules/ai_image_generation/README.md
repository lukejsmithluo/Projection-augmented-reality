# AI 图像生成模块（ai_image_generation）

本模块支持双提供者：OpenAI Images API 与 Google Gemini/Imagen。接收上传图片与提示词，生成新图片并保存输出文件。

## 功能
- OpenAI：接入 `OPENAI_API_KEY`，调用 `gpt-image-1` 模型进行图片编辑。
- Gemini：接入 `GEMINI_API_KEY`（或 `GOOGLE_API_KEY`），调用 `gemini-2.5-flash-image` 或 `imagen-*` 模型进行图片生成/编辑（文本+图片）。
- 存储：上传图片保存在 `data/ai_images/uploads/`，输出图片保存在 `data/ai_images/outputs/`。
  - 保存策略：所有上传图片都会被保存，并使用“时间戳+序号”的唯一文件名，避免同名覆盖；生成时以“最新一张”作为实际输入。
- FastAPI 路由：
  - `POST /ai-image/edit`（multipart：`prompt`、`image` 或 `images`（保留左→右顺序）
    - OpenAI：可选 `size`（允许 `256x256/512x512/1024x1024`）
    - Gemini：可选 `aspect_ratio`（允许 `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9`）与 `image_resolution`（允许 `1K/2K/4K`）
    - 通用：可选 `model`、`provider`、`api_key`、`api_org_id`
    ）。当提供 `api_key` 时，后端将临时使用该值作为当前进程的对应提供者的 Key。当前生成以“最新一张”作为实际输入，后续可按需求扩展为序列处理。
  - `GET /ai-image/status`（查看模块状态与最近输出）。

## 配置与环境
- 依赖：
  - OpenAI：`openai` Python 库（按需，运行时懒加载）。缺失库时返回 `OPENAI_LIB_MISSING`。
  - Gemini：`google-genai` 与 `Pillow` 库（运行时懒加载）。缺失库时返回 `GEMINI_LIB_MISSING` 或 `PIL_OR_GEMINI_TYPES_MISSING`。
- 环境变量/`.env`：
  - OpenAI：`OPENAI_API_KEY=sk-xxxxx`；`OPENAI_ORG_ID=org_xxxxx`（可选）
  - Gemini：`GEMINI_API_KEY=xxxxxx`（或 `GOOGLE_API_KEY=xxxxxx`）
- 默认设置（可通过 `AIImageSettings` 调整）：
  - `output_dir`: `data/ai_images`
  - `model`: `gpt-image-1`
  - `default_size`: `1024x1024`
 - 尺寸说明：当前已对 `size` 参数进行规范化，仅支持 `256x256`、`512x512`、`1024x1024`。当传入其它尺寸（如 `1280x720`）时将自动回退到默认值 `1024x1024`，以避免 OpenAI API 返回不支持尺寸的错误。

### 组织验证要求
- 使用 `gpt-image-1` 模型需要组织已通过验证（Verified Organization）。若未验证，OpenAI 会返回 403 错误，提示前往 `https://platform.openai.com/settings/organization/general` 完成验证；验证后通常需要等待约 15 分钟权限才会生效。
- 路由在捕获该情况时会返回错误码：`ORG_NOT_VERIFIED`，并附带说明与链接以便快速处理。
- 可选 `api_org_id`（multipart 表单字段）在调用 `/ai-image/edit` 时传入组织 ID；后端会临时在当前进程中使用该组织 ID（等价于设置 `OPENAI_ORG_ID`）。

### 模型选择
- `/ai-image/edit` 支持可选表单字段 `model` 用于指定生成模型名；未提供时采用配置中的默认模型（`gpt-image-1`）。
- 注意：不同模型的可用性与权限可能受组织/地区/账户计划限制；若无权限或模型名无效，OpenAI 将返回错误（例如 403/404），不会产生成功调用计费。

## 使用示例（PowerShell）
```powershell
# 启动后端服务
python -m uvicorn src.server.main:app --reload
; # 设置 .env 包含 OPENAI_API_KEY
; # 调用 AI 图像编辑接口（multipart）
$filePath = "C:\\path\\to\\local.png"
 # 单图（兼容旧用法）
 $form = @{ prompt = "make it look like watercolor"; size = "1024x1024"; api_key = "sk-xxxxx"; image = Get-Item $filePath }
Invoke-WebRequest -Uri "http://127.0.0.1:8000/ai-image/edit" -Method POST -Form $form

 # 多图（推荐使用 curl 方式上传保持顺序）：
 curl -X POST \
   -F "prompt=make it look like watercolor" \
   -F "size=1024x1024" \
   -F "api_key=sk-xxxxx" \
   -F "api_org_id=org_xxxxx" \
   -F "images=@C:/path/to/img1.png" \
   -F "images=@C:/path/to/img2.png" \
   -F "images=@C:/path/to/img3.png" \
  http://127.0.0.1:8000/ai-image/edit
```

## 上传数量限制（后端强制）
- OpenAI（`gpt-image-1`）：每次请求仅支持 1 张输入图片（与 Images Edit 能力一致）。
- Gemini 3 Pro Image（`gemini-3-pro-image-preview`）：最多 14 张参考图。
- Gemini 2.5（如 `gemini-2.5-flash-image`）：后端默认限制为 16 张（综合考虑令牌/大小开销与稳定性，实际 SDK 能接受更多文件，但高并发场景下易受配额与性能影响）。

超过上限时，路由返回统一错误结构：`{"accepted": false, "error_code": "TOO_MANY_IMAGES", "error": "..."}`。

## 模块结构
- `module.py`：模块包装类（生命周期与状态）。
- `config.py`：模块配置（输出目录、模型名、默认尺寸）。
- `services/openai_service.py`：OpenAI 调用封装与结果保存。
- `services/gemini_service.py`：Gemini/Imagen 调用封装与结果保存。
- `services/storage_service.py`：上传与输出文件存储帮助类。

## 更新记录
- 2025-11-21：保存策略改为“全部上传图片均保存且文件名唯一”；新增上传数量后端限制（OpenAI=1，Gemini-3-Pro-Image-Preview=14，Gemini-2.5=16）。
- 2025-11-21：新增 Gemini 3 Pro Image（`gemini-3-pro-image-preview`）支持；路由增加 `aspect_ratio` 与 `image_resolution` 字段并进行输入校验；模块/服务层将参数传入 `ImageConfig`（1K/2K/4K）。
- 2025-11-21：修复 Gemini 文本/图片输入构造方式，文本使用 `types.Part(text=...)`，图片改为 `types.Part(inline_data=types.Blob(mime_type=..., data=...))` 的内联二进制，并将两者包装为 `types.Content(role="user", parts=[...])` 传入，避免不同 SDK 版本的签名差异导致的 `GENERATION_FAILED`。
- 2025-11-21：新增 Gemini/Imagen 提供者支持；`/ai-image/edit` 新增 `provider` 字段；地区策略按提供者使用对应白名单；UI 默认模型改为 `gemini-2.5-flash-image`。
- 2025-11-20：增强错误处理，未验证组织时返回 `ORG_NOT_VERIFIED` 并提供验证指引；支持 `OPENAI_ORG_ID` 环境变量与 `api_org_id` 表单字段以显式指定组织。
- 2025-11-20：修复调用方法为 `images.edit`（替换错误的 `images.edits`），并对 `size` 参数进行规范化（非支持尺寸自动回退到默认值）以提升稳定性。
- 2025-11-19：风格维护（imports 排序与格式统一），修复 CI isort/black 提示；不改动业务逻辑。
- 2025-11-19：新增 AI 图像生成模块与路由，支持图片编辑与输出保存。
- 2025-11-19：`/ai-image/edit` 支持可选 `api_key` 字段以便在未预置环境变量时即时调用。