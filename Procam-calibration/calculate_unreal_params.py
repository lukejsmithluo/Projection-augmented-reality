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
    
    M = np.array([[0, 0, 1], [1, 0, 0], [0, -1, 0]])
    
    # R_ue = M * R_cv * M.T
    R_ue = M @ R @ M.T
    
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
    rotation = fs.getNode("rotation").mat()       # R (ZED -> Projector)
    translation = fs.getNode("translation").mat() # T (ZED -> Projector)
    img_shape = fs.getNode("img_shape").mat() 

    # ---------------------------------------------------------
    # 1. 内参处理
    # ---------------------------------------------------------
    proj_w = 1280
    proj_h = 720
    
    print("-" * 60)
    print("【Unreal Engine Lens File 参数计算】")
    print("-" * 60)
    
    fx = proj_int[0,0]
    fy = proj_int[1,1]
    cx = proj_int[0,2]
    cy = proj_int[1,2]
    
    cx_norm = cx / proj_w
    cy_norm = cy / proj_h
    
    k1 = proj_dist[0,0]
    k2 = proj_dist[0,1]
    p1 = proj_dist[0,2]
    p2 = proj_dist[0,3]
    k3 = proj_dist[0,4] if proj_dist.shape[1] > 4 else 0.0

    print(f"1. Lens File 参数 (CineCameraComponent / LensFile)")
    print(f"   假设 Sensor Width = 36.0mm (全画幅标准，请在虚幻中确认此设置)")
    sensor_width_mm = 36.0 
    focal_length_mm = fx * sensor_width_mm / proj_w
    
    print(f"   * Current Focal Length: {focal_length_mm:.4f} mm")
    print(f"   * Current Aperture:     建议设置 > 10 (例如 22) 以获得全清晰画面")
    print(f"   * Focus Distance:       设置为投影距离 (例如 200.0 cm)")
    print(f"   * Image Center:")
    print(f"       Cx: {cx_norm:.6f}")
    print(f"       Cy: {cy_norm:.6f}")
    print(f"   * Distortion (OpenCV):")
    print(f"       k1: {k1:.6f}, k2: {k2:.6f}, k3: {k3:.6f}")
    print(f"       p1: {p1:.6f}, p2: {p2:.6f}")
    print(f"   * Nodal Offset: 0.0 (我们标定的是光学中心)")

    # ---------------------------------------------------------
    # 2. 外参处理 (Coordinate Conversion & Inversion)
    # ---------------------------------------------------------
    print("-" * 60)
    print(f"2. Actor Transform (Projector 相对于 Camera)")
    
    # 原始 R, T 是 ZED 到 Projector 的变换: P_proj = R * P_zed + T
    # 即 T 是 ZED 原点在 Projector 坐标系下的位置。
    # 我们需要的是 Projector 在 ZED 坐标系下的位置 (Projector relative to ZED)。
    # P_zed = R.T * P_proj - R.T * T
    # 所以:
    # R_rel = R.T
    # T_rel = - R.T * T
    
    R_inv = rotation.T
    T_inv = - R_inv @ translation
    
    # 现在将 T_rel (在 ZED/OpenCV 坐标系中) 转换为 Unreal 坐标系
    # OpenCV: +X Right, +Y Down, +Z Forward
    # Unreal: +X Forward, +Y Right, +Z Up
    # UE_X = CV_Z
    # UE_Y = CV_X
    # UE_Z = -CV_Y
    
    pos_ue_x = T_inv[2][0]
    pos_ue_y = T_inv[0][0]
    pos_ue_z = -T_inv[1][0]
    
    # 旋转转换
    roll, pitch, yaw = rotation_matrix_to_euler_unreal(R_inv)
    
    print(f"   请将以下数值填入 Projector Actor 的 Transform (Parent 是 Camera):")
    print(f"   [单位提示]: 根据数值推测，您的标定单位可能是 'cm'。")
    print(f"              如果看起来位置不对，请尝试除以 10 (如果是 mm) 或 乘以 10。")
    print(f"")
    print(f"   * Location (位置):")
    print(f"       X (Forward): {pos_ue_x:.4f}")
    print(f"       Y (Right):   {pos_ue_y:.4f}")
    print(f"       Z (Up):      {pos_ue_z:.4f}")
    print(f"")
    print(f"   * Rotation (旋转):")
    print(f"       Roll:  {roll:.4f}")
    print(f"       Pitch: {pitch:.4f}")
    print(f"       Yaw:   {yaw:.4f}")

    print("-" * 60)

if __name__ == "__main__":
    xml_file = r"e:\OrganizedWork\susTech\HCI\XProjection\Projection-augmented-reality\Procam-calibration\calibration_result.xml"
    process_calibration_xml(xml_file)
