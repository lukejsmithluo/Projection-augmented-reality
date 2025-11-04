#!/usr/bin/env python3
"""
棋盘格识别检测脚本
- 自动查找捕获目录 capture_*/graycode_*.png
- 自动选择更亮的图像作为“白图”进行角点检测
- 检测棋盘格角点并给出结果与标注图
- 支持自定义棋盘格内角点数量

使用方法：
python captured_chessboard_checker.py [--search-dir <目录>] [--rows <内角点行数>] [--cols <内角点列数>]
默认搜索目录优先：
1) ../sample_data （在procam-calibration根目录下示例数据）
2) 当前脚本所在目录的父目录（ZED_Projector_Calibration）
"""

import cv2
import numpy as np
from pathlib import Path
import argparse


def find_capture_dirs(base_dir: Path):
    """在base_dir下查找所有capture_*目录"""
    return sorted([d for d in base_dir.glob("capture_*") if d.is_dir()])


def pick_white_black_images(files):
    """从graycode序列中挑选白/黑图像（根据平均亮度自动判断）"""
    if len(files) < 2:
        return None, None
    # 尝试最后两张作为候选
    candidates = files[-2:]
    imgs = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in candidates]
    means = [float(np.mean(im)) for im in imgs]
    # 更亮者作为白图，另一张为黑图
    white_idx = int(np.argmax(means))
    black_idx = 1 - white_idx
    return candidates[white_idx], candidates[black_idx]


def analyze_capture_dir(capture_dir: Path, pattern_size):
    program_name = Path(__file__).stem
    output_dir = Path(__file__).parent / "Data" / program_name / capture_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== 检测目录: {capture_dir} ===")
    files = sorted(capture_dir.glob("graycode_*.png"))
    if not files:
        print("[FAIL] 未找到graycode图像")
        return False

    # 选择白/黑图像
    white_file, black_file = pick_white_black_images(files)
    if white_file is None or black_file is None:
        print("[FAIL] 无法选择白/黑图像")
        return False

    white_img = cv2.imread(str(white_file), cv2.IMREAD_GRAYSCALE)
    black_img = cv2.imread(str(black_file), cv2.IMREAD_GRAYSCALE)
    white_mean = float(np.mean(white_img))
    black_mean = float(np.mean(black_img))
    contrast = white_mean - black_mean

    print(f"白图: {white_file.name}, 平均亮度={white_mean:.1f}")
    print(f"黑图: {black_file.name}, 平均亮度={black_mean:.1f}")
    print(f"白黑对比度: {contrast:.1f}")
    if contrast < 20:
        print("[WARN] 白/黑对比度较低，可能影响角点检测")

    # 尝试检测棋盘格角点
    ret, corners = cv2.findChessboardCorners(white_img, pattern_size)

    if not ret:
        # 提高对比度尝试
        white_eq = cv2.equalizeHist(white_img)
        ret, corners = cv2.findChessboardCorners(white_eq, pattern_size)
        if ret:
            print("[OK] 通过直方图均衡化后检测到角点")
            white_vis = white_eq.copy()
        else:
            print("[FAIL] 未检测到棋盘格角点")
            white_vis = white_img.copy()
    else:
        print(f"[OK] 检测到 {len(corners)} 个角点")
        white_vis = white_img.copy()

    # 角点精细化与标注
    if ret:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        gray = white_img if white_img.ndim == 2 else cv2.cvtColor(white_img, cv2.COLOR_BGR2GRAY)
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        vis = cv2.cvtColor(white_vis, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(vis, pattern_size, corners_refined, True)
        cv2.imwrite(str(output_dir / "chessboard_annotated.png"), vis)
        print(f"已保存标注图: {output_dir / 'chessboard_annotated.png'}")
        return True
    else:
        # 保存增强后的白图缩略图以便查看
        thumb = cv2.resize(white_vis, (min(800, white_vis.shape[1]), min(600, white_vis.shape[0])))
        cv2.imwrite(str(output_dir / "white_image_preview.png"), thumb)
        print(f"已保存白图预览: {output_dir / 'white_image_preview.png'}")
        print("建议: 提高投影亮度、降低环境光、确保棋盘朝向投影区域且对焦清晰")
        return False


def main():
    parser = argparse.ArgumentParser(description="棋盘格识别检测")
    parser.add_argument("--search-dir", type=str, default=None, help="捕获目录的上级目录（包含多个capture_*）")
    parser.add_argument("--rows", type=int, default=9, help="棋盘格内角点行数（垂直）")
    parser.add_argument("--cols", type=int, default=7, help="棋盘格内角点列数（水平）")
    args = parser.parse_args()

    # 默认搜索目录：优先sample_data，其次父目录
    if args.search_dir is not None:
        base_dir = Path(args.search_dir)
    else:
        candidate1 = Path(__file__).resolve().parent.parent / "sample_data"
        candidate2 = Path(__file__).resolve().parent.parent
        base_dir = candidate1 if candidate1.exists() else candidate2

    print(f"搜索目录: {base_dir}")

    capture_dirs = find_capture_dirs(base_dir)
    if not capture_dirs:
        print("[FAIL] 未找到任何capture_*目录")
        return 1

    pattern_size = (args.cols, args.rows)  # OpenCV使用(列, 行)
    any_success = False
    for cdir in capture_dirs:
        ok = analyze_capture_dir(cdir, pattern_size)
        any_success = any_success or ok

    print("\n=== 结论 ===")
    if any_success:
        print("[OK] 至少一个拍摄序列可以成功检测到棋盘格")
        return 0
    else:
        print("[FAIL] 所有拍摄序列均未检测到棋盘格，请根据提示调整拍摄条件")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())