# ZED 2i 空间映射程序

## 概述
这是一个基于Stereolabs ZED 2i摄像头的空间映射程序，能够实时生成3D网格或点云数据。该程序展示了如何使用ZED SDK进行环境映射，支持实时3D重建和纹理映射功能。

## 文件结构
```
Pre-scanned point cloud/
├── src/
│   ├── spatial_mapping.py     # 主程序文件
│   └── ogl_viewer/
│       └── viewer.py          # OpenGL渲染器
├── data/                      # 输出数据文件夹
└── README.md                  # 本文档
```

## 功能特性
- 实时空间映射和3D重建
- 支持网格(Mesh)和融合点云(Fused Point Cloud)两种模式
- 实时OpenGL可视化和网格叠加显示
- 支持纹理映射和后处理滤镜
- 自动保存生成的3D数据
- 带时间戳的文件命名避免冲突

## 安装要求
- 获取最新的 [ZED SDK](https://www.stereolabs.com/developers/release/) 和 [pyZED 包](https://www.stereolabs.com/docs/app-development/python/install/)
- 查看 [官方文档](https://www.stereolabs.com/docs/)

## 虚拟环境设置（推荐）

为了避免包版本冲突问题，强烈建议使用虚拟环境运行此程序：

### 方法一：使用现有虚拟环境
项目已包含配置好的虚拟环境 `zed_env`，包含兼容的依赖版本：
- NumPy 1.24.4（与 PyOpenGL-accelerate 3.1.6 兼容）
- ZED SDK 5.1.0 pyzed 库
- PyOpenGL 和 PyOpenGL-accelerate 3.1.10

直接使用虚拟环境运行：
```bash
# 在项目根目录
cd src
..\zed_env\Scripts\python.exe spatial_mapping.py
```

### 方法二：创建新的虚拟环境
如果需要重新创建虚拟环境：
```bash
# 创建虚拟环境
python -m venv zed_env

# 安装依赖
.\zed_env\Scripts\pip.exe install -r requirements.txt

# 手动复制 pyzed 库（如果需要特定版本）
# 从系统 Python 的 site-packages 复制 pyzed 文件夹到虚拟环境
```

## 使用方法

### 基本运行
1. 确保ZED 2i摄像头已连接
2. 在终端中运行程序：
   ```bash
   cd src
   python spatial_mapping.py
   ```

### 高级参数运行
如果您希望从SVO文件回放、指定IP地址或设置分辨率，请使用：

#### 示例命令：
```bash
# 使用HD2K分辨率生成网格
python spatial_mapping.py --resolution HD2K --build_mesh

# 从SVO文件回放并生成点云
python spatial_mapping.py --input_svo_file path/to/file.svo

# 连接到IP摄像头并设置分辨率
python spatial_mapping.py --ip_address 192.168.1.100:2171 --resolution HD1080 --build_mesh

# 完整参数示例
python spatial_mapping.py --input_svo_file <输入svo文件> --ip_address <ip地址> --resolution <分辨率> --build_mesh
```

### 参数说明
- `--input_svo_file`: 现有.svo文件的路径，用于回放。如果未指定此参数和ip_address，软件将默认使用有线连接的摄像头
- `--ip_address`: IP地址，格式为a.b.c.d:port或a.b.c.d。如果指定，软件将尝试连接到该IP
- `--resolution`: 分辨率，可以是HD2K、HD1200、HD1080、HD720、SVGA或VGA
- `--build_mesh`: 指定脚本应该生成网格还是周围环境的点云（带纹理）
 - `--mesh_filter`: 网格过滤级别，可选值：
  - `NONE`: 禁用过滤，保留所有网格数据（推荐用于保留更多细节）
  - `LOW`: 低级过滤，轻微清理噪声
  - `MEDIUM`: 中级过滤（默认值），平衡质量和细节
  - `HIGH`: 高级过滤，大幅减少噪声但可能丢失细节
 - `--units`: 坐标单位选择，支持 `METER` 与 `CENTIMETER`。默认值为 `CENTIMETER`，以便与虚幻引擎（Unreal Engine，单位为厘米）无缝对接。
 - `--mapping_resolution`: 空间映射分辨率预设，可选 `LOW|MEDIUM|HIGH`，默认 `MEDIUM`
 - `--mapping_range`: 空间映射范围预设，可选 `SHORT|MEDIUM|LONG`，默认 `MEDIUM`
 - `--max_memory_usage`: 空间映射最大内存占用（MB），默认 `2048`（保留兼容参数 `--max_memory_mb`，优先使用本参数）

#### 单位与虚幻对接
- 本程序生成的 `.obj` 顶点坐标遵循 `InitParameters.coordinate_units` 设置。
- 默认 `--units CENTIMETER`，导入虚幻后无需额外缩放（1 Unreal 单位 = 1 cm）。
- 若选择 `METER`，请在虚幻导入时将 `Import Uniform Scale` 设置为 `100`，或在导入后将网格缩放为 `100x`，以匹配厘米单位。
- 坐标系使用 `RIGHT_HANDED_Y_UP`（Y向上），虚幻为 `Z` 向上。如出现朝向不一致，可在导入时设置 `Import Rotation` 约 `X=-90°` 进行修正。

**示例**：
```bash
# 默认（推荐）：以厘米为单位输出（虚幻无需缩放）
python spatial_mapping.py --build_mesh --units CENTIMETER

# 以米为单位输出（虚幻导入需缩放100倍）
python spatial_mapping.py --build_mesh --units METER
```

### ⚠️ 重要说明：纹理文件生成
**如果您需要生成材质(.mtl)和纹理(.png)文件，必须使用 `--build_mesh` 参数！**

- **网格模式**（使用 `--build_mesh`）：
  - 生成文件：`mesh_YYYYMMDD_HHMMSS.obj`、`.mtl`、`.png`
  - 支持纹理映射和材质信息
  - 适用于需要完整3D模型的应用

- **点云模式**（不使用 `--build_mesh`）：
  - 生成文件：`pointcloud_YYYYMMDD_HHMMSS.obj`
  - 仅包含几何点数据，无纹理支持
  - 适用于点云分析和简单几何重建

**示例命令**：
```bash
# 生成带纹理的网格文件（推荐）
python spatial_mapping.py --build_mesh --save_texture

# 生成网格文件并禁用过滤（保留更多细节）
python spatial_mapping.py --build_mesh --save_texture --mesh_filter NONE

# 使用高级过滤生成更干净的网格
python spatial_mapping.py --build_mesh --save_texture --mesh_filter HIGH

# 控制空间映射分辨率与范围及内存
python spatial_mapping.py --build_mesh --mapping_resolution MEDIUM --mapping_range MEDIUM --max_memory_usage 2048

# 仅生成点云文件
python spatial_mapping.py
```

#### NONE 模式贴图兼容
- 当使用 `--mesh_filter NONE` 且开启 `--save_texture` 时，程序会在内部禁用 `chunk-only` 映射以允许跨块进行纹理烘焙，从而在不进行几何过滤的前提下生成 `.mtl/.png`。
- 此兼容策略不会改变 `LOW/MEDIUM/HIGH` 模式的现有流程，仅在 `NONE` 模式下启用；在极端场景下可能略微增加贴图阶段耗时。
- 示例：`python spatial_mapping.py --build_mesh --save_texture --mesh_filter NONE`

### 操作说明
- 按**空格键**开始/停止映射过程
- 实时网格叠加到图像上
- 可以对网格应用纹理和后处理滤镜
- 停止映射时自动保存最终网格
 - 叠加显示优化：蓝色线框会显示所有可用块（不仅是最近更新的块），更贴近最终导出的模型；若现场性能受影响，可降低采集分辨率或提高 `--update_rate_ms`。

## 输出文件

### 保存位置
所有生成的文件保存在 `data/` 文件夹中

### 文件命名规则
- **网格模式**: `mesh_YYYYMMDD_HHMMSS.obj`
- **点云模式**: `pointcloud_YYYYMMDD_HHMMSS.obj`

### 支持的文件格式
- **`.obj`** - 主要输出格式，包含3D几何数据
- **`.mtl`** - 材质文件（当启用纹理时自动生成）
- **`.png`** - 纹理图像文件（当启用纹理时自动生成）

**注意**: 当使用网格模式且启用纹理时，ZED SDK会自动生成对应的.mtl和.png文件

## 技术规格
- **SDK版本**: Stereolabs ZED SDK 5.1.0
- **Python版本**: 3.10+
- **支持分辨率**: HD720, HD1080, HD1200, HD2K, SVGA, VGA
- **深度模式**: NEURAL_PLUS（默认，性能需求可切换为 NEURAL）
- **渲染**: OpenGL 3.3+
- **空间映射分辨率**: MEDIUM (默认)
- **映射范围**: MEDIUM (默认)
- **最大内存使用**: 2048MB

## 依赖项
- Python 3.10+
- Stereolabs ZED SDK 5.1.0
- pyZED 包
- OpenGL 3.3+
- NumPy
- PyOpenGL

## 已修复问题

### 内存访问违规错误修复 (2025-10-23)
**问题描述**: 在长时间运行空间映射时出现的内存访问违规错误

**根本原因**: 在 `update_fpc` 函数中，索引数组会不断累积而不清空，导致内存越界访问

**解决方案**: 
- 每次更新时清空索引数组，避免累积
- 使用正确的数据类型 (`np.uint32`) 确保与OpenGL兼容
- 直接使用numpy数组传递给OpenGL，避免ctypes转换带来的内存安全问题

**影响**: 现在可以长时间运行空间映射而不会崩溃

**修改文件**: `ogl_viewer/viewer.py` - 修复了 `SubMapObj.update_fpc()` 和 `SubMapObj.update_mesh()` 函数中的内存管理问题

### 输出路径优化 (2025-10-23)
**改进内容**: 
- 将输出文件从根目录移动到专用的`data/`文件夹
- 添加时间戳避免文件名冲突
- 自动创建输出目录
- 改进文件保存状态提示

### 纹理支持增强 (2025-10-23)
**新增功能**:
- 为网格模式启用纹理保存功能
- 自动应用纹理到生成的网格
- 支持.mtl和.png文件的自动生成
- 改进纹理相关的状态输出

## 使用注意事项
- 确保有足够的存储空间用于保存3D数据
- 建议在良好光照条件下使用以获得最佳纹理效果
- 长时间映射可能生成较大的文件
- 纹理功能仅在网格模式下可用，点云模式不支持纹理
- 确保ZED 2i摄像头固件为最新版本

## 故障排除
- 如果程序无法启动，请检查ZED SDK是否正确安装
- 如果出现OpenGL错误，请更新显卡驱动程序
- 如果保存失败，请检查data文件夹的写入权限
 - 如果在按下空格开始空间映射时出现：`Cannot use Spatial mapping: Positional tracking not enabled` 或提示定位状态不是 `OK`，说明在启用空间映射前定位跟踪未处于有效状态。现版本脚本在开始映射前会自动重新启用并重置定位跟踪，并进行约 3 秒的预热抓帧与状态轮询（必须达到 `OK` 才启用映射）；若仍非 `OK` 则跳过本次启用并提示。建议：
   - 按空格前将相机对准有纹理/几何特征的区域，略微移动相机至日志出现 `OK`（不依赖 `SEARCHING FLOOR PLANE`）
   - 观察日志：`Positional tracking reset` 和后续 `Tracking state: OK` 是否出现
   - 若使用 SVO/网络流，确认流支持定位跟踪（必要时确保 IMU/位姿信息或使用特征丰富的视频源）

## 技术支持
如果您需要帮助，请访问我们的社区网站：https://community.stereolabs.com/

## 相关链接
- [ZED SDK 官方文档](https://www.stereolabs.com/docs/)
- [ZED SDK Python API](https://www.stereolabs.com/docs/api/python/)
- [空间映射 API 使用指南](https://www.stereolabs.com/docs/spatial-mapping/using-mapping/)
### 与官方示例对齐的改动
- 取消 `set_floor_as_origin=True`，避免定位状态长期停留在 `SEARCHING FLOOR PLANE` 导致映射启用失败。
- 启用映射前等待定位跟踪状态为 `OK`，与官方示例在时序上的隐含前提保持一致（示例未设置地面为原点，因此更快进入 `OK`）。