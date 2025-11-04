#!/usr/bin/env python3
"""
灰码图案质量检测脚本
- 检查灰码图案是否为二值图(0/255)
- 检查图案数量是否正确（包含白/黑图像）
- 检查所有图案分辨率是否一致
- 检查每张图案是否包含有效条纹（非全黑或全白）
- 输出详细报告和结论

使用方法：
python graycode_pattern_validator.py [--pattern-dir <路径>]
默认路径为: ../graycode_pattern（相对当前脚本所在目录）
"""

import cv2
import numpy as np
from pathlib import Path
import argparse

# 放宽的阈值与梯度检测参数
STD_THR = 2.0
EDGE_THR = 0.0002
SOBEL_KSIZE = 3
GRAD_MAG_THR = 8.0
GRAD_RATIO_THR = 0.001


def is_binary_image(img: np.ndarray) -> bool:
    """判断图像是否为仅包含0和255的二值图"""
    unique_vals = np.unique(img)
    return np.all(np.isin(unique_vals, [0, 255]))


def compute_grad_metrics(img: np.ndarray):
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=SOBEL_KSIZE)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=SOBEL_KSIZE)
    mag = cv2.magnitude(gx, gy)
    mean_grad = float(np.mean(mag))
    grad_ratio = float(np.mean(mag > GRAD_MAG_THR))
    return mean_grad, grad_ratio


def analyze_graycode_patterns(pattern_dir: Path):
    program_name = Path(__file__).stem
    output_dir = Path(__file__).parent / "Data" / program_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== 灰码图案质量检测 ===")
    print(f"图案目录: {pattern_dir}")

    if not pattern_dir.exists():
        print("❌ 图案目录不存在")
        return 1

    files = sorted(pattern_dir.glob("pattern_*.png"))
    if not files:
        print("❌ 未找到任何图案文件")
        return 1

    # 读取所有图像
    imgs = []
    sizes = []
    binary_flags = []
    stripe_flags = []

    for f in files:
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"❌ 无法读取文件: {f.name}")
            return 1
        imgs.append(img)
        sizes.append(img.shape)

        # 二值检查
        is_bin = is_binary_image(img)
        binary_flags.append(is_bin)

        # 条纹存在性检查（放宽阈值 + Sobel梯度）
        std_val = float(np.std(img))
        edges = cv2.Canny(img, 100, 200)
        edge_ratio = np.sum(edges > 0) / edges.size
        mean_grad, grad_ratio = compute_grad_metrics(img)
        has_stripes = ((std_val > STD_THR) or (edge_ratio > EDGE_THR)) or ((mean_grad > GRAD_MAG_THR) and (grad_ratio > GRAD_RATIO_THR))
        stripe_flags.append(has_stripes)

    # 基础统计
    count = len(imgs)
    unique_sizes = set(sizes)

    # 查找全白/全黑图像（不限位置，要求各一张）
    white_indices = [i for i, img in enumerate(imgs) if np.all(img == 255)]
    black_indices = [i for i, img in enumerate(imgs) if np.all(img == 0)]

    white_img = imgs[white_indices[0]] if len(white_indices) >= 1 else None
    black_img = imgs[black_indices[0]] if len(black_indices) >= 1 else None

    white_mean = float(np.mean(white_img)) if white_img is not None else None
    black_mean = float(np.mean(black_img)) if black_img is not None else None
    wb_contrast = (white_mean - black_mean) if (white_mean is not None and black_mean is not None) else None

    # 仅对位平面图案检查条纹（排除全白/全黑）
    bitplane_indices = [i for i in range(count) if i not in set(white_indices + black_indices)]
    stripes_all = all([stripe_flags[i] for i in bitplane_indices]) if bitplane_indices else False

    # 记录失败位平面列表并复制样例图片
    failing_indices = [i for i in bitplane_indices if not stripe_flags[i]]
    failing_list_path = output_dir / "failing_bitplanes.txt"
    failing_dir = output_dir / "failing_bitplanes"
    if failing_indices:
        failing_dir.mkdir(parents=True, exist_ok=True)
        with open(failing_list_path, "w", encoding="utf-8") as fl:
            fl.write("位平面条纹检测失败列表\n")
            fl.write("=" * 40 + "\n")
            for i in failing_indices:
                fpath = files[i]
                img = imgs[i]
                std_val = float(np.std(img))
                edges = cv2.Canny(img, 100, 200)
                edge_ratio = np.sum(edges > 0) / edges.size
                mean_grad, grad_ratio = compute_grad_metrics(img)
                fl.write(f"{fpath.name}: std={std_val:.2f}, edge_ratio={edge_ratio:.4f}, mean_grad={mean_grad:.2f}, grad_ratio={grad_ratio:.4f}\n")
                cv2.imwrite(str(failing_dir / fpath.name), img)

    # 输出报告
    report_path = output_dir / "graycode_pattern_quality_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("灰码图案质量检测报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"图案总数: {count}\n")
        f.write(f"分辨率集合: {sorted(list(unique_sizes))}\n")
        f.write(f"是否全部为二值图: {all(binary_flags)}\n")
        f.write(f"是否存在全白图: {len(white_indices) == 1}\n")
        f.write(f"是否存在全黑图: {len(black_indices) == 1}\n")
        f.write(f"位平面条纹是否全部存在: {stripes_all}\n")
        if wb_contrast is not None:
            f.write(f"白/黑图像平均亮度: 白={white_mean:.1f}, 黑={black_mean:.1f}, 对比度={wb_contrast:.1f}\n")
        if failing_indices:
            f.write(f"\n条纹检测失败的位平面数量: {len(failing_indices)}\n")
            f.write(f"失败列表已保存: {failing_list_path}\n")
            f.write(f"失败图片已复制到: {failing_dir}\n")
        f.write("\n逐文件检测:\n")
        for i, fpath in enumerate(files):
            img = imgs[i]
            std_val = float(np.std(img))
            edges = cv2.Canny(img, 100, 200)
            edge_ratio = np.sum(edges > 0) / edges.size
            mean_grad, grad_ratio = compute_grad_metrics(img)
            f.write(f"  {fpath.name}: 分辨率={img.shape[1]}x{img.shape[0]}, 二值={binary_flags[i]}, 条纹={stripe_flags[i]}, 亮度std={std_val:.1f}, 边缘比例={edge_ratio:.4f}, 梯度均值={mean_grad:.2f}, 梯度比例={grad_ratio:.4f}\n")

    # 控制台输出总结
    print(f"图案总数: {count}")
    print(f"分辨率一致: {len(unique_sizes) == 1}")
    print(f"全部为二值图: {all(binary_flags)}")
    print(f"存在且仅存在一张全白图: {len(white_indices) == 1}")
    print(f"存在且仅存在一张全黑图: {len(black_indices) == 1}")
    print(f"位平面条纹全部存在: {stripes_all}")
    if failing_indices:
        print(f"条纹检测失败的位平面数量: {len(failing_indices)}")
        print(f"失败列表: {failing_list_path}")
        print(f"失败图片目录: {failing_dir}")
    if wb_contrast is not None:
        print(f"白/黑对比度: {wb_contrast:.1f} (白={white_mean:.1f}, 黑={black_mean:.1f})")
        if wb_contrast < 30:
            print("⚠️ 白/黑对比度较低，可能影响拍摄时的解码效果")
        if wb_contrast < 0:
            print("❌ 白/黑亮度关系颠倒，请检查生成顺序或文件命名")

    # 合格判定
    ok = True
    if len(unique_sizes) != 1:
        ok = False
        print("❌ 图案分辨率不一致")
    if not all(binary_flags):
        ok = False
        print("❌ 存在非二值图案（不是仅0/255）")
    if count < 10:
        ok = False
        print("❌ 图案数量过少（应包含多个位平面以及白/黑）")
    if len(white_indices) != 1 or len(black_indices) != 1:
        ok = False
        print("❌ 未检测到且仅检测到一张全白与一张全黑图案")
    if not stripes_all:
        ok = False
        print("❌ 位平面条纹检测未全部通过（排除全白/全黑）")

    print("\n=== 结论 ===")
    if ok:
        print("✓ 灰码图案质量合格，适合用于投影拍摄")
    else:
        print("❌ 灰码图案质量不合格，请根据上方提示修正")

    print(f"\n详细报告已保存到: {report_path}")
    return 0 if ok else 2


def main():
    parser = argparse.ArgumentParser(description="灰码图案质量检测")
    parser.add_argument("--pattern-dir", type=str, default=str(Path(__file__).resolve().parent.parent / "graycode_pattern"), help="灰码图案目录")
    args = parser.parse_args()

    pattern_dir = Path(args.pattern_dir)
    exit_code = analyze_graycode_patterns(pattern_dir)
    exit(exit_code)


if __name__ == "__main__":
    main()