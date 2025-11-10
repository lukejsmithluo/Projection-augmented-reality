# [Script] GitHub CI 状态查询脚本（直接运行查看最近结果）
# 类型：Simple（使用完可删除）
# 用途：在本地终端快速查询 GitHub Actions 最近的工作流运行状态并输出摘要。
# 说明：支持自定义仓库与打开最新一次运行详情页；私有仓库可通过环境变量 GH_TOKEN 访问。

param(
    [string]$Owner = "lukejsmithluo",
    [string]$Repo = "Projection-augmented-reality",
    [int]$PerPage = 5,
    [switch]$OpenLatest,
    [string]$Branch = ""
)

$ErrorActionPreference = "Stop"

function Get-Headers {
    $headers = @{ 'Accept' = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28'; 'User-Agent' = 'Trae-CI-Status' }
    if ($env:GH_TOKEN -and $env:GH_TOKEN.Trim().Length -gt 0) {
        $headers['Authorization'] = "Bearer $($env:GH_TOKEN)"
    }
    return $headers
}

function Get-Runs {
    param([string]$Owner, [string]$Repo, [int]$PerPage, [string]$Branch)
    $base = ('{0}/{1}/{2}/{3}' -f 'https://api.github.com','repos',$Owner,$Repo) + '/actions/runs'
    $url = $base + '?per_page=' + $PerPage
    if ($Branch -and $Branch.Trim().Length -gt 0) { $url += '&branch=' + $Branch }
    Write-Host "[Debug] Request URL: $url" -ForegroundColor DarkGray
    $headers = Get-Headers
    try {
        return Invoke-RestMethod -Uri $url -Headers $headers
    } catch {
        Write-Host "[Error] Failed to access GitHub API: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

function Show-Table {
    param($WorkflowRuns)
    $WorkflowRuns | Select-Object name, event, status, conclusion, head_branch, head_sha, run_started_at, updated_at, html_url | Format-Table -AutoSize
}

$resp = Get-Runs -Owner $Owner -Repo $Repo -PerPage $PerPage -Branch $Branch
if (-not $resp -or -not $resp.workflow_runs) {
    Write-Host "[Info] No workflow runs found." -ForegroundColor Yellow
    exit 0
}

$runs = $resp.workflow_runs
Show-Table -WorkflowRuns $runs

if ($OpenLatest) {
    $latest = $runs | Sort-Object run_started_at -Descending | Select-Object -First 1
    if ($latest -and $latest.html_url) {
        Write-Host "Opening latest run details: $($latest.html_url)" -ForegroundColor Cyan
        Start-Process $latest.html_url | Out-Null
    }
}