# 项目使用手册（用户手册）

本文档面向最终用户与开发者，介绍项目的快速开始、模块功能、UI 使用方法与常见问题。内容与当前开发进度保持同步。

## 快速开始
- 环境要求：Windows 11；Python 3.10+；建议使用虚拟环境。
- 安装依赖（PowerShell）：
  ```powershell
  python -m pip install -r requirements.txt
  ```
- 启动后端 API：
  ```powershell
  python -m uvicorn src.server.main:app --reload
  ```
- 启动 UI：
  ```powershell
  python .\src\ui\app.py
  ```

## 模块概览
- 空间映射（SpatialMappingModule）：提供开始/停止与状态查询，输出 `.obj/.mtl/.png`。
- 投影标定（ProjectorCalibrationModule）：提供标定运行与结果查询。
- AI 图像生成（AIImageGenerationModule）：支持上传图片与提示词进行图像编辑；默认模型为 `gpt-image-1`；支持 `size`、`model`、`api_org_id`、`api_key` 等可选字段。

## UI 使用
- 主窗口包含“空间映射”、“投影标定”、“AI图像生成”标签页；所有操作通过 HTTP 调用后端 API 执行；本地模式内部已禁用代理以保证直连本地服务。
- AI 图像生成页：
  - 支持多图选择并预览缩略图（右到左顺序；最新在右）；默认使用最近一次选择的图片作为生成输入。
  - 预览容器为 16:9 框（约 640x360），最多显示 3 张；提供横向滑条浏览与“清空已选图片”按钮。
  - 支持“预览最新输出”直接显示 `data/ai_images/outputs` 中最近生成的图片；无需再次提交生成请求。
  - 输入项：提示词 `prompt`、尺寸 `size`（默认 `1024x1024`）、模型下拉 `model`（仅包含图像生成模型 `gpt-image-1`）、`OpenAI Org ID`（可选）、`OpenAI API Key`（可选）。填写的 `model` 与 `api_org_id` 会随请求一并传递到后端。
  - 注意：聊天/文本模型（如 GPT‑5/4 及其版本）不适用于图像编辑接口；请保持 `model=gpt-image-1`。
- 地区策略展示与刷新：通过 `GET /policy/region/status` 显示国家/地区代码、城市、是否允许、连通性诊断与原因；仅当地区允许时，OpenAI 相关能力才可调用成功（VPN 以出口 IP 定位为准）。
- API 基础地址可通过环境变量 `API_BASE_URL` 配置（默认 `http://127.0.0.1:8000`）。

## 后端 API 概览
- 映射（Mapping）：
  - `POST /mapping/start` → `{"build_mesh": true, "save_texture": true}`；返回 `{"accepted": true}`。
  - `POST /mapping/stop` → 返回保存的文件列表。
  - `GET /mapping/status` → 返回模块状态。
- 标定（Calibration）：
  - `POST /calibration/run` → `{"proj_height":1080,"proj_width":1920,"rounds":1}`；返回 `{"accepted": true}`。
  - `GET /calibration/result` → 返回标定结果或占位信息。
- AI 图像生成（AI Image Generation）：
  - `POST /ai-image/edit`（multipart）：字段 `prompt`、`image`/`images[]`；可选 `size`（默认 `1024x1024`）、`model`（默认 `gpt-image-1`）、`api_key`、`api_org_id`。成功返回：`{"accepted": true, "output_file": "data/ai_images/outputs/gen_YYYYmmdd_HHMMSS.png"}`。
  - `GET /ai-image/status` → 返回模块状态与最近输出文件路径。
- 策略（Policy）：
  - `GET /policy/region/status` → 返回地区策略评估结果；默认严格对齐 OpenAI 官方支持国家/地区名单（运行时动态获取并缓存 24h），其他全部阻止。

## 常见问题（FAQ）
- 403 错误且提示 `ORG_NOT_VERIFIED`：OpenAI 组织未验证。请完成组织验证或使用具有权限的 API Key；也可在请求中显式传入 `api_org_id` 或通过环境变量 `OPENAI_ORG_ID` 指定组织。
- 选择了非图像模型：AI 图像编辑接口不支持聊天/文本模型（GPT‑5/4/3.5 等）；请使用 `gpt-image-1`。
- 地区被阻止：请检查 VPN 出口 IP 所在国家/地区是否在官方支持名单；必要时调整网络设置或白名单覆盖（谨慎使用）。

更新记录：
- 2025-11-21：新增并同步当前进度的 UI 使用与 AI 图像接口说明，包含模型下拉与组织 ID 输入；补充 403 → `ORG_NOT_VERIFIED` 错误映射说明。