# 预扫描点云模块（Pre-scanned point cloud）

封装现有 `Pre-scanned point cloud/src/spatial_mapping.py`，通过子进程方式启动，遵循：
- 必须使用虚拟环境 `zed_env` 运行。
- 保留原有参数与输出行为。

 后续将通过后端API与UI触发该模块。

更新记录：
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。
- 2025-11-05：新增配置类 `SpatialMappingSettings`，路由 `POST /mapping/start` 会通过 `configure()/start()` 传入 `build_mesh/save_texture` 参数；`POST /mapping/stop` 收集 `data/` 下的 `.obj/.mtl/.png` 输出。