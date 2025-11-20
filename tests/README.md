# 测试（tests）

- 运行非硬件测试：`python -m pytest -m "not hardware" -q`
- 分层：`tests/common`（基础设施）、`tests/server`（API）。
- CI 中仅运行非硬件测试，跳过需要真实设备或 GUI 的用例。

更新记录：
- 2025-11-20：统一格式化与导入顺序（black/isort），不涉及测试逻辑；确保本地与 CI 风格检查一致通过。