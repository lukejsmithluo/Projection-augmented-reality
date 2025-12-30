import cv2
import numpy as np
import os
import math

def rotation_matrix_to_euler_unreal(R):
    """
    将 OpenCV 的旋转矩阵 (Right-handed, Y-down, Z-forward) 
    转换为 Unreal Engine 的欧拉角 (Left-handed, Z-up, X-forward).
    Unreal Rotator: (Roll, Pitch, Yaw)
    """
    # 1. 坐标系基底转换矩阵 (Basis Change Matrix)
    # OpenCV: X_cv, Y_cv, Z_cv
    # Unreal: X_ue, Y_ue, Z_ue
    # X_ue (Forward) = Z_cv
    # Y_ue (Right)   = X_cv
    # Z_ue (Up)      = -Y_cv
    
    # M = [ [0, 0, 1],
    #       [1, 0, 0],
    #       [0, -1, 0] ]
    M = np.array([[0, 0, 1], [1, 0, 0], [0, -1, 0]])
    
    # R_ue = M * R_cv * M.T
    R_ue = M @ R @ M.T
    
    # 2. 旋转矩阵转欧拉角 (Unreal Order: Roll, Pitch, Yaw ? No, standard decomposition)
    # Unreal 使用的旋转顺序通常是 Roll(X) -> Pitch(Y) -> Yaw(Z) ???
    # 实际上 Unreal 的 Rotator 是 (Pitch, Yaw, Roll) 但构造函数是 MakeRotator(Roll, Pitch, Yaw)
    # 我们使用标准算法提取 Euler Angles.
    # Sy = sqrt(R[0,0] * R[0,0] + R[1,0] * R[1,0])
    # bool singular = Sy < 1e-6;
    # if (!singular)
    #     x = atan2(R[2,1] , R[2,2])
    #     y = atan2(-R[2,0], sy)
    #     z = atan2(R[1,0], R[0,0])
    # else
    #     x = atan2(-R[1,2], R[1,1])
    #     y = atan2(-R[2,0], sy)
    #     z = 0
    
    # 但要注意 Unreal 的坐标轴定义：
    # Pitch: 围绕 Y 轴 (Right) 旋转 (点头)
    # Yaw:   围绕 Z 轴 (Up) 旋转 (摇头)
    # Roll:  围绕 X 轴 (Forward) 旋转 (歪头)
    
    # 让我们使用 scipy 或手动计算。这里手动计算 Z-Y-X 顺序 (Yaw-Pitch-Roll) 对应 Unreal 的应用顺序吗？
    # Unreal Rotator 顺序通常是：先 Roll，再 Pitch，再 Yaw (Local 坐标系)？
    # 实际上最简单的方法是输出矩阵给用户，或者使用标准的转换公式。
    # 为避免复杂的欧拉角万向锁和顺序问题，这里提供一个近似的转换。
    
    sy = math.sqrt(R_ue[0,0] * R_ue[0,0] + R_ue[1,0] * R_ue[1,0])
    singular = sy < 1e-6
    
    if not singular:
        x = math.atan2(R_ue[2,1], R_ue[2,2]) # Roll
        y = math.atan2(-R_ue[2,0], sy)       # Pitch
        z = math.atan2(R_ue[1,0], R_ue[0,0]) # Yaw
    else:
        x = math.atan2(-R_ue[1,2], R_ue[1,1])
        y = math.atan2(-R_ue[2,0], sy)
        z = 0
        
    return np.degrees(x), np.degrees(y), np.degrees(z)

def process_calibration_xml(xml_path):
    if not os.path.exists(xml_path):
        print(f"Error: 文件 {xml_path} 不存在")
        return

    fs = cv2.FileStorage(xml_path, cv2.FILE_STORAGE_READ)
    if not fs.isOpened():
        print("Error: 无法打开 XML 文件")
        return

    # 读取矩阵
    cam_int = fs.getNode("cam_int").mat()
    proj_int = fs.getNode("proj_int").mat()
    proj_dist = fs.getNode("proj_dist").mat()
    rotation = fs.getNode("rotation").mat()
    translation = fs.getNode("translation").mat()
    img_shape = fs.getNode("img_shape").mat() # [rows, cols] -> [Height, Width]

    # 解析分辨率
    # img_shape data: [Height, Width]
    # 但根据 XML 内容: 1242. 2208. -> Height=1242, Width=2208 (ZED 2K)
    cam_h = int(img_shape[0][0])
    cam_w = int(img_shape[1][0])
    
    # 投影仪分辨率 (通常是 1280x720，这里我们根据光心反推或假设)
    # Procam-calibration 通常假设 1280x720 或用户输入。
    # 我们这里假设 1280x720，因为 Cx=526 (接近 640), Cy=429 (接近 360)
    proj_w = 1280
    proj_h = 720
    
    print("-" * 50)
    print("【Unreal Engine Lens File 参数计算】")
    print("-" * 50)
    
    # 1. 投影仪内参 (Lens File Parameters)
    print(f"1. 投影仪内参 (Projector Intrinsics) - 填写到 Lens File")
    print(f"   假设投影仪分辨率: {proj_w} x {proj_h}")
    
    fx = proj_int[0,0]
    fy = proj_int[1,1]
    cx = proj_int[0,2]
    cy = proj_int[1,2]
    
    # 归一化光心 (Principal Point)
    cx_norm = cx / proj_w
    cy_norm = cy / proj_h
    
    # 畸变系数
    k1 = proj_dist[0,0]
    k2 = proj_dist[0,1]
    p1 = proj_dist[0,2]
    p2 = proj_dist[0,3]
    k3 = proj_dist[0,4] if proj_dist.shape[1] > 4 else 0.0

    print(f"   * Image Center (Principal Point):")
    print(f"       Cx (Normalized) = {cx_norm:.6f}")
    print(f"       Cy (Normalized) = {cy_norm:.6f}")
    print(f"   * Distortion (OpenCV / RadTan):")
    print(f"       k1 = {k1:.6f}")
    print(f"       k2 = {k2:.6f}")
    print(f"       p1 = {p1:.6f}")
    print(f"       p2 = {p2:.6f}")
    print(f"       k3 = {k3:.6f}")
    
    # 焦距计算 (Focal Length)
    # F(mm) = F(pixels) * SensorWidth(mm) / ImageWidth(pixels)
    # 假设传感器宽度为 36mm (全画幅标准，仅作为参考，虚幻中需保持一致)
    sensor_width_mm = 36.0 
    focal_length_mm = fx * sensor_width_mm / proj_w
    
    print(f"   * Focal Length (基于假设 Sensor Width = {sensor_width_mm}mm):")
    print(f"       Focal Length = {focal_length_mm:.6f} mm")
    print(f"       (注意：在虚幻 Lens File 中，请确保 Sensor Width 也设置为 {sensor_width_mm}mm)")
    print(f"       (如果使用 Fx/Fy 直接输入，请忽略此项，但在 Lens File 中通常需要 mm)")

    print("-" * 50)
    
    # 2. 外参 (Extrinsics) - 投影仪相对于相机的位置
    print(f"2. 投影仪外参 (Projector Extrinsics) - 填写到 Actor Transform")
    print(f"   这是投影仪(Projector) 相对于 相机(ZED) 的位置和旋转。")
    
    # 坐标系转换: OpenCV (Right: X, Down: Y, Fwd: Z) -> Unreal (Fwd: X, Right: Y, Up: Z)
    # Pos_UE = (Pos_CV.z, Pos_CV.x, -Pos_CV.y)
    
    tx = translation[0][0]
    ty = translation[1][0]
    tz = translation[2][0]
    
    # 单位转换: 假设标定单位是 cm (根据 -20.89 这种数值大小判断，如果是 mm 则太小)
    # 如果标定板格子大小单位是 mm，则这里是 mm。如果是 cm，则这里是 cm。
    # 20 个单位，对于投影仪和相机的距离，cm 是合理的。
    
    pos_ue_x = tz
    pos_ue_y = tx
    pos_ue_z = -ty
    
    print(f"   * Location (位置) [单位: 假设原始单位为 cm]:")
    print(f"       X (Forward) = {pos_ue_x:.4f}")
    print(f"       Y (Right)   = {pos_ue_y:.4f}")
    print(f"       Z (Up)      = {pos_ue_z:.4f}")
    
    # 旋转转换
    roll, pitch, yaw = rotation_matrix_to_euler_unreal(rotation)
    
    print(f"   * Rotation (旋转) [单位: 度]:")
    print(f"       Roll  (X) = {roll:.4f}")
    print(f"       Pitch (Y) = {pitch:.4f}")
    print(f"       Yaw   (Z) = {yaw:.4f}")

    print("-" * 50)
    print("注意：")
    print("1. 请确认您标定时使用的棋盘格尺寸单位。如果 calibration_result.xml 中的 translation 数值是毫米，请将上述 Location 除以 10 (转为 cm)。")
    print("   (根据数值 -20.89，如果是 mm 则仅 2cm 距离，不太可能；如果是 cm 则 20cm 距离，比较合理。)")
    print("2. 虚幻引擎默认单位是 cm。")

if __name__ == "__main__":
    xml_file = r"e:\OrganizedWork\susTech\HCI\XProjection\Projection-augmented-reality\Procam-calibration\calibration_result.xml"
    process_calibration_xml(xml_file)
