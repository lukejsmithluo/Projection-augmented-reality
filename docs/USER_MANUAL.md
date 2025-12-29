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

## UI 使用指南

本项目的用户界面（`src/ui/app.py`）采用 PyQt6 构建，提供向导式的操作流程。以下是详细的使用说明。

### 1. 启动 UI
确保后端服务已在运行（见“快速开始”），然后在终端执行：
```powershell
python .\src\ui\app.py
```
启动后将出现主窗口，包含三个标签页：“空间映射”、“投影标定”和“AI图像生成”。

### 2. 空间映射 (Spatial Mapping)
用于控制 ZED 相机的空间扫描功能。
- **界面元素**：
  - **状态栏**：显示当前映射状态或错误信息（支持复制）。
  - **开始映射**：点击后后端将调用 ZED SDK 开始扫描空间，构建网格（Mesh）与纹理。
  - **停止映射**：点击后结束扫描，后端自动保存 `.obj`, `.mtl`, `.png` 文件。
- **操作流程**：
  1. 确保 ZED 相机连接正常。
  2. 点击“开始映射”，并在控制台观察日志或通过物理移动相机进行扫描。
  3. 扫描完成后点击“停止映射”，结果将保存至 `Pre-scanned point cloud/data/`。

### 3. 投影标定 (Projector Calibration)
提供完整的 Pro-Cam 系统标定流程，分为四个步骤：

#### 步骤 1: 生成图案 (Pattern Generation)
生成用于结构光编码的 Gray Code 图案序列。
- **配置**：
  - `Projector Width/Height`：投影仪分辨率（默认 1280x720）。
  - `Graycode Step`：条纹步长（默认 1）。
- **操作**：点击 **"Generate Patterns"**。
- **结果**：图案生成至 `data/calibration/patterns`。成功后会自动同步分辨率设置到后续步骤。

#### 步骤 2: 相机设置 (Camera Setup)
获取并保存 ZED 相机的内参。
- **操作**：点击 **"Get & Save Camera Params (ZED)"**。
- **结果**：相机参数保存至 `data/calibration/camera_config.json`。

#### 步骤 3: 数据采集 (Data Capture)
控制投影仪投射图案并同步采集图像。
- **配置**：
  - `Projector Width/Height`：应与生成图案时一致。
  - `Monitor Index`：投影仪所在的显示器索引（0为主屏，1为副屏/投影仪）。
- **操作流程**：
  1. 点击 **"Start Session"**：将打开全屏投影窗口显示白色背景。
  2. **调整位置**：将标定板放置在投影与相机视野重叠区域。
  3. 点击 **"Capture Shot"**：系统将自动投射一系列 Gray Code 图案并拍照。
  4. **重复**：移动标定板到不同角度/位置，重复点击 "Capture Shot"（建议采集 10-15 组）。
  5. 点击 **"Stop Session"**：关闭投影窗口，结束采集。
- **数据**：采集的图片保存在 `data/calibration/captures`。

#### 步骤 4: 标定计算 (Calibration)
基于采集的数据计算投影仪内参及系统外参。
- **配置**：
  - `Chessboard Rows/Cols`：标定板**内角点**数量（非格子数，例如 7x10 的格子通常是 6x9 的内角点）。
  - `Block Size`：单个方格的物理边长（单位：mm）。
- **操作**：点击 **"Run Calibration"**。
- **结果**：
  - 界面文本框显示 RMS 误差、相机内参矩阵、投影仪内参矩阵。
  - 详细结果保存为 XML 文件。

### 4. AI 图像生成 (AI Image Generation)
利用 AI 模型对现有图片进行编辑或重绘。

#### 图片选择与预览
- **添加图片**：点击预览区最右侧的 **"＋"** 号，选择本地图片。
- **多图管理**：支持多选，预览区按“左旧右新”排列，最多显示 3 张缩略图（可横向滚动）。
- **移除图片**：点击缩略图右上角的 **"－"** 移除单张，或点击左侧 **"×"** 清空所有。
- **生成输入**：系统默认使用**最近一次选择**（最右侧）的图片作为 AI 输入。

#### 参数配置
- **Prompt**：输入提示词（英文），描述你想要的修改效果（如 "make it cyberpunk style"）。
- **Model**：下拉选择模型（默认为 `gpt-image-1` 或 Gemini 系列）。
  - **OpenAI (`gpt-image-1`)**：需设置 `Size`（支持 256x256, 512x512, 1024x1024）。
  - **Gemini (`gemini-2.5-flash-image` 等)**：需设置 `Aspect Ratio`（宽高比）和 `Resolution`（分辨率）。
- **API Key & Org ID**：
  - 可在界面直接输入 API Key（右侧按钮切换显示/隐藏）。
  - OpenAI 可选输入 Organization ID。
  - 也可通环境变量配置。

#### 地区策略与状态
- **地区状态**：顶部显示当前网络环境的地区检测结果（是否允许访问 AI 服务）。
- **刷新**：点击 **"刷新地区状态"** 更新检测结果。
- **复制**：支持一键复制状态文本，便于排查网络问题。

#### 生成与结果
- **生成**：点击 **"Generate Image"**。
- **结果预览**：生成成功后，右侧大图区域将显示结果。
- **历史查看**：点击 **"预览最新输出"** 可直接加载最近一次生成的文件。
- **文件位置**：输出保存在 `data/ai_images/outputs`。

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