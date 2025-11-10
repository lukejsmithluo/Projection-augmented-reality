# coding: utf-8
import os
import sys
import time
import glob
import json
import ctypes
import subprocess
from pathlib import Path
from datetime import datetime

import cv2

# 尝试导入ZED SDK
try:
    import pyzed.sl as sl
except Exception as e:
    print("[错误] 未能导入 ZED Python SDK (pyzed.sl)。请确保已安装 Stereolabs ZED SDK 和 Python API。")
    print(e)
    sys.exit(1)

# 监视器枚举（Windows）
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(RECT), ctypes.c_double)

monitors = []

def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
    r = lprcMonitor.contents
    width = r.right - r.left
    height = r.bottom - r.top
    monitors.append({"left": r.left, "top": r.top, "width": width, "height": height})
    return 1

# Tk 用于投影显示和文件夹选择
import tkinter as tk
from tkinter import filedialog

class ProjectorWindow:
    def __init__(self, monitor_rect):
        self.root = tk.Tk()
        self.root.title("Graycode Projector")
        self.root.configure(bg="black")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        # 放置到指定显示器位置与大小
        x, y = monitor_rect["left"], monitor_rect["top"]
        w, h = monitor_rect["width"], monitor_rect["height"]
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.canvas = tk.Canvas(self.root, width=w, height=h, highlightthickness=0, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.photo = None
        self.image_id = None
        # 预创建一个全黑背景
        self.canvas.create_rectangle(0, 0, w, h, fill="black", outline="black")
        self.root.update()

    def show_image(self, image_path):
        # 添加调试信息
        print(f"[调试] ProjectorWindow.show_image() 接收到路径: {image_path}")
        print(f"[调试] 路径类型: {type(image_path)}")
        print(f"[调试] 文件是否存在: {Path(image_path).exists()}")
        
        # 使用 Tk 的 PhotoImage 直接加载 PNG
        try:
            self.photo = tk.PhotoImage(file=str(image_path))
            print(f"[调试] 成功加载图片: {Path(image_path).name}")
        except Exception as e:
            print(f"[错误] 加载图片失败: {e}")
            return
            
        # 将图像放在左上角（不缩放），其余区域保持黑色
        if self.image_id is not None:
            self.canvas.delete(self.image_id)
        self.image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
        self.root.update_idletasks()
        self.root.update()

    def clear(self):
        self.canvas.delete("all")
        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        self.root.destroy()

# ZED 相机管理
class ZEDCameraManager:
    def __init__(self):
        self.zed = sl.Camera()
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD2K  # 2K 模式
        init_params.camera_fps = 15
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init_params.coordinate_units = sl.UNIT.MILLIMETER
        status = self.zed.open(init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            print(f"[错误] 打开ZED相机失败: {status}")
            raise RuntimeError("ZED camera open failed")
        self.runtime = sl.RuntimeParameters()
        self.image_mat = sl.Mat()

    def save_intrinsics_json(self, json_path: Path):
        """保存相机内参到JSON文件"""
        try:
            # 根据Stereolabs官方文档获取相机信息和标定参数
            camera_info = self.zed.get_camera_information()
            camera_config = camera_info.camera_configuration
            calibration_params = camera_config.calibration_parameters
            
            # 获取分辨率
            resolution = camera_config.resolution
            width = int(resolution.width)
            height = int(resolution.height)
            print(f"[信息] 相机分辨率: {width}x{height}")
            
            # 获取左相机的标定参数
            left_cam = calibration_params.left_cam
            
            # 焦距参数
            fx = float(left_cam.fx)
            fy = float(left_cam.fy)
            
            # 主点参数
            cx = float(left_cam.cx)
            cy = float(left_cam.cy)
            
            # 镜头畸变参数
            # k1, k2, k3: 径向畸变系数
            # p1, p2: 切向畸变系数
            k1 = float(left_cam.disto[0])
            k2 = float(left_cam.disto[1])
            p1 = float(left_cam.disto[2])
            p2 = float(left_cam.disto[3])
            k3 = float(left_cam.disto[4])
            
            # 视场角信息
            h_fov = float(left_cam.h_fov)  # 水平视场角
            v_fov = float(left_cam.v_fov)  # 垂直视场角
            d_fov = float(left_cam.d_fov)  # 对角线视场角
            
            print(f"[信息] 成功获取ZED相机完整内参:")
            print(f"  焦距: fx={fx:.2f}, fy={fy:.2f}")
            print(f"  主点: cx={cx:.2f}, cy={cy:.2f}")
            print(f"  径向畸变: k1={k1:.6f}, k2={k2:.6f}, k3={k3:.6f}")
            print(f"  切向畸变: p1={p1:.6f}, p2={p2:.6f}")
            print(f"  视场角: 水平={h_fov:.1f}°, 垂直={v_fov:.1f}°, 对角线={d_fov:.1f}°")
            
            # 构建相机矩阵 (3x3)
            P = [
                fx, 0, cx,
                0, fy, cy,
                0, 0, 1
            ]
            
            # 畸变参数 (5个系数: k1, k2, p1, p2, k3)
            distortion = [k1, k2, p1, p2, k3]
            
            # 保存完整的相机配置信息
            data = {
                "camera": {
                    "P": P,
                    "distortion": distortion,
                    "other properties will be ignored": "",
                    "width": width,
                    "height": height,
                    "intrinsics": {
                        "fx": fx,
                        "fy": fy,
                        "cx": cx,
                        "cy": cy
                    },
                    "distortion_coefficients": {
                        "k1": k1,
                        "k2": k2,
                        "k3": k3,
                        "p1": p1,
                        "p2": p2
                    },
                    "field_of_view": {
                        "horizontal_deg": h_fov,
                        "vertical_deg": v_fov,
                        "diagonal_deg": d_fov
                    },
                    "camera_model": "ZED",
                    "sdk_version": "4.x",
                    "calibration_source": "factory_calibration"
                }
            }
            
            # 保存到JSON文件
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print(f"[信息] 相机内参已保存到: {json_path} (使用ZED工厂标定参数)")
                
        except Exception as e:
            print(f"[错误] 获取ZED相机内参失败: {e}")
            print("[警告] 回退到默认参数")
            
            # 回退方案：使用默认参数
            width, height = 2208, 1242
            fx = fy = width * 0.7
            cx = width / 2.0
            cy = height / 2.0
            
            data = {
                "camera": {
                    "P": [
                        fx, 0, cx,
                        0, fy, cy,
                        0, 0, 1
                    ],
                    "distortion": [0.0, 0.0, 0.0, 0.0, 0.0],
                    "other properties will be ignored": "",
                    "width": width,
                    "height": height,
                    "calibration_source": "default_fallback"
                }
            }
            
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print(f"[信息] 相机内参已保存到: {json_path} (使用默认值)")

    def capture_left_gray(self):
        # 等待抓取成功
        grab_status = self.zed.grab(self.runtime)
        if grab_status != sl.ERROR_CODE.SUCCESS:
            # 再试一次，简单重试
            time.sleep(0.02)
            grab_status = self.zed.grab(self.runtime)
            if grab_status != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(f"ZED grab failed: {grab_status}")
        self.zed.retrieve_image(self.image_mat, sl.VIEW.LEFT)
        img_rgba = self.image_mat.get_data()  # H x W x 4 BGRA
        gray = cv2.cvtColor(img_rgba, cv2.COLOR_BGRA2GRAY)
        return gray

    def close(self):
        self.image_mat.free()
        self.zed.close()


def enumerate_monitors():
    global monitors
    monitors = []
    user32 = ctypes.windll.user32
    user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_monitor_enum_proc), 0)
    return monitors


def ask_user_monitor_choice(monitors_list):
    print("可用显示器列表：")
    for idx, m in enumerate(monitors_list):
        print(f"[{idx}] left={m['left']}, top={m['top']}, width={m['width']}, height={m['height']}")
    while True:
        try:
            sel = int(input("请选择用于投影的显示器索引：").strip())
            if 0 <= sel < len(monitors_list):
                return monitors_list[sel]
            else:
                print("索引无效，请重新输入。")
        except Exception:
            print("输入无效，请输入整数索引。")


def select_graycode_folder():
    """使用GUI选择格雷码图案文件夹"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    root.attributes('-topmost', True)  # 置顶
    
    folder_path = filedialog.askdirectory(
        title="选择格雷码图案文件夹",
        initialdir="E:/OrganizedWork/susTech/HCI/XProjection/AutoProjectionProject/Temp/procam-calibration/ZED_Projector_Calibration"
    )
    root.destroy()
    return folder_path if folder_path else None


def main():
    print("=== ZED 2i 投影-拍摄-标定程序 ===")
    # 将输出与标定脚本目录指向当前仓库的 Projector-Calibration 目录
    repo_root = Path(__file__).resolve().parents[2]  # .../Projector-Calibration
    base_dir = repo_root
    calibrate_py = base_dir / "calibrate_optimized.py"
    camera_json = base_dir / "camera_config.json"

    # 初始化相机并保存内参
    zed_mgr = ZEDCameraManager()
    try:
        zed_mgr.save_intrinsics_json(camera_json)
    except Exception as e:
        zed_mgr.close()
        raise

    # 显示器选择
    mons = enumerate_monitors()
    if not mons:
        print("[错误] 未检测到显示器信息。")
        zed_mgr.close()
        return
    mon = ask_user_monitor_choice(mons)
    proj_win = ProjectorWindow(mon)

    # 用户选择格雷码图案文件夹
    gray_folder = select_graycode_folder()
    if not gray_folder:
        print("[错误] 未选择格雷码图案文件夹。")
        proj_win.destroy()
        zed_mgr.close()
        return
    
    gray_dir = Path(gray_folder)
    if not gray_dir.exists():
        print(f"[错误] 格雷码图案文件夹不存在: {gray_folder}")
        proj_win.destroy()
        zed_mgr.close()
        return
    
    print(f"[信息] 使用格雷码图案文件夹：{gray_folder}")
    
    # 获取格雷码图案文件列表，严格按照数字顺序
    pattern_files = []
    
    # 首先尝试查找 pattern_*.png 文件（优先使用原始图案）
    pattern_found = False
    for i in range(100):  # 最多检查100个文件
        pattern_file = gray_dir / f"pattern_{i:02d}.png"
        if pattern_file.exists():
            pattern_files.append(str(pattern_file))
            pattern_found = True
        elif pattern_found:  # 如果之前找到过文件但当前文件不存在，说明序列结束
            break
    
    # 如果没有找到 pattern_*.png，尝试 graycode_*.png
    if not pattern_files:
        for i in range(100):  # 最多检查100个文件
            graycode_file = gray_dir / f"graycode_{i:02d}.png"
            if graycode_file.exists():
                pattern_files.append(str(graycode_file))
            elif pattern_files:  # 如果之前找到过文件但当前文件不存在，说明序列结束
                break
    
    if len(pattern_files) == 0:
        print("[错误] 未在指定文件夹中找到 pattern_XX.png 或 graycode_XX.png 格式的文件。")
        proj_win.destroy()
        zed_mgr.close()
        return
    
    print(f"[信息] 检测到图案数量: {len(pattern_files)}")
    print(f"[信息] 图案文件范围: {Path(pattern_files[0]).name} 到 {Path(pattern_files[-1]).name}")
    
    # 调试：显示前5个文件的完整路径
    print(f"[调试] 前5个图案文件的完整路径:")
    for i, file_path in enumerate(pattern_files[:5]):
        print(f"  [{i}] {file_path}")
        print(f"      文件存在: {Path(file_path).exists()}")
    
    # 验证文件顺序
    for i, file_path in enumerate(pattern_files):
        expected_num = i
        file_name = Path(file_path).name
        if 'pattern_' in file_name:
            actual_num = int(file_name.split('_')[1].split('.')[0])
        elif 'graycode_' in file_name:
            actual_num = int(file_name.split('_')[1].split('.')[0])
        else:
            print(f"[警告] 文件名格式不符合预期: {file_name}")
            continue
            
        if actual_num != expected_num:
            print(f"[警告] 文件顺序不连续: 期望 {expected_num:02d}，实际 {actual_num:02d}")
            break

    # 从选定的显示器获取实际投影分辨率
    proj_width, proj_height = mon["width"], mon["height"]
    print(f"[信息] 投影分辨率: {proj_height} x {proj_width}")
    
    # 验证格雷码图案文件是否可读（仅用于验证）
    sample_img = cv2.imread(pattern_files[0], cv2.IMREAD_GRAYSCALE)
    if sample_img is None:
        print("[错误] 无法读取样例图案。")
        proj_win.destroy()
        zed_mgr.close()
        return
    pattern_height, pattern_width = sample_img.shape[0], sample_img.shape[1]
    print(f"[信息] 格雷码图案分辨率: {pattern_height} x {pattern_width}")
    
    # 如果图案分辨率与投影分辨率不匹配，给出警告
    if pattern_width != proj_width or pattern_height != proj_height:
        print(f"[警告] 格雷码图案分辨率({pattern_width}x{pattern_height})与投影分辨率({proj_width}x{proj_height})不匹配")
        print("[警告] 将使用指定的投影分辨率进行标定")

    # 轮次输入
    try:
        rounds = int(input("请输入要执行的拍摄轮次（整数）：").strip())
    except Exception:
        print("[错误] 轮次输入无效。")
        proj_win.destroy()
        zed_mgr.close()
        return
    if rounds <= 0:
        print("[错误] 轮次必须为正整数。")
        proj_win.destroy()
        zed_mgr.close()
        return

    # 拍摄轮次，保存到 ./capture_0, ./capture_1, ...（相对于 calibrate.py 所在目录）
    for r in range(rounds):
        cap_dir = base_dir / f"capture_{r}"
        cap_dir.mkdir(parents=True, exist_ok=True)
        print(f"=== 开始第 {r+1} 轮拍摄，保存到 {cap_dir} ===")
        for idx, img_path in enumerate(pattern_files):
            # 获取原始图案文件名用于显示对应关系
            pattern_name = Path(img_path).name
            print(f"[调试] 准备投影第 {idx+1} 张图片:")
            print(f"  完整路径: {img_path}")
            print(f"  文件名: {pattern_name}")
            print(f"  文件存在: {Path(img_path).exists()}")
            
            proj_win.show_image(img_path)
            # 显示后稍作等待，保证显示器刷新与相机曝光稳定
            time.sleep(0.5)  # 增加等待时间确保拍摄稳定
            gray = zed_mgr.capture_left_gray()
            # 转换文件名为标定程序期望的格式 graycode_XX.png
            save_name = f"graycode_{idx:02d}.png"
            save_path = cap_dir / save_name
            cv2.imwrite(str(save_path), gray)
            print(f"  [{idx+1}/{len(pattern_files)}] 投影 {pattern_name} -> 拍摄 {save_name}")
        if r < rounds - 1:  # 修改条件以适应从0开始的索引
            input("请改变标定图案姿态后，按回车开始下一轮...")

    # 清屏并关闭窗口
    proj_win.clear()
    proj_win.destroy()

    # 运行标定程序
    print("=== 开始运行标定程序 ===")
    # 我们的棋盘格角点数为 11 8（横向11，纵向8）对应12x9格子
    chess_vert = 8  # 纵向内角点数（9格-1）
    chess_hori = 11  # 横向内角点数（12格-1）
    chess_block_size = 15  # 每个棋盘格大小为15mm
    graycode_step = 1
    black_thr = 40
    white_thr = 5
    cmd = [
        sys.executable, str(calibrate_py),
        str(proj_height), str(proj_width),
        str(chess_vert), str(chess_hori),
        str(chess_block_size), str(graycode_step),
        "-black_thr", str(black_thr),
        "-white_thr", str(white_thr),
        "-camera", str(camera_json)
    ]
    print("调用命令:")
    print(" ", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=str(base_dir), check=False)
    except Exception as e:
        print(f"[错误] 调用标定程序失败: {e}")
    finally:
        zed_mgr.close()
        print("=== 程序结束 ===")


if __name__ == '__main__':
    main()