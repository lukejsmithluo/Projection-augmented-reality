# 项目规则（统一架构与流程规范）

本文档用于约束项目整体架构、模块化设计、OOP规范、依赖与环境、测试与CI/CD、文档与变更管理等，确保后续新增功能遵循既定方式且不破坏现有框架。

## 1. 架构总则
- 采用模块化分层：`src/common`（基础设施）+ `src/modules`（功能模块）+ `src/server`（FastAPI）+ `src/ui`（PyQt6）+ `tests`（Pytest）。
- 每个模块以“多类协作”的方式实现功能，不允许单类巨石；模块需实现统一的对外接口契约（见第2节）。
- 现有已完成部分作为模块纳入：
  - `Pre-scanned point cloud` → 统一封装为 `SpatialMappingModule`（保留原实现与运行方式）。
  - `Projector-Calibration` → 统一封装为 `ProjectorCalibrationModule`（保留原实现与运行方式）。
- 不重复造轮子：已有能力优先在既有模块扩展；确需新模块时先评估是否可写进现有类或子系统。

## 2. 模块接口契约（OOP规范）
- 抽象基类：`ModuleBase`（位于 `src/common/module_base.py`）。
  - 必需方法：
    - `configure(config: BaseSettings)`：加载模块配置。
    - `start()` / `stop()`：生命周期管理。
    - `status() -> dict`：返回模块运行状态。
    - `get_routes() -> APIRouter | list[APIRouter]`：提供对外API路由（如有）。
  - 可选：`on_event(event: BaseModel)` 用于进程内事件总线。
- 注册中心：`ModuleRegistry`（位于 `src/common/registry.py`），负责模块注册、依赖解析与统一生命周期调用。
- 面向对象要求：封装（私有成员与清晰接口）、继承（抽象基类与策略扩展）、多态（不同设备/策略/数据源可互换）。

## 3. 目录与文件规范
- 统一目录结构（顶层已有文件保持不变，新增按下列规范）：
  - `src/common/`：配置、日志、事件、类型、模块基类与注册中心。
  - `src/modules/<module_name>/`：模块实现；内部包含若干类（服务/控制器/导出器/适配器等）。
  - `src/server/`：FastAPI 应用入口与路由、依赖注入、Schema。
  - `src/ui/`：PyQt6 应用入口、窗口、控件、服务（与后端交互）。
  - `tests/`：按 common/modules/server 分目录组织测试。
- Debug/Test/Temp 文件：必须在对应子目录下，禁止创建在项目根目录；文件名以 `debug_`、`test_`、`temp_` 开头，并在首行注明文件类型注释；使用完必须清理。
- 命名与风格：Python 采用 PEP8；枚举/常量使用大写下划线；类名使用 `PascalCase`；函数/变量使用 `snake_case`。

## 4. 依赖与环境
- Python 版本：3.10+。
- 后端：`fastapi`、`uvicorn[standard]`、`pydantic`。
- UI：`PyQt6`。
- 测试：`pytest`、`pytest-cov`、`requests`（API测试）。
- 代码质量（可选）：`ruff` 或 `flake8`，`black`，`isort`。
- 硬件/SDK：`pyzed`（ZED 2i，SDK 5.1.0），仅在模块内部引用；CI 中跳过硬件测试。
- 依赖检查：新增库前使用 `python -m pip list` 检查是否已存在；名称不确定时需上网核对官方名称并用 `pip list` 进一步确认。
- Windows PowerShell：命令分隔使用分号 `;`（不使用 `&&`）。

## 5. 运行规则与平台约束
- Pre-scanned point cloud 模块：运行 `spatial_mapping.py` 必须使用虚拟环境（`zed_env`）。
  - 示例：在 `Pre-scanned point cloud/src/` 中运行：`..\zed_env\Scripts\python.exe spatial_mapping.py`。
- 禁止模拟（mock）硬件调试：调试需在真实环境进行。
- 与 Unreal 对接：默认坐标单位为厘米；如使用米，导入 Unreal 时需统一缩放100倍。

## 6. 后端 API 规范
- 路由组织：每个模块提供独立 `APIRouter`，注册到 `FastAPI` 应用。
- 示例接口（建议）：
  - 映射：`POST /mapping/start`，`POST /mapping/stop`，`GET /mapping/status`。
  - 标定：`POST /calibration/run`，`GET /calibration/result`。
- Schema：请求/响应模型使用 `pydantic`，放置于 `server/api/schemas/`。
- 依赖注入：通过 `server/api/deps.py` 提供模块实例与配置。

## 7. PyQt6 UI 规范
- 主窗口使用 Tab 分模块：空间映射、投影标定等。
- 与后端通信：优先使用 HTTP（便于跨进程与部署）；本地模式可使用事件总线以提升性能。
- 可视化与GGUI：涉及 Taichi 可视化时使用 GGUI，不使用内置 GUI。

## 8. 测试与质量保障
- 测试分层：
  - 单元测试：`tests/common`、`tests/modules`、`tests/server`。
  - API 测试：使用 FastAPI `TestClient`。
- 硬件相关测试标记：`@pytest.mark.hardware`；CI 中运行 `-m "not hardware"` 跳过硬件测试。
- 本地提交前运行：`python -m pytest -m "not hardware"`，失败则阻止提交（见第9节）。
- 测试范围策略：修改过的代码优先添加或更新对应测试；发现同类问题需要一次性修复与补测，不得“挤牙膏”。

## 9. CI/CD 规则
- 本地 pre-commit 钩子：
  - 安装：`python -m pip install pre-commit; pre-commit install`。
  - Hook：在 `.pre-commit-config.yaml` 中配置 `entry: python -m pytest -m "not hardware"`，`pass_filenames: false`；失败阻止 `git commit`。
- 远端 GitHub Actions：
  - 触发：`push`/`pull_request`。
  - 步骤：安装 Python 3.10；安装依赖；运行 `pytest -m "not hardware" --maxfail=1 --disable-warnings -q`；可选增加 `ruff/black/isort` 检查。
- 不得在 CI 中运行需要真实硬件或GUI交互的测试。

## 10. 文档与变更管理
- 非 Debug/Test/Temp 文件的新增或修改：完成后必须更新该文件所在目录的 `README.md`，说明新增/修改内容与使用方法。
- 新功能实施前需在模块 `README.md` 中增加用途说明与接口约定；实施后同步更新。
- 变更日志（可选）：在顶层 `README.md` 或 `CHANGELOG.md` 中记录关键版本与变更。

## 11. 性能与资源
- 空间映射默认参数以性能优先，必要时在 `README.md` 提供“质量优先/性能优先”两套推荐参数。
- 长时间运行需监控内存与GPU占用，避免积累性数据结构未清理（例如 OpenGL 索引缓冲）。
- 纹理/材质保存仅在网格模式下启用；保持 `.obj/.mtl/.png` 输出一致性。

## 12. 安全与异常处理
- 所有对外接口需统一错误返回结构（错误码+信息）。
- 关键流程（启用/停止设备、文件保存、网络连接）必须记录日志并进行异常捕获与清理（释放资源、关闭句柄）。

## 13. 版本与发布
- 版本号策略（可选）：`setuptools_scm` 或 `bump2version`。
- 构建/发布（可选）：生成发行包或内部 artifact；不影响开发目录结构。

## 14. 兼容与平台
- 主要开发平台：Windows 11；命令行为 PowerShell；命令串联使用分号。
- 图形/渲染：OpenGL 3.3+；如引入 Taichi，可视化使用 GGUI。

## 15. 迁移与集成原则
- 迁入的现有模块需保持原有运行路径与依赖习惯，同时在外部增加薄包装类以接入统一框架与API/UI。
- 接口调用尽量通过模块对外接口而非直接调用核心内部类，确保模块边界清晰。

## 16. 特别强制规则（Must）
1) 在运行 `Pre-scanned point cloud/src/spatial_mapping.py` 时，必须使用虚拟环境运行程序（`zed_env`）。
2) 禁止使用 mock 方式进行硬件调试，需在真实环境验证。
3) Debug/Test/Temp 类型文件不得创建在项目根目录，且需在使用完后及时清理；文件名必须带前缀并在首行注明类型注释。
4) 任何非 Debug/Test/Temp 文件的新增或修改，必须同步更新本目录 `README.md` 文档。
5) 发生过代码修改后，优先运行代码验证可正常工作；随后更新对应文档。
6) 同类问题修复需一次性排查并修复，不得分散或延期（避免“挤牙膏”）。
7) PowerShell 命令不使用 `&&`，统一使用 `;` 分隔。
8) 新增或使用第三方库前，必须用 `python -m pip list` 检查；名称不确定需上网核对并再次确认。

—— 以上规则自合并之日起生效；新增需求与实现必须遵循本规则，以确保不破坏既有框架与接口契约。