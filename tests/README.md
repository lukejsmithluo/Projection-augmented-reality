# 测试（tests）

- 运行非硬件测试：`python -m pytest -m "not hardware" -q`
- 分层：`tests/common`（基础设施）、`tests/server`（API）。
- CI 中仅运行非硬件测试，跳过需要真实设备或 GUI 的用例。