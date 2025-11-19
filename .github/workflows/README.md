# CI 工作流说明（GitHub Actions）

此目录包含项目的持续集成配置（Windows 平台）：
- Python 3.10 环境；
- 安装依赖与风格工具（`ruff`/`black`/`isort`）；
- 运行风格检查（限作用于 `src/`、`tests/`、`scripts/`、`.trae/`；`isort` 使用 `--profile black` 与 `black` 保持一致）；
- 运行非硬件测试：`pytest -m "not hardware"`。

额外依赖说明：
- 已在 CI 安装步骤中加入 `python -m pip install openai`，用于 AI 图像模块在测试收集阶段避免缺库的导入错误（即使不真实调用 OpenAI 也能顺利完成测试）。
 - `isort` 已与 `black` 对齐为 `--profile black`，避免两者格式风格冲突导致 CI 报错。

注意：
- CI 中不运行需要真实硬件或 GUI 交互的测试；
- 若风格检查或测试失败，将阻止合并。
 - 已在 CI 作业级设置 `PYTHONPATH=${{ github.workspace }}`，确保 `tests` 能正确导入 `src.*` 包结构。