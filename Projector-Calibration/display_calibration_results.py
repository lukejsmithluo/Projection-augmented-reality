#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标定结果显示工具
解析XML格式的标定结果文件，以用户友好的格式显示相机和投影仪的内参外参
"""

import xml.etree.ElementTree as ET
import numpy as np
import math
from pathlib import Path

def parse_opencv_matrix(matrix_element):
    """解析OpenCV XML格式的矩阵"""
    rows = int(matrix_element.find('rows').text)
    cols = int(matrix_element.find('cols').text)
    data_text = matrix_element.find('data').text
    
    # 解析数据
    data_values = [float(x) for x in data_text.split()]
    
    # 重塑为矩阵
    matrix = np.array(data_values).reshape(rows, cols)
    return matrix

def rotation_matrix_to_euler(R):
    """将旋转矩阵转换为欧拉角（度）"""
    # 使用ZYX顺序的欧拉角
    sy = math.sqrt(R[0,0] * R[0,0] + R[1,0] * R[1,0])
    
    singular = sy < 1e-6
    
    if not singular:
        x = math.atan2(R[2,1], R[2,2])
        y = math.atan2(-R[2,0], sy)
        z = math.atan2(R[1,0], R[0,0])
    else:
        x = math.atan2(-R[1,2], R[1,1])
        y = math.atan2(-R[2,0], sy)
        z = 0
    
    return np.degrees([x, y, z])

def opencv_to_unreal_transform(rotation_matrix, translation_vector):
    """
    将OpenCV坐标系转换为虚幻引擎坐标系
    
    OpenCV坐标系: 右手坐标系, X右, Y下, Z前, 单位毫米
    虚幻引擎坐标系: 左手坐标系, X前, Y右, Z上, 单位厘米
    
    转换矩阵:
    [X_unreal]   [0  0  1] [X_opencv]
    [Y_unreal] = [1  0  0] [Y_opencv]
    [Z_unreal]   [0 -1  0] [Z_opencv]
    """
    # 坐标系转换矩阵 (OpenCV -> Unreal)
    coord_transform = np.array([
        [0,  0,  1],  # X_unreal = Z_opencv
        [1,  0,  0],  # Y_unreal = X_opencv  
        [0, -1,  0]   # Z_unreal = -Y_opencv
    ])
    
    # 转换旋转矩阵
    unreal_rotation = coord_transform @ rotation_matrix @ coord_transform.T
    
    # 转换平移向量 (毫米 -> 厘米)
    opencv_translation = translation_vector.flatten()
    unreal_translation = coord_transform @ opencv_translation
    unreal_translation = unreal_translation / 10.0  # mm to cm
    
    return unreal_rotation, unreal_translation

def rotation_matrix_to_unreal_euler(R):
    """
    将旋转矩阵转换为虚幻引擎的欧拉角（度）
    虚幻引擎使用ZYX顺序（Yaw-Pitch-Roll）
    """
    # 虚幻引擎的欧拉角顺序: Yaw(Z) -> Pitch(Y) -> Roll(X)
    sy = math.sqrt(R[0,0] * R[0,0] + R[1,0] * R[1,0])
    
    singular = sy < 1e-6
    
    if not singular:
        # Roll (绕X轴旋转)
        roll = math.atan2(R[2,1], R[2,2])
        # Pitch (绕Y轴旋转)  
        pitch = math.atan2(-R[2,0], sy)
        # Yaw (绕Z轴旋转)
        yaw = math.atan2(R[1,0], R[0,0])
    else:
        roll = math.atan2(-R[1,2], R[1,1])
        pitch = math.atan2(-R[2,0], sy)
        yaw = 0
    
    # 转换为度并返回虚幻引擎的顺序 (Roll, Pitch, Yaw)
    return np.degrees([roll, pitch, yaw])

def display_calibration_results(xml_file_path):
    """显示标定结果"""
    
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    print("=" * 80)
    print("📷 ZED相机-投影仪标定结果")
    print("=" * 80)
    
    # 基本信息
    img_shape = parse_opencv_matrix(root.find('img_shape'))
    rms_error = float(root.find('rms').text)
    successful_captures = int(root.find('successful_captures').text)
    
    print(f"\n📊 标定质量信息:")
    print(f"   图像分辨率: {int(img_shape[1,0])} × {int(img_shape[0,0])}")
    print(f"   RMS重投影误差: {rms_error:.4f} 像素")
    print(f"   成功标定捕获数: {successful_captures}")
    
    # 相机内参
    cam_int = parse_opencv_matrix(root.find('cam_int'))
    cam_dist = parse_opencv_matrix(root.find('cam_dist'))
    
    print(f"\n📷 ZED相机内参:")
    print(f"   焦距 (fx, fy): ({cam_int[0,0]:.2f}, {cam_int[1,1]:.2f})")
    print(f"   主点 (cx, cy): ({cam_int[0,2]:.2f}, {cam_int[1,2]:.2f})")
    print(f"   内参矩阵:")
    print(f"      [{cam_int[0,0]:10.2f}  {cam_int[0,1]:10.2f}  {cam_int[0,2]:10.2f}]")
    print(f"      [{cam_int[1,0]:10.2f}  {cam_int[1,1]:10.2f}  {cam_int[1,2]:10.2f}]")
    print(f"      [{cam_int[2,0]:10.2f}  {cam_int[2,1]:10.2f}  {cam_int[2,2]:10.2f}]")
    
    # 相机畸变参数
    print(f"\n   畸变参数:")
    if cam_dist.size >= 5:
        print(f"      径向畸变 (k1, k2, k3): ({cam_dist[0,0]:.6f}, {cam_dist[1,0]:.6f}, {cam_dist[4,0]:.6f})")
        print(f"      切向畸变 (p1, p2): ({cam_dist[2,0]:.6f}, {cam_dist[3,0]:.6f})")
    else:
        print(f"      畸变系数: {cam_dist.flatten()}")
    
    # 投影仪内参
    proj_int = parse_opencv_matrix(root.find('proj_int'))
    proj_dist = parse_opencv_matrix(root.find('proj_dist'))
    
    print(f"\n🎯 投影仪内参:")
    print(f"   焦距 (fx, fy): ({proj_int[0,0]:.2f}, {proj_int[1,1]:.2f})")
    print(f"   主点 (cx, cy): ({proj_int[0,2]:.2f}, {proj_int[1,2]:.2f})")
    print(f"   内参矩阵:")
    print(f"      [{proj_int[0,0]:10.2f}  {proj_int[0,1]:10.2f}  {proj_int[0,2]:10.2f}]")
    print(f"      [{proj_int[1,0]:10.2f}  {proj_int[1,1]:10.2f}  {proj_int[1,2]:10.2f}]")
    print(f"      [{proj_int[2,0]:10.2f}  {proj_int[2,1]:10.2f}  {proj_int[2,2]:10.2f}]")
    
    # 投影仪畸变参数
    print(f"\n   畸变参数:")
    if proj_dist.size >= 5:
        print(f"      径向畸变 (k1, k2, k3): ({proj_dist[0,0]:.6f}, {proj_dist[0,1]:.6f}, {proj_dist[0,4]:.6f})")
        print(f"      切向畸变 (p1, p2): ({proj_dist[0,2]:.6f}, {proj_dist[0,3]:.6f})")
        if proj_dist.size > 5:
            print(f"      高阶畸变系数: {proj_dist[0,5:].flatten()}")
    else:
        print(f"      畸变系数: {proj_dist.flatten()}")
    
    # 相机-投影仪外参
    rotation = parse_opencv_matrix(root.find('rotation'))
    translation = parse_opencv_matrix(root.find('translation'))
    
    print(f"\n🔄 相机-投影仪外参 (投影仪相对于相机的位姿):")
    print(f"   旋转矩阵:")
    print(f"      [{rotation[0,0]:10.6f}  {rotation[0,1]:10.6f}  {rotation[0,2]:10.6f}]")
    print(f"      [{rotation[1,0]:10.6f}  {rotation[1,1]:10.6f}  {rotation[1,2]:10.6f}]")
    print(f"      [{rotation[2,0]:10.6f}  {rotation[2,1]:10.6f}  {rotation[2,2]:10.6f}]")
    
    # 转换为欧拉角
    euler_angles = rotation_matrix_to_euler(rotation)
    print(f"\n   欧拉角 (绕X, Y, Z轴旋转, 度):")
    print(f"      Roll (X):  {euler_angles[0]:8.2f}°")
    print(f"      Pitch (Y): {euler_angles[1]:8.2f}°")
    print(f"      Yaw (Z):   {euler_angles[2]:8.2f}°")
    
    print(f"\n   平移向量 (毫米):")
    print(f"      X: {translation[0,0]:10.2f} mm")
    print(f"      Y: {translation[1,0]:10.2f} mm")
    print(f"      Z: {translation[2,0]:10.2f} mm")
    
    # 计算距离
    distance = np.linalg.norm(translation)
    print(f"      距离: {distance:10.2f} mm ({distance/1000:.3f} m)")
    
    # 虚幻引擎坐标系转换和显示
    unreal_rotation, unreal_translation = opencv_to_unreal_transform(rotation, translation)
    unreal_euler = rotation_matrix_to_unreal_euler(unreal_rotation)
    
    print(f"\n🎮 虚幻引擎坐标系 (投影仪相对于相机的位姿):")
    print(f"   📝 坐标系说明: 左手坐标系, X前, Y右, Z上, 单位厘米")
    print(f"   📝 可直接复制到虚幻引擎中使用")
    
    print(f"\n   旋转矩阵:")
    print(f"      [{unreal_rotation[0,0]:10.6f}  {unreal_rotation[0,1]:10.6f}  {unreal_rotation[0,2]:10.6f}]")
    print(f"      [{unreal_rotation[1,0]:10.6f}  {unreal_rotation[1,1]:10.6f}  {unreal_rotation[1,2]:10.6f}]")
    print(f"      [{unreal_rotation[2,0]:10.6f}  {unreal_rotation[2,1]:10.6f}  {unreal_rotation[2,2]:10.6f}]")
    
    print(f"\n   欧拉角 (虚幻引擎格式, 度):")
    print(f"      Roll (X):  {unreal_euler[0]:8.2f}°")
    print(f"      Pitch (Y): {unreal_euler[1]:8.2f}°")
    print(f"      Yaw (Z):   {unreal_euler[2]:8.2f}°")
    
    print(f"\n   位置向量 (厘米):")
    print(f"      X: {unreal_translation[0]:10.2f} cm")
    print(f"      Y: {unreal_translation[1]:10.2f} cm")
    print(f"      Z: {unreal_translation[2]:10.2f} cm")
    
    # 计算虚幻坐标系下的距离
    unreal_distance = np.linalg.norm(unreal_translation)
    print(f"      距离: {unreal_distance:10.2f} cm ({unreal_distance/100:.3f} m)")
    
    print(f"\n   🎯 虚幻引擎Transform组件设置:")
    print(f"      Location: X={unreal_translation[0]:.2f}, Y={unreal_translation[1]:.2f}, Z={unreal_translation[2]:.2f}")
    print(f"      Rotation: Roll={unreal_euler[0]:.2f}, Pitch={unreal_euler[1]:.2f}, Yaw={unreal_euler[2]:.2f}")
    print(f"      Scale: X=1.00, Y=1.00, Z=1.00")
    
    # 标定质量评估
    print(f"\n📈 标定质量评估:")
    if rms_error < 1.0:
        quality = "优秀"
        color = "🟢"
    elif rms_error < 2.0:
        quality = "良好"
        color = "🟡"
    elif rms_error < 5.0:
        quality = "一般"
        color = "🟠"
    else:
        quality = "较差"
        color = "🔴"
    
    print(f"   {color} RMS误差: {rms_error:.4f} 像素 ({quality})")
    
    if successful_captures < 3:
        print(f"   ⚠️  警告: 成功标定捕获数较少 ({successful_captures}), 建议增加更多标定姿态")
    
    print("\n" + "=" * 80)
    print("✅ 标定结果显示完成")
    print("=" * 80)

def main():
    """主函数"""
    xml_file = Path("calibration_result_optimized.xml")
    
    if not xml_file.exists():
        print(f"❌ 错误: 找不到标定结果文件 {xml_file}")
        print("请确保标定程序已成功运行并生成了结果文件。")
        return
    
    try:
        display_calibration_results(xml_file)
    except Exception as e:
        print(f"❌ 解析标定结果文件时出错: {e}")
        print("请检查XML文件格式是否正确。")

if __name__ == "__main__":
    main()