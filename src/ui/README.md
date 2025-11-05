# 用户界面（ui）

此目录包含 PyQt6 应用入口与基础窗口：
- `app.py`：主窗口，包含“空间映射”与“投影标定”标签页。

运行示例：
```powershell
python .\src\ui\app.py
```

使用说明：
- 先启动后端 API 服务：`python -m uvicorn src.server.main:app --reload`。
- UI 按钮通过 HTTP 调用后端端点：
  - “开始映射/停止映射”分别对应 `POST /mapping/start` 与 `POST /mapping/stop`；
  - “开始标定”对应 `POST /calibration/run`；状态信息将在标签页标题处更新。

更新记录：
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
- 2025-11-05：UI 按钮已接入后端 HTTP 端点，需先启动 API 服务。