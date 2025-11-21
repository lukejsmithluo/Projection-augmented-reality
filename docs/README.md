# 文档目录（docs）

此目录提供面对用户与开发者的中文使用手册：
- `USER_MANUAL.md`：项目使用手册（快速开始、API/UI、模块运行、常见问题、开发规范）。
- `WEB_API_USAGE.md`：Web API 浏览器交互文档使用指南（在 `/docs` 页面直接调用接口）。

维护约定：新增或修改文档后，需在对应目录的 `README.md` 记录变更。

更新记录：
- 2025-11-21：同步当前开发进度，完善 `USER_MANUAL.md` 与 `WEB_API_USAGE.md`，新增/明确 AI 图像接口的 `model` 与 `api_org_id` 可选字段、错误码 `ORG_NOT_VERIFIED` 说明与示例；与 UI 下拉选择与后端路由改动一致。