# 投影标定模块（Projector-Calibration）

封装现有 `Projector-Calibration/calibrate_optimized.py`，通过子进程方式启动，保留原流程。

 后续将通过后端API与UI触发该模块。

更新记录：
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
- 2025-11-05：新增配置类 `ProjectorCalibrationSettings`，路由 `POST /calibration/run` 会通过 `configure()/start()` 传入 `proj_height/proj_width/rounds` 参数；`GET /calibration/result` 暂返回占位信息，后续解析输出文件。