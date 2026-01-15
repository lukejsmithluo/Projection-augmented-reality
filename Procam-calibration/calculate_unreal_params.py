import cv2
import numpy as np
import os
import math
import argparse


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

    sy = math.sqrt(R_ue[0, 0] * R_ue[0, 0] + R_ue[1, 0] * R_ue[1, 0])
    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R_ue[2, 1], R_ue[2, 2])  # Roll
        y = math.atan2(-R_ue[2, 0], sy)  # Pitch
        z = math.atan2(R_ue[1, 0], R_ue[0, 0])  # Yaw
    else:
        x = math.atan2(-R_ue[1, 2], R_ue[1, 1])
        y = math.atan2(-R_ue[2, 0], sy)
        z = 0

    return np.degrees(x), np.degrees(y), np.degrees(z)


def _read_required_mat(fs: cv2.FileStorage, key: str) -> np.ndarray:
    node = fs.getNode(key)
    if node is None or node.empty():
        raise ValueError(f"Missing required key '{key}' in calibration XML.")
    mat = node.mat()
    if mat is None:
        raise ValueError(f"Key '{key}' exists but is not a matrix.")
    return mat


def _read_optional_mat(fs: cv2.FileStorage, key: str) -> np.ndarray | None:
    node = fs.getNode(key)
    if node is None or node.empty():
        return None
    mat = node.mat()
    return mat


def _as_rotation_3x3(mat: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=np.float64)
    if mat.shape != (3, 3):
        raise ValueError(f"Rotation must be 3x3, got {mat.shape}.")
    return mat


def _as_translation_3x1(mat: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=np.float64)
    if mat.shape == (3, 1):
        return mat
    if mat.shape == (1, 3):
        return mat.reshape(3, 1)
    if mat.size == 3:
        return mat.reshape(3, 1)
    raise ValueError(f"Translation must be 3x1 (or equivalent), got {mat.shape}.")


def _flatten_distortion(dist: np.ndarray) -> np.ndarray:
    dist = np.asarray(dist, dtype=np.float64).reshape(-1)
    if dist.size == 0:
        return np.zeros((5,), dtype=np.float64)
    if dist.size < 5:
        padded = np.zeros((5,), dtype=np.float64)
        padded[: dist.size] = dist
        return padded
    return dist


def process_calibration_xml(
    xml_path: str,
    proj_width: int = 1280,
    proj_height: int = 720,
    sensor_width_mm: float = 36.0,
    translation_scale: float = 1.0,
):
    if not os.path.exists(xml_path):
        print(f"Error: file does not exist: {xml_path}")
        return

    fs = cv2.FileStorage(xml_path, cv2.FILE_STORAGE_READ)
    if not fs.isOpened():
        print("Error: failed to open calibration XML.")
        return

    # 读取矩阵
    proj_int = _read_required_mat(fs, "proj_int")
    proj_dist = _read_required_mat(fs, "proj_dist")
    rotation = _as_rotation_3x3(_read_required_mat(fs, "rotation"))
    translation = _as_translation_3x1(_read_required_mat(fs, "translation"))
    img_shape = _read_optional_mat(fs, "img_shape")
    rms_node = fs.getNode("rms")
    rms = (
        float(rms_node.real())
        if rms_node is not None and not rms_node.empty()
        else None
    )
    fs.release()

    # ---------------------------------------------------------
    # 1. 内参处理
    # ---------------------------------------------------------
    proj_w = int(proj_width)
    proj_h = int(proj_height)

    print("-" * 60)
    title = "Unreal Engine lens parameters from calibration"
    if rms is not None:
        title += f" (RMS: {rms:.6f})"
    print(title)
    print("-" * 60)

    fx = proj_int[0, 0]
    fy = proj_int[1, 1]
    cx = proj_int[0, 2]
    cy = proj_int[1, 2]

    cx_norm = cx / proj_w
    cy_norm = cy / proj_h

    dist = _flatten_distortion(proj_dist)
    k1 = float(dist[0])
    k2 = float(dist[1])
    p1 = float(dist[2])
    p2 = float(dist[3])
    k3 = float(dist[4]) if dist.size > 4 else 0.0

    print("1) Lens parameters (CineCameraComponent / LensFile)")
    print(f"   Projector resolution assumed: {proj_w} x {proj_h}")
    if img_shape is not None and img_shape.size >= 2:
        cam_h = int(img_shape.reshape(-1)[0])
        cam_w = int(img_shape.reshape(-1)[1])
        print(f"   Camera image shape in XML: {cam_w} x {cam_h}")
    print(f"   Filmback sensor width assumption: {sensor_width_mm:.3f} mm")
    focal_length_mm = fx * float(sensor_width_mm) / proj_w

    print("   Intrinsics (pixels):")
    print(f"     fx: {fx:.6f}")
    print(f"     fy: {fy:.6f}")
    print(f"   Focal length (derived): {focal_length_mm:.4f} mm")
    print("   Image center (normalized):")
    print(f"     Cx: {cx_norm:.6f}")
    print(f"     Cy: {cy_norm:.6f}")
    print("   Distortion (OpenCV k1,k2,p1,p2,k3):")
    print(f"     k1: {k1:.6f}, k2: {k2:.6f}, k3: {k3:.6f}")
    print(f"     p1: {p1:.6f}, p2: {p2:.6f}")
    print("   Nodal offset: 0.0")

    # ---------------------------------------------------------
    # 2. 外参处理 (Coordinate Conversion & Inversion)
    # ---------------------------------------------------------
    print("-" * 60)
    print("2) Actor transform (Projector relative to Camera)")

    translation = translation * float(translation_scale)

    R_inv = rotation.T
    T_inv = -R_inv @ translation

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

    print("   Set the following values on the Projector Actor (Parent: Camera):")
    print(f"   Translation scale applied: {translation_scale:g}")
    print("")
    print("   Location:")
    print(f"     X (Forward): {pos_ue_x:.4f}")
    print(f"     Y (Right):   {pos_ue_y:.4f}")
    print(f"     Z (Up):      {pos_ue_z:.4f}")
    print("")
    print("   Rotation (degrees):")
    print(f"     Roll:  {roll:.4f}")
    print(f"     Pitch: {pitch:.4f}")
    print(f"     Yaw:   {yaw:.4f}")

    print("-" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert calibration XML to Unreal-friendly parameters."
    )
    parser.add_argument(
        "-xml",
        "--xml",
        type=str,
        default="calibration_result.xml",
        help="Path to calibration XML (default: calibration_result.xml).",
    )
    parser.add_argument(
        "--proj-width", type=int, default=1280, help="Projector width in pixels."
    )
    parser.add_argument(
        "--proj-height", type=int, default=720, help="Projector height in pixels."
    )
    parser.add_argument(
        "--sensor-width-mm",
        type=float,
        default=36.0,
        help="Filmback sensor width in mm.",
    )
    parser.add_argument(
        "--translation-scale",
        type=float,
        default=1.0,
        help="Scale factor applied to translation before reporting (e.g. 0.1 to convert mm to cm).",
    )
    args = parser.parse_args()

    process_calibration_xml(
        args.xml,
        proj_width=args.proj_width,
        proj_height=args.proj_height,
        sensor_width_mm=args.sensor_width_mm,
        translation_scale=args.translation_scale,
    )
