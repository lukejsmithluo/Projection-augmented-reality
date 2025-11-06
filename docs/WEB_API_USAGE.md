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
1) 启动映射（构建网格并保存纹理）：
   - 选择 `POST /mapping/start` → “Try it out” → 在 Request body 输入：
   ```json
   {
     "build_mesh": true,
     "save_texture": true
   }
   ```
   - 点击 “Execute”，返回示例：`{"accepted": true}` 表示已开始。

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