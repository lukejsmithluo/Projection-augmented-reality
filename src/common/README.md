# 公共基础设施（common）

此目录包含：
- `module_base.py`：模块抽象基类，统一生命周期与接口契约。
- `registry.py`：模块注册中心，统一管理模块实例。
- `config.py`：应用配置（`.env`支持）。
- `logging.py`：日志初始化。
- `events.py`：进程内事件总线（异步）。
- `types.py`：通用类型与枚举。
 - `policy/region_policy.py`：地区策略服务（provider-aware，hybrid）；按提供者（OpenAI/Gemini）分别动态获取“官方支持国家与地区名单”（缓存24h），基于出口 IP 地理定位严格白名单放行；支持环境变量覆盖与连通性诊断（不参与放行）。

 遵循项目规则：新增/修改后需同步更新文档。

更新记录：
- 2025-11-21：`region_policy.py` 升级为按提供者（OpenAI/Gemini）切换白名单；AI 路由在生成前将根据所选提供者进行地区合规校验。
- 2025-11-20：格式化与导入顺序统一（black/isort），不涉及业务逻辑变更；确保本地与 CI 风格检查一致通过。
- 2025-11-20：新增 `policy/region_policy.py` 与 `OpenAIRegionPolicySettings`，用于在调用 OpenAI API 前进行地区合规校验；默认模式 `hybrid`（严格白名单），并对齐官方支持国家与地区（动态获取）。
- 2025-11-05：启用风格检查（ruff/black/isort）；本目录 Python 文件已按规则格式化，未改变业务逻辑。