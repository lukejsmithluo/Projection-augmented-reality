# 项目根目录说明

本仓库包含两个主要子模块：
- `Pre-scanned point cloud/`：ZED 2i 空间映射相关代码与虚拟环境
- `procam-calibration/`：投影-相机标定与质量检测工具

## Git忽略策略
 已在根目录配置 `.gitignore`，以确保不会将临时或体积巨大的文件提交到版本库：
- 忽略 `Pre-scanned point cloud/zed_env/` 虚拟环境目录（用户指定）
- 忽略 `procam-calibration/` 下所有以 `capture_` 开头的目录（用户指定），包括子目录中的 `capture_*`，且**递归忽略其所有内容**（已添加 `capture_*/` 与 `capture_*/**` 规则）
 - 忽略 `procam-calibration/graycode_pattern/` 目录及其所有内容（含子目录匹配规则）
- 忽略通用虚拟环境、Python缓存、IDE配置、操作系统隐藏文件等

若某些目录或文件已被提交过版本库，需要执行以下命令从跟踪中移除：
```
# 仅从Git索引中移除，不删除本地文件
git rm -r --cached "Pre-scanned point cloud/zed_env"
git rm -r --cached procam-calibration/capture_*
 git rm -r --cached procam-calibration/graycode_pattern
```

## 路径与匹配说明
- `.gitignore` 使用 **相对路径** 与 **通配符**，在Windows下亦需使用 **正斜杠** `/`
- 通过 `procam-calibration/**/capture_*/` 规则可匹配子目录中所有 `capture_*`

如需新增忽略规则，请在根目录 `.gitignore` 中追加相应条目，避免分散配置导致维护困难。