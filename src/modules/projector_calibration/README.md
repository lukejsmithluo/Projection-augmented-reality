# 投影标定模块（Projector-Calibration）

本模块实现了基于 Gray Code 结构光的投影仪-相机系统（Pro-Cam）标定功能。
已完全重构为 Python 原生实现，不再依赖外部子进程脚本。

## 功能特性
- **相机参数获取**：自动读取 ZED 2i 相机内参。
- **数据采集**：控制投影仪投射 Gray Code 图案，并控制相机同步采集。
- **系统标定**：基于采集的图像序列，计算投影仪内参及 Pro-Cam 外参。
- **结果输出**：输出 XML 格式标定结果，兼容 OpenCV `FileStorage`。

## 架构
模块内部划分为三个服务：
1. **CameraService**: 负责与 ZED SDK 交互，获取相机参数。
2. **PatternService**: 负责生成 Gray Code 投影图案。
3. **CaptureService**: 负责投影与采集流程控制（OpenCV 窗口显示图案 + ZED 采集）。
4. **CalibrationService**: 负责图像处理与标定算法（Gray Code 解码、角点检测、立体标定）。

## API 接口
模块通过 `src/server/api/routes/calibration_routes.py` 暴露以下 API：
- `GET /calibration/status`: 获取模块状态。
- `POST /calibration/camera/params`: 获取并保存相机参数。
- `POST /calibration/pattern/generate`: 生成 Gray Code 图案序列。
- `POST /calibration/capture/start`: 开启采集会话（打开相机与投影窗口）。
- `POST /calibration/capture/shot`: 采集当前位姿（投射一组图案并拍照）。
- `POST /calibration/capture/stop`: 结束采集会话。
- `POST /calibration/run`: 运行标定算法，返回结果。

## 配置参数
可在 `ProjectorCalibrationSettings` 中配置：
- `proj_height` / `proj_width`: 投影仪分辨率（默认 720p）。
- `monitor_index`: 投影仪所在的显示器索引。
- `chess_vert` / `chess_hori`: 标定板内角点数量。
- `chess_block_size`: 标定板方格物理尺寸（mm）。
- `graycode_step`: Gray Code 条纹步长。
- **输出目录**：
  - 格雷码图案：`data/calibration/patterns`
  - 采集数据：`data/calibration/captures`
  - 相机参数：`data/calibration/camera_config.json`
- **配置文件**：模块内 `config.py` 或通过 API 传递参数。

## 依赖
- `pyzed` (ZED SDK，仅采集时需要)
- `opencv-contrib-python`（需要 `structured_light`，仅采集/生成图案/标定时需要）
- `numpy`（仅采集/生成图案/标定时需要）
- `screeninfo`（仅采集时需要）

说明：
- CI 环境默认不会安装以上“投影标定相关依赖”，以避免引入较大三方库导致流水线变慢或不稳定。
- 因此模块代码已做成“依赖缺失也可被导入”，但当你实际调用采集/图案生成/标定接口时，会在运行时提示缺什么依赖以及安装命令。

## 更新记录
- 2025-12-29: 新增 PatternService 及对应 API，支持在线生成 Gray Code 图案。
- 2025-12-29: 重构模块，集成 `Procam-calibration` 代码，实现原生服务调用与完整 API 支持。
