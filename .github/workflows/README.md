# CI 工作流说明（GitHub Actions）

此目录包含项目的持续集成配置（Windows 平台）：
- Python 3.10 环境；
- 安装依赖与风格工具（`ruff`/`black`/`isort`）；
- 运行风格检查（限作用于 `src/`、`tests/`、`scripts/`、`.trae/`）；
- 运行非硬件测试：`pytest -m "not hardware"`。

注意：
- CI 中不运行需要真实硬件或 GUI 交互的测试；
- 若风格检查或测试失败，将阻止合并。
 - 已在 CI 作业级设置 `PYTHONPATH=${{ github.workspace }}`，确保 `tests` 能正确导入 `src.*` 包结构。