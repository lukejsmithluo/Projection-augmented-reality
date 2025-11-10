# Web API 使用指南（通过浏览器操作 /docs）

本指南面向不熟悉代码的使用者，教你如何在浏览器的 Swagger UI（交互文档）中直接调用项目开放的接口完成空间映射与投影标定。

## 一键启动服务
- 在项目根目录运行：
  - `python main.py`
- 默认启动地址：`http://127.0.0.1:8000`，交互文档：`http://127.0.0.1:8000/docs`
- 可选环境变量：
  - `API_HOST`（默认 `127.0.0.1`）
  - `API_PORT`（默认 `8000`）
  - `API_RELOAD`（默认启用热重载，`0/false` 关闭）

若提示缺少 `uvicorn`，请在终端执行：
```powershell
python -m pip install "uvicorn[standard]"
```

## 打开交互文档
- 在浏览器访问 `http://127.0.0.1:8000/docs`
- 左侧为接口列表，右侧为接口说明与参数。
- 点击某个接口的“Try it out”，填写请求体，再点击“Execute”即可在线请求并查看响应。

## 常用接口操作
### 空间映射（Mapping）
1) 启动映射（支持全部参数配置）：
   - 选择 `POST /mapping/start` → “Try it out” → 在 Request body 输入（按需填写，以下为完整字段及默认值）：
   ```json
   {
     "build_mesh": true,
     "save_texture": true,
     "input_svo_file": "",
     "ip_address": "",
     "resolution": "",
     "mesh_filter": "MEDIUM",
     "units": "CENTIMETER",
     "mapping_resolution": "MEDIUM",
     "mapping_range": "MEDIUM",
     "max_memory_usage": 2048,
     "update_rate_ms": 700,
     "depth_mode": "NEURAL_PLUS"
   }
   ```
   - 点击 “Execute”，返回示例：`{"accepted": true}` 表示已开始。

   字段说明（与 `Pre-scanned point cloud/src/spatial_mapping.py` 一致）：
   - 运行模式：
     - `build_mesh` 启用网格构建；`save_texture` 保存材质与纹理（`.mtl/.png`）。
   - 输入与分辨率（可选其一或都为空）：
     - `input_svo_file` 使用离线 SVO 文件；`ip_address` 连接网络摄像头；`resolution` 指定相机分辨率（不填按设备默认）。
   - 空间映射参数：
     - `mesh_filter`：`NONE|LOW|MEDIUM|HIGH`（默认 `MEDIUM`）。
     - `units`：`METER|CENTIMETER`（默认 `CENTIMETER`，与 Unreal 对接推荐厘米）。
     - `mapping_resolution`：`LOW|MEDIUM|HIGH`（默认 `MEDIUM`）。
     - `mapping_range`：`SHORT|MEDIUM|LONG`（默认 `MEDIUM`）。
     - `max_memory_usage`：最大内存使用（MB，默认 `2048`）。
     - `update_rate_ms`：映射更新周期（毫秒，默认 `700`）。
     - `depth_mode`：`NEURAL|NEURAL_PLUS`（默认 `NEURAL_PLUS`）。

2) 查询状态：
   - 选择 `GET /mapping/status` → “Execute”，返回示例：
   ```json
   { "module": "spatial_mapping", "status": { "state": "RUNNING" } }
   ```

3) 停止并保存产物：
   - 选择 `POST /mapping/stop` → “Execute”，返回示例：
   ```json
   { "saved_files": [".../mesh_YYYYMMDD_HHMMSS.obj", "...mtl", "...png"] }
   ```
   - 产物路径：`Pre-scanned point cloud/data/`（`.obj/.mtl/.png` 三件套）。

使用须知：
- 必须在真实硬件环境运行（ZED 2i 摄像机），且空间映射模块强制使用 `zed_env` 虚拟环境。
- 若相机被其他程序占用（如 ZED Explorer），请先关闭它再启动映射。
 - 在 `mesh_filter` 为 `NONE` 且 `save_texture=true` 时，系统会自动禁用 `chunk-only` 模式以允许跨块纹理烘焙，确保 `.mtl/.png` 正常生成（不影响 `LOW/MEDIUM/HIGH` 模式行为）。

### 投影标定（Calibration）
1) 启动标定（按你的投影仪分辨率）：
   - 选择 `POST /calibration/run` → “Try it out” → 输入：
   ```json
   {
     "proj_width": 1280,
     "proj_height": 720,
     "rounds": 1
   }
   ```
   - 点击 “Execute”，返回示例：`{"accepted": true}`。

2) 查看结果：
   - 选择 `GET /calibration/result` → “Execute”（当前返回占位信息，用于确认流程走通）。

操作建议：
- 标定时保持投影画面与相机视野稳定，避免强反光或过曝；按提示完成拍摄。

## 常见问题与排查
- 打不开 `/docs`：请确认 `main.py` 启动成功，终端无报错，并检查端口占用。
- `ModuleNotFoundError`：服务启动时自动设置了 `PYTHONPATH`；若仍报错，请确认使用的是项目根目录运行 `python main.py`。
- 相机无法打开：关闭占用设备的程序（如 ZED Explorer），检查 USB 线缆与供电稳定性。
- 未生成纹理：确保启动时使用了 `{"build_mesh": true, "save_texture": true}`；场景光照平衡，避免投影图案干扰相机曝光。

## 参考
- 交互文档（Swagger UI）：`http://127.0.0.1:8000/docs`
- 只读文档（ReDoc）：`http://127.0.0.1:8000/redoc`
- OpenAPI 规范：`http://127.0.0.1:8000/openapi.json`