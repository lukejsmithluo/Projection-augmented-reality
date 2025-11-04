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
python spatial_mapping.py --build_mesh

# 生成网格文件并禁用过滤（保留更多细节）
python spatial_mapping.py --build_mesh --mesh_filter NONE

# 使用高级过滤生成更干净的网格
python spatial_mapping.py --build_mesh --mesh_filter HIGH

# 仅生成点云文件
python spatial_mapping.py
```

### 操作说明
- 按**空格键**开始/停止映射过程
- 实时网格叠加到图像上
- 可以对网格应用纹理和后处理滤镜
- 停止映射时自动保存最终网格

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
- **SDK版本**: Stereolabs ZED SDK 5.0.7
- **Python版本**: 3.10+
- **支持分辨率**: HD720, HD1080, HD1200, HD2K, SVGA, VGA
- **深度模式**: NEURAL (默认)
- **渲染**: OpenGL 3.3+
- **空间映射分辨率**: MEDIUM (默认)
- **映射范围**: MEDIUM (默认)
- **最大内存使用**: 2048MB

## 依赖项
- Python 3.10+
- Stereolabs ZED SDK 5.0.7
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

## 技术支持
如果您需要帮助，请访问我们的社区网站：https://community.stereolabs.com/

## 相关链接
- [ZED SDK 官方文档](https://www.stereolabs.com/docs/)
- [ZED SDK Python API](https://www.stereolabs.com/docs/api/python/)
- [空间映射 API 使用指南](https://www.stereolabs.com/docs/spatial-mapping/using-mapping/)