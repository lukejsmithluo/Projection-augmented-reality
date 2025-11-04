#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标定数据格式转换工具
将XML格式的标定结果转换为虚拟投影仪验证系统所需的JSON格式

输入: calibration_result_optimized.xml
输出: calibration_result.json (兼容虚拟投影仪验证系统)
"""

import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys

def parse_opencv_matrix(node):
    """解析OpenCV XML矩阵节点"""
    rows = int(node.find('rows').text)
    cols = int(node.find('cols').text)
    data_text = node.find('data').text.strip()
    data = [float(x) for x in data_text.split()]
    return np.array(data).reshape(rows, cols)

def convert_xml_to_json(xml_file_path, json_file_path):
    """将XML标定结果转换为JSON格式"""
    
    # 使用OpenCV读取XML文件
    fs = cv2.FileStorage(str(xml_file_path), cv2.FILE_STORAGE_READ)
    
    if not fs.isOpened():
        raise ValueError(f"无法打开XML文件: {xml_file_path}")
    
    try:
        # 读取数据
        img_shape = fs.getNode('img_shape').mat().flatten()
        rms = fs.getNode('rms').real()
        cam_int = fs.getNode('cam_int').mat()
        cam_dist = fs.getNode('cam_dist').mat().flatten()
        proj_int = fs.getNode('proj_int').mat()
        proj_dist = fs.getNode('proj_dist').mat().flatten()
        rotation = fs.getNode('rotation').mat()
        translation = fs.getNode('translation').mat().flatten()
        successful_captures = int(fs.getNode('successful_captures').real())
        
        # 构建JSON数据结构
        calibration_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_file": str(xml_file_path),
                "conversion_tool": "convert_calibration_to_json.py",
                "format_version": "1.0"
            },
            "calibration_quality": {
                "rms_reprojection_error": float(rms),
                "successful_captures": successful_captures,
                "image_resolution": {
                    "width": int(img_shape[1]),
                    "height": int(img_shape[0])
                }
            },
            "camera_intrinsics": {
                "matrix": cam_int.tolist(),
                "distortion_coefficients": cam_dist.tolist(),
                "focal_length": {
                    "fx": float(cam_int[0, 0]),
                    "fy": float(cam_int[1, 1])
                },
                "principal_point": {
                    "cx": float(cam_int[0, 2]),
                    "cy": float(cam_int[1, 2])
                }
            },
            "projector_intrinsics": {
                "matrix": proj_int.tolist(),
                "distortion_coefficients": proj_dist.tolist(),
                "focal_length": {
                    "fx": float(proj_int[0, 0]),
                    "fy": float(proj_int[1, 1])
                },
                "principal_point": {
                    "cx": float(proj_int[0, 2]),
                    "cy": float(proj_int[1, 2])
                },
                "resolution": {
                    "width": 1920,  # 从之前的测试得知
                    "height": 1080
                }
            },
            "extrinsic_parameters": {
                "rotation_matrix": rotation.tolist(),
                "translation_vector": translation.tolist(),
                "rotation_vector": cv2.Rodrigues(rotation)[0].flatten().tolist(),
                "distance": float(np.linalg.norm(translation))
            },
            "coordinate_system": {
                "description": "OpenCV coordinate system",
                "camera_frame": "Right-handed, Z forward, Y down, X right",
                "projector_frame": "Same as camera frame",
                "units": "millimeters"
            }
        }
        
        # 计算欧拉角（用于验证）
        from scipy.spatial.transform import Rotation as R
        r = R.from_matrix(rotation)
        euler_angles = r.as_euler('xyz', degrees=True)
        
        calibration_data["extrinsic_parameters"]["euler_angles"] = {
            "pitch_x": float(euler_angles[0]),
            "yaw_y": float(euler_angles[1]), 
            "roll_z": float(euler_angles[2])
        }
        
        # 保存JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(calibration_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 标定数据转换完成")
        print(f"  输入文件: {xml_file_path}")
        print(f"  输出文件: {json_file_path}")
        print(f"  RMS误差: {rms:.4f} 像素")
        print(f"  成功捕获: {successful_captures} 次")
        print(f"  相机-投影仪距离: {np.linalg.norm(translation):.2f} mm")
        print(f"  欧拉角: Pitch={euler_angles[0]:.2f}°, Yaw={euler_angles[1]:.2f}°, Roll={euler_angles[2]:.2f}°")
        
        return calibration_data
        
    except Exception as e:
        print(f"转换过程中出错: {e}")
        raise
    finally:
        fs.release()

def main():
    """主函数"""
    # 设置文件路径
    current_dir = Path(__file__).parent
    xml_file = current_dir / "calibration_result_optimized.xml"
    json_file = current_dir / "calibration_result.json"
    
    if not xml_file.exists():
        print(f"[错误] 找不到XML标定文件: {xml_file}")
        return
    
    try:
        # 转换文件
        calibration_data = convert_xml_to_json(xml_file, json_file)
        
        print(f"\n📊 标定数据摘要:")
        print(f"  相机内参: fx={calibration_data['camera_intrinsics']['focal_length']['fx']:.2f}, fy={calibration_data['camera_intrinsics']['focal_length']['fy']:.2f}")
        print(f"  投影仪内参: fx={calibration_data['projector_intrinsics']['focal_length']['fx']:.2f}, fy={calibration_data['projector_intrinsics']['focal_length']['fy']:.2f}")
        print(f"  相机-投影仪距离: {calibration_data['extrinsic_parameters']['distance']:.2f} mm")
        
        print(f"\n🎯 现在可以使用虚拟投影仪验证系统:")
        print(f"  python examples/validation/virtual_projector_validation_example.py")
        
    except Exception as e:
        print(f"[错误] 转换失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()