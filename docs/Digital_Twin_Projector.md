# 数字孪生投影仪复现程序

本文档描述如何从 projector-camera 标定结果构建一个“数字孪生投影仪”：在虚拟空间中放置一个与真实投影仪具有相同内参、畸变和相对相机外参的虚拟投影仪，使虚拟投影仪看到的图像经真实投影仪投射后能够覆盖现实表面。

这里的“程序”指可复现实验流程和算法说明，不限定具体软件实现。本文使用 Unreal Engine 作为本项目实现平台，但核心公式可以换算到 Unity、OpenGL、Blender、OpenCV 或自研渲染器中。

## 1. 目标与坐标关系

系统包含一台相机和一台投影仪。二者刚性固定，因此只要得到：

1. 投影仪内参 `Kp` 和畸变参数 `Dp`。
2. 投影仪相对于相机参考坐标系的外参。
3. 渲染系统中相机、投影仪、场景几何之间一致的坐标变换。

就可以在虚拟世界中复现真实投影仪的位置和成像模型。

如果真实投影仪接收虚拟投影仪渲染出的图像，则理想情况下：

```text
真实相机看到的现实表面
≈ 虚拟相机/点云重建出的虚拟表面
≈ 虚拟投影仪投影到虚拟表面的结果
≈ 真实投影仪投影到现实表面的结果
```

## 2. 设备与环境准备

建议准备以下设备：

- 一台投影仪，输出分辨率固定，例如 `1280 x 720`。
- 一台相机，建议使用固定曝光、固定增益、固定分辨率。
- 一块平整棋盘格标定板。
- 一套刚性支架，使相机和投影仪之间的相对位置在实验中保持不变。
- 一台运行标定程序和渲染程序的计算机。
- 可选：一台额外观察相机，用于拍摄投影结果并修正 Image Center。

实验前需要固定这些条件：

- 投影仪分辨率。
- Windows / 系统显示缩放。
- 投影仪数字变焦、梯形校正、自动画面适配、过扫描。
- 相机采集分辨率。
- 相机曝光和增益。

建议关闭：

```text
Keystone / Auto Keystone
Digital Zoom
Overscan
Auto Fit / Screen Fit
Windows display scaling other than 100%
```

如果这些设置在标定后发生变化，需要重新验证，严重时需要重新标定。

## 3. Projector-Camera 标定流程

### 3.1 生成 Gray Code 图案

使用投影仪真实输出分辨率生成结构光图案：

```text
projector_width  = W
projector_height = H
```

本项目使用 OpenCV structured light / Gray Code 思路。图案至少包含：

- 横向编码图案。
- 纵向编码图案。
- white 参考帧。
- black 参考帧。

要求生成分辨率必须等于投影仪实际输出分辨率。

### 3.2 采集多组棋盘视角

每一组采集流程：

1. 将棋盘放在相机和投影仪共同可见区域。
2. 投影 Gray Code 序列。
3. 相机逐帧拍摄。
4. 移动或旋转棋盘，重复采集。

建议采集 10 组以上不同姿态，覆盖不同位置、距离和角度。避免极端倾斜、严重反光、过曝、模糊或棋盘只占画面很小区域。

### 3.3 建立棋盘三维点到投影仪像素点的对应

对每一组采集：

1. 在相机图像中检测棋盘角点。
2. 对相机图像中的每个角点附近区域进行 Gray Code 解码。
3. 得到相机角点附近的投影仪像素坐标。
4. 用局部 homography 提高角点处投影仪像素估计精度。

棋盘上的三维点可定义为：

```text
X_board = [i * square_size, j * square_size, 0]^T
```

投影仪被视作“反向相机”，于是可以得到：

```text
X_board  ->  projector pixel (u_p, v_p)
```

这使得投影仪可以用普通相机标定方法求解内参。

## 4. 投影仪内参和畸变模型

投影仪内参矩阵：

```text
Kp =
[ fx   0  cx
   0  fy  cy
   0   0   1 ]
```

OpenCV 常用 5 参数畸变：

```text
Dp = [k1, k2, p1, p2, k3]
```

对投影仪坐标系中的三维点：

```text
X_p = [X, Y, Z]^T
```

归一化坐标：

```text
x = X / Z
y = Y / Z
r2 = x^2 + y^2
```

OpenCV 畸变模型：

```text
radial = 1 + k1*r2 + k2*r2^2 + k3*r2^3

x_d = x*radial + 2*p1*x*y + p2*(r2 + 2*x^2)
y_d = y*radial + p1*(r2 + 2*y^2) + 2*p2*x*y
```

最终投影仪像素：

```text
u = fx*x_d + cx
v = fy*y_d + cy
```

如果渲染系统支持自定义投影矩阵，应使用 `fx, fy, cx, cy` 构造离轴投影。若只支持普通 FOV，需要至少匹配水平和垂直视场：

```text
HFOV = 2 * atan(W / (2*fx))
VFOV = 2 * atan(H / (2*fy))
```

如果渲染器使用 filmback / focal length 模型，给定传感器宽度 `S_w`：

```text
f_mm = fx * S_w / W
S_h  = f_mm * H / fy
```

若强制使用固定宽高比 filmback，可令：

```text
S_h = S_w * H / W
```

但此时 `fy` 可能只能近似匹配。

主点通常转成归一化值：

```text
Cx_norm = cx / W
Cy_norm = cy / H
```

不同软件对主点的定义可能不同，有些使用 `[0,1]` 归一化坐标，有些使用相对中心偏移。若使用相对中心偏移，常见形式为：

```text
offset_x = (cx - W/2) / W
offset_y = (cy - H/2) / H
```

具体符号需要按渲染器的图像坐标方向验证。

## 5. 相机到投影仪外参

OpenCV `stereoCalibrate` 通常输出从第一相机坐标系到第二相机坐标系的变换。若第一相机为真实相机 `C`，第二相机为投影仪 `P`，则：

```text
{}^P X = R_{P<-C} * {}^C X + t_{P<-C}
```

也就是：

```text
T_{P<-C} =
[ R_{P<-C}  t_{P<-C}
  0 0 0      1       ]
```

但是在虚拟场景中，通常需要把虚拟投影仪作为相机的子节点放置，即需要“投影仪坐标系相对于相机坐标系的位姿”。这个位姿是上式的逆：

```text
R_{C<-P} = R_{P<-C}^T
t_{C<-P} = -R_{P<-C}^T * t_{P<-C}
```

因此：

```text
T_{C<-P} =
[ R_{C<-P}  t_{C<-P}
  0 0 0      1       ]
```

其中 `t_{C<-P}` 就是投影仪光心在相机坐标系中的位置。

## 6. 坐标系换算到渲染引擎

OpenCV 相机坐标系通常为：

```text
+X: 图像右方
+Y: 图像下方
+Z: 镜头前方
```

如果目标渲染引擎使用不同坐标系，需要定义一个基底变换矩阵 `B`：

```text
v_engine = B * v_opencv
```

则旋转和平移转换为：

```text
R_engine = B * R_opencv * B^{-1}
t_engine = s * B * t_opencv
```

其中 `s` 是单位缩放。例如标定中棋盘格单位为 mm，而引擎单位为 cm，则：

```text
s = 0.1
```

### Unreal 示例

Unreal 常用坐标系：

```text
+X: 前方
+Y: 右方
+Z: 上方
```

对应 OpenCV 到 Unreal 的基底变换为：

```text
B =
[ 0   0   1
  1   0   0
  0  -1   0 ]
```

即：

```text
X_ue =  Z_cv
Y_ue =  X_cv
Z_ue = -Y_cv
```

对投影仪相对相机位姿，先对 OpenCV 外参取逆：

```text
R_inv = R^T
t_inv = -R^T * t
```

再转到引擎坐标：

```text
t_ue = s * B * t_inv
R_ue = B * R_inv * B^T
```

然后将 `R_ue` 转为引擎所需的欧拉角、四元数或矩阵格式。

注意：不同引擎的相机 forward 方向、图像上下方向、欧拉角顺序都可能不同。应通过简单 A/B 测试验证旋转符号。例如本项目在 Unreal 中实测需要对导出的 Pitch 做符号修正，这是 Unreal 虚拟投影仪组件约定与 OpenCV 外参转换之间的实现差异，不是标定数学本身的一部分。

## 7. 构建数字孪生投影仪

在任意渲染系统中，应构建如下对象：

```text
CameraFrame
  VirtualProjector
```

`CameraFrame` 代表标定时使用的物理相机视点。如果使用双目相机，应明确外参相对于左目、右目还是中间基线中心。本项目使用 ZED 左目图像标定，因此外参父坐标系应是 ZED 左目视点。

`VirtualProjector` 应满足：

1. 位置和旋转来自 `T_{C<-P}` 经过目标引擎坐标转换后的结果。
2. 投影矩阵来自投影仪内参 `Kp`。
3. 畸变模型与 OpenCV 畸变模型一致，或用等价的预畸变/后处理贴图实现。
4. 输出分辨率等于真实投影仪实际显示分辨率。
5. 虚拟投影仪的渲染画面以 pixel-perfect 方式送到真实投影仪。

## 8. Image Center 修正

### 8.1 为什么需要修正

即使 projector-camera 标定 RMS 很低，实际投影中仍可能出现稳定的整体偏移。常见原因包括：

- 投影仪实际显示链路存在轻微缩放或偏移。
- 渲染器对 LensFile / principal point 的定义和 OpenCV 略有差异。
- 投影仪光学中心和标定模型之间存在小量系统误差。
- 真实投影仪的数字处理链路并非理想 pinhole。

如果误差表现为：

```text
整个投影画面大致同方向偏移
```

优先修正 Image Center，即 `cx, cy` 或其归一化形式 `Cx_norm, Cy_norm`。

如果误差表现为：

```text
中心准、边缘不准
有些区域准、有些区域不准
残差呈弯曲或径向分布
```

则主要问题可能是畸变、FOV、几何表面或深度重建，不应只继续调 Image Center。

### 8.2 半手动修正需要的数据

需要准备：

- 当前投影仪主点：

```text
Cx_old = cx / W
Cy_old = cy / H
```

- 投影仪分辨率：

```text
W, H
```

- 一张观察相机拍摄的照片，照片中同时看到：
  - 现实目标点，例如棋盘格角点。
  - 投影实际点，例如投影黑格角点。

- 多组点对：

```text
target_i    = (x_target_i, y_target_i)
projected_i = (x_projected_i, y_projected_i)
```

二者必须在同一张照片坐标系中。

- 观察照片尺寸：

```text
photo_width, photo_height
```

- 反馈增益：

```text
alpha = 0.25 ~ 0.5
```

### 8.3 残差定义

对每组点：

```text
dx_i = x_projected_i - x_target_i
dy_i = y_projected_i - y_target_i
```

照片坐标系通常为：

```text
+x: 向右
+y: 向下
```

因此：

```text
dx_i > 0 表示投影点在目标点右边
dy_i > 0 表示投影点在目标点下边
dy_i < 0 表示投影点在目标点上边
```

求平均残差：

```text
mean_dx = (1/N) * sum(dx_i)
mean_dy = (1/N) * sum(dy_i)
```

### 8.4 Image Center 更新公式

使用观察照片中的平均残差做保守反馈：

```text
Cx_new = Cx_old - alpha * mean_dx / photo_width
Cy_new = Cy_old - alpha * mean_dy / photo_height
```

如果使用像素形式的主点：

```text
cx_new = W * Cx_new
cy_new = H * Cy_new
```

符号解释：

- 投影整体向右偏：`mean_dx > 0`，因此 `Cx_new` 减小。
- 投影整体向左偏：`mean_dx < 0`，因此 `Cx_new` 增大。
- 投影整体向上偏：`mean_dy < 0`，因此 `Cy_new` 增大。
- 投影整体向下偏：`mean_dy > 0`，因此 `Cy_new` 减小。

本项目中曾观察到投影整体向右上偏，对应：

```text
mean_dx > 0
mean_dy < 0
```

所以修正方向为：

```text
Cx 减小
Cy 增大
```

### 8.5 为什么需要增益 alpha

观察相机照片中的像素偏移不一定等于投影仪图像坐标中的像素偏移。二者之间存在观察相机透视关系。因此使用 `alpha` 做迭代反馈。

推荐：

```text
alpha = 0.25  更保守，适合初次修正
alpha = 0.5   常用
alpha = 1.0   只在方向稳定且误差很小时尝试
```

迭代流程：

1. 用当前 `Cx, Cy` 投影测试图案。
2. 拍照并标注点对。
3. 根据公式计算 `Cx_new, Cy_new`。
4. 写回渲染系统或 LensFile。
5. 重复 1 到 3 次，直到平均残差接近 0。

## 9. 残差分析与故障定位

完成 Image Center 修正后，需要观察残差形态。

### 9.1 平移型残差

现象：

```text
所有点几乎同方向、同量级偏移
```

优先处理：

```text
Image Center
输出画面偏移
窗口缩放
显示器/投影仪缩放
```

### 9.2 径向或弯曲残差

现象：

```text
中心附近准，边缘逐渐偏
偏差方向随位置呈弯曲或径向变化
```

优先处理：

```text
畸变参数 k1, k2, k3, p1, p2
畸变模型方向
渲染器 LensFile 解释方式
```

### 9.3 线性倾斜型残差

现象：

```text
某一侧准，另一侧偏
距离越远偏差越大
```

优先处理：

```text
外参旋转
投影平面姿态
虚拟表面法线
```

### 9.4 和点云或实时深度相关的残差

如果投影内容依赖实时点云、深度图或空间重建，ZED 或其他深度相机的深度误差会影响最终投影。

建议分三步隔离：

1. 绕开点云，只投影固定 2D 测试图到真实标定板。
2. 使用理想虚拟平面替代实时点云表面。
3. 冻结一次点云或 mesh，再与实时点云结果比较。

判断：

```text
绕开点云仍偏：优先查内参、畸变、Image Center、外参。
理想平面准但点云不准：优先查深度、点云平滑、帧同步、坐标变换。
冻结点云准但实时点云漂：优先查实时深度噪声和同步。
```

## 10. 可复现实验流程摘要

1. 固定相机和投影仪，关闭所有自动缩放和自动校正。
2. 生成与投影仪真实输出分辨率一致的 Gray Code 图案。
3. 采集多组棋盘姿态。
4. 解码 projector-camera 像素对应关系。
5. 用投影仪像素点和棋盘三维点标定投影仪内参。
6. 用 stereo calibration 求解相机到投影仪外参。
7. 将外参取逆，得到投影仪相对相机的虚拟位姿。
8. 将 OpenCV 坐标转换到目标渲染系统坐标。
9. 在渲染系统中设置虚拟投影仪内参、畸变、分辨率和位姿。
10. 将虚拟投影仪图像以 pixel-perfect 方式输出给真实投影仪。
11. 用棋盘或网格测试投影对齐情况。
12. 若存在整体偏移，按 Image Center 更新公式修正 `Cx, Cy`。
13. 若剩余局部误差明显，继续检查畸变、外参旋转、投影表面几何和实时深度。

## 11. 最小参数清单

为了让他人复现，需要记录并公开：

```text
projector_width
projector_height
camera_resolution
chessboard_inner_corners
square_size
camera_intrinsics
projector_intrinsics Kp
projector_distortion Dp
stereo R, t
OpenCV-to-renderer basis matrix B
translation unit scale s
final Image Center Cx, Cy
Image Center refinement gain alpha
validation residual before/after refinement
```

如果使用实时点云，还应记录：

```text
depth mode
depth resolution
coordinate units
whether point cloud / mesh is live or frozen
whether points are in camera frame or world frame
whether camera tracking transform has been applied once or multiple times
```

## 12. 参考实现文件

本项目中的相关脚本：

```text
Procam-calibration/calibrate.py
Procam-calibration/calculate_unreal_params.py
Procam-calibration/image_center_tuner.py
```

其中：

- `calibrate.py` 完成 projector-camera 标定。
- `calculate_unreal_params.py` 演示 OpenCV 标定结果如何换算到 Unreal。
- `image_center_tuner.py` 实现半手动 Image Center 残差反馈。

这些脚本不是唯一实现方式。复现者只要按照本文定义的几何关系、坐标变换和 Image Center 更新公式，即可将结果换算到自己的渲染系统中。
