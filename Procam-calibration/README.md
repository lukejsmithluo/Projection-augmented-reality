# procam-calibration（本项目改进版）

本目录是一套“用相机标定投影仪”的 Pro-Cam 标定工具：通过灰码（Gray code）建立相机像素与投影仪像素的对应关系，再把投影仪当作“反向相机”做标定与相机-投影仪外参求解，最终输出可用于 Unreal/SLAM/投影校正的参数。

本 README 已按当前工程中的最新实现更新（包含鲁棒性修复、对比运行与可视化输出方式）。

## 1. 设计思路（Why it works）

核心目标：求解
1) 投影仪内参/畸变（把投影仪视作一台“相机”）
2) 相机→投影仪的外参（R、t）

基本思路如下：
1) 在棋盘上投影一组灰码图案，并用相机逐帧拍摄。
2) 对每个棋盘角点，在角点附近的小区域内进行灰码解码，得到若干“相机像素 → 投影仪像素”的稠密对应点。
3) 用局部单应性（homography）把“角点的相机坐标”映射到“角点的投影仪坐标”，从而得到“棋盘 3D 角点 → 投影仪 2D 像素”的对应数据。
4) 用 OpenCV 的 `calibrateCamera` 标定投影仪（等价于标定一台相机）。
5) 用 OpenCV 的 `stereoCalibrate` 联合求解相机与投影仪的外参（相机坐标系到投影仪坐标系的 R、t）。

算法背景：本项目基于 Moreno & Taubin 2012 的 projector-camera 标定思想，在棋盘角点附近用局部单应性提高精度。

## 2. 框架与目录结构（What’s inside）

本目录主要脚本：
* `gen_graycode_imgs.py`：生成灰码图案（含 white/black 参考图）。
* `capture_data.py`：自动化投影与拍摄（支持 ZED / OpenCV 通用相机）。
* `get_zed_params.py`：读取 ZED 相机内参生成 `camera_config.json`。
* `calibrate.py`：标定主程序，输出 `cv::FileStorage` 格式的 XML。
* `calculate_unreal_params.py`：把标定结果转为 Unreal 常用参数（如果你后续要用到）。

数据组织约定：
* 输入目录下包含多个 `capture_*` 子目录（例如 `capture_P5UIST/capture_0`）。
* 每个 `capture_X` 目录内必须包含 `graycode_00.png ... graycode_YY.png`，并且最后两张为 white/black 参考图（顺序与生成方式一致）。

输出约定：
* 标定结果：`calibration_result*.xml`
* 可视化：`visualize_corners_projector_<tag>_capture_X.png`

## 3. 环境依赖（Requirement）

* Python 3.10+（建议与项目统一）
* OpenCV（需要 structured_light 模块）
  * `python -m pip install opencv-python opencv-contrib-python`
* ZED 相机用户：
  * 安装 ZED SDK，并在 Python 环境中可导入 `pyzed`
* 自动投影采集脚本使用屏幕枚举：
  * `python -m pip install screeninfo`

## 4. 快速开始（How to use）

### Step A：生成灰码图案

在本目录运行：

```sh
python gen_graycode_imgs.py <proj_height> <proj_width> -graycode_step 1
```

* `<proj_height> <proj_width>` 必须与你投影仪“实际输出分辨率”一致。
* `graycode_step` 是灰码像素块大小；如果你看到明显摩尔纹或解码不稳定，可以增大（例如 2 或 3），代价是精度上限会下降一点，但整体会更稳。

图案会输出到 `./graycode_pattern/`。

### Step B：投影并采集数据

你可以手动采集，也可以用自动脚本：

```sh
python capture_data.py <proj_height> <proj_width> --monitor <monitor_index>
```

推荐采集策略（非常关键）：
* 尽量关闭相机自动曝光/自动增益（或至少固定曝光），避免灰码序列亮度漂移。
* 让棋盘尽量占据相机画面较大区域，并且棋盘的大部分区域处于投影覆盖范围内。
* 建议采集 10+ 组不同姿态（平移/旋转/距离变化），但不要极端倾斜导致棋盘格严重透视变形或模糊。

采集输出目录形如：
* `./capture_P5UIST/capture_0/graycode_00.png ...`
* `./capture_P5UIST/capture_1/graycode_00.png ...`

### Step C：准备相机内参（可选但强烈建议）

如果你使用 ZED：
```sh
python get_zed_params.py
```

会生成 `camera_config.json`（包含相机内参矩阵 `P` 和畸变 `distortion`）。

然后在标定时用 `-camera camera_config.json` 固定相机内参，用于更稳的初值求解。

### Step D：运行标定（单次运行）

```sh
python calibrate.py <proj_height> <proj_width> <chess_corners_vert> <chess_corners_hori> <chess_block_size> <graycode_step> ^
  -black_thr 40 -white_thr 5 ^
  -input_dir "./capture_P5UIST" ^
  -camera camera_config.json
```

参数说明：
* `chess_corners_vert / chess_corners_hori` 是“角点数量”，不是格子数量（OpenCV 角点定义）。
* `chess_block_size` 是单个格子的物理尺寸（单位自定，但会影响平移向量的单位）。
* `black_thr / white_thr` 影响灰码解码鲁棒性：
  * 终端若频繁出现 `decoded pixels were too few`，通常需要提高 `black_thr/white_thr` 或改进曝光/投影对比度。

结果输出：
* 默认 `calibration_result.xml`
* 同时会输出每视图的投影仪 RMS（用于定位离群视图）
* 会输出可视化图 `visualize_corners_projector_capture_X.png`（或带 tag 的版本）

### Step E：导出 Unreal 参数（可选）

`calculate_unreal_params.py` 用于把 `calibration_result*.xml` 转成 Unreal 常用的镜头参数与 “Projector relative to Camera” 的 Transform。

```sh
python calculate_unreal_params.py --xml calibration_result_after.xml --proj-width 1280 --proj-height 720 --translation-scale 0.1
```

说明：
* `--translation-scale` 用于把标定平移单位转换到 Unreal 常用的厘米（cm）：
  * 若 `chess_block_size` 用的是 mm：用 `0.1`（mm → cm）
  * 若 `chess_block_size` 用的是 cm：用 `1.0`
  * 若 `chess_block_size` 用的是 m：用 `100.0`（m → cm）
* `--sensor-width-mm` 默认 36mm（全画幅），如你在 Unreal 里用了不同 Filmback，请改成对应数值。

## 5. 对比运行（推荐：before/after 对比）

为了方便定位问题、验证改动效果，`calibrate.py` 支持输出文件名和可视化 tag：

* 剔除前（关闭亚像素与视图剔除）：
```sh
python calibrate.py 1080 1920 11 8 15 1 -black_thr 40 -white_thr 3 -input_dir "./capture_P5UIST" -camera camera_config.json ^
  -output_xml calibration_result_before.xml -viz_tag before -enable_subpix 0 -enable_view_filter 0
```

* 剔除后（开启亚像素与视图剔除）：
```sh
python calibrate.py 1080 1920 11 8 15 1 -black_thr 40 -white_thr 3 -input_dir "./capture_P5UIST" -camera camera_config.json ^
  -output_xml calibration_result_after.xml -viz_tag after -enable_subpix 1 -enable_view_filter 1
```

对应输出文件：
* `calibration_result_before.xml`
* `calibration_result_after.xml`
* `visualize_corners_projector_before_capture_X.png`
* `visualize_corners_projector_after_capture_X.png`

## 6. 结果解释与排错（Debugging）

### 6.1 首先看 RMS
* `=== Result === RMS`（stereoCalibrate 的 RMS）越小越好；一般来说：
  * > 3：大概率存在解码离群点或采集质量问题
  * 2 左右：通常可用，但仍可能受畸变/曝光/摩尔纹影响
  * < 1.5：通常属于比较理想的采集与解码质量（不保证一定达到，取决于设备与采集）

### 6.2 再看每视图 RMS
* 程序会打印 “Per-view Projector RMS”，可以快速定位哪组 `capture_X` 是离群视图。
* 如果某些视图明显比其它视图大很多，建议：
  * 先检查对应的 `visualize_corners_projector_*_capture_X.png`
  * 删除该 `capture_X` 或重拍（不要用“少量坏视图”拉低整体）

### 6.3 常见失败原因与对策
* 棋盘角点检测失败：
  * 常见原因：投影过曝、反光、模糊、棋盘太小、角点对比不足。
  * 对策：调整曝光/距离/角度；让棋盘更大、更清晰；尽量避免强反光。
* 灰码解码点太少：
  * 常见原因：投影对比度不足、曝光飘、棋盘不在投影覆盖范围、摩尔纹。
  * 对策：固定曝光；提高投影亮度或缩短曝光；增大 `graycode_step`；适当提高 `black_thr/white_thr`。

## 7. 参数与接口（CLI）

`calibrate.py` 关键参数：
* `-camera <camera_config.json>`：指定相机内参 JSON（格式见 `camera_config.json` 示例）。
* `-input_dir <dir>`：包含 `capture_*` 目录的输入根目录。
* `-output_xml <file>`：输出 XML 文件名（默认 `calibration_result.xml`）。
* `-viz_tag <tag>`：可视化图的 tag 前缀（用于 before/after 对比）。
* `-enable_subpix 0/1`：是否启用角点亚像素精炼（默认 1）。
* `-enable_view_filter 0/1`：是否启用离群视图剔除（默认 1，仅在明显离群时触发）。

## 8. 参考

* OpenCV stereo calibration / structured light 文档
* MORENO, Daniel; TAUBIN, Gabriel. Simple, accurate, and robust projector-camera calibration. 3DIMPVT 2012.
