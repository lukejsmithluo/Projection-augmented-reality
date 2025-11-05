# 公共基础设施（common）

此目录包含：
- `module_base.py`：模块抽象基类，统一生命周期与接口契约。
- `registry.py`：模块注册中心，统一管理模块实例。
- `config.py`：应用配置（`.env`支持）。
- `logging.py`：日志初始化。
- `events.py`：进程内事件总线（异步）。
- `types.py`：通用类型与枚举。

 遵循项目规则：新增/修改后需同步更新文档。

更新记录：
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。