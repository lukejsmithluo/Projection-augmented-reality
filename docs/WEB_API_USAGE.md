# Web API 使用指南

本文档介绍如何在浏览器的 Swagger UI（`/docs`）与命令行中调用项目后端 API，内容与当前开发进度保持同步。

## 打开交互文档（Swagger UI）
- 启动后端后访问 `http://127.0.0.1:8000/docs`。
- 每个模块提供独立的路由分组；点击相应分组即可展开端点与入参说明。

## 映射（Mapping）
- `POST /mapping/start`：设置是否构建网格与保存纹理；返回是否接受。
- `POST /mapping/stop`：停止并返回保存文件列表。
- `GET /mapping/status`：返回当前状态（RUNNING/IDLE 等）。

## 投影标定（Calibration）
- `POST /calibration/run`：填写投影分辨率与轮次；返回是否接受。
- `GET /calibration/result`：返回标定结果或占位信息。

## AI 图像生成（AI Image Generation）
- 交互步骤（`POST /ai-image/edit`）：
  1. 在“请求体”切换为 `multipart/form-data`。
  2. 填写 `prompt` 与上传图片（单图字段 `image` 或多图字段 `images[]`）。
  3. 可选字段：
     - `size`（默认 `1024x1024`；支持 `256x256`、`512x512` 等）。
     - `model`（默认 `gpt-image-1`；仅图像生成模型）。
     - `api_key`（若提供将覆盖当前进程环境变量）。
     - `api_org_id`（显式组织 ID，覆盖环境变量 `OPENAI_ORG_ID`）。
  4. 点击“Execute”执行；成功返回输出文件路径：`{"accepted": true, "output_file": "data/ai_images/outputs/gen_YYYYmmdd_HHMMSS.png"}`。
  5. 常见错误：
     - 未配置 API Key：`{"accepted": false, "error_code": "NO_API_KEY"}`。
     - 组织未验证导致 403：`{"accepted": false, "error_code": "ORG_NOT_VERIFIED"}`。
- `GET /ai-image/status`：返回模块状态与最近输出文件。

### cURL 示例（PowerShell）
```powershell
curl -X POST http://127.0.0.1:8000/ai-image/edit \
  -F "prompt=make it look like watercolor" \
  -F "size=1024x1024" \
  -F "model=gpt-image-1" \
  -F "api_org_id=org_XXXXXXXX" \
  -F "api_key=sk-xxxxx" \
  -F "images=@C:/path/to/img1.png" \
  -F "images=@C:/path/to/img2.png"
```

## 地区策略（Policy）
- `GET /policy/region/status`：返回国家/地区代码、城市、是否允许、连通性诊断与原因；AI 图像生成在基本入参校验后将进行地区策略校验并严格对齐 OpenAI 官方支持列表（运行时动态获取并缓存 24h）。
- 若地区不在白名单，返回：`{"accepted": false, "error_code": "REGION_BLOCKED"}`。

更新记录：
- 2025-11-21：补充 AI 图像接口的 `model` 与 `api_org_id` 可选字段，新增 cURL 示例与错误码 `ORG_NOT_VERIFIED` 说明；与 UI/后端当前进度对齐。