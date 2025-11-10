# 脚本说明（scripts）

此目录包含辅助开发的本地脚本。

## 文件列表
- `dev.ps1`：开发环境便捷命令集合。
- `ci_status.ps1`：GitHub Actions CI 状态查询脚本（直接运行即可查看最近结果）。

## 使用方法
### 查询 GitHub Actions 最近运行结果
```powershell
# 默认查询 lukejsmithluo/Projection-augmented-reality 仓库最近 5 次
powershell -ExecutionPolicy Bypass -File scripts/ci_status.ps1

# 打开最新一次运行的详情页
powershell -ExecutionPolicy Bypass -File scripts/ci_status.ps1 -OpenLatest

# 指定仓库与分支
powershell -ExecutionPolicy Bypass -File scripts/ci_status.ps1 -Owner "<owner>" -Repo "<repo>" -Branch "main" -PerPage 10

# 访问私有仓库：设置环境变量 GH_TOKEN
$env:GH_TOKEN = "<your_personal_access_token>"
powershell -ExecutionPolicy Bypass -File scripts/ci_status.ps1
```

## 说明
- 脚本使用 GitHub REST API，无需登录即可查询公共仓库；私有仓库需设置 `GH_TOKEN`。
- 输出包括：名称、事件、状态、结论、分支、提交、开始与结束时间以及详情链接。
- Windows 环境建议使用 `-ExecutionPolicy Bypass` 运行以避免策略阻拦。

## 维护记录
- 2025-11-10：新增 `ci_status.ps1` 用于在本地直接查看 CI 状态；不影响业务逻辑。