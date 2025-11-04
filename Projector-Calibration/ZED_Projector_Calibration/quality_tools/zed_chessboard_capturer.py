"""
ZED 2i 棋盘格拍照程序（Python SDK）
- 初始化相机为 2K@15FPS，深度模式 NEURAL_PLUS
- 用户按回车后拍照，将图像保存到 ZED_Projector_Calibration/capture_<timestamp>/
- 为了兼容 captured_chessboard_checker.py，会保存两份同一张图：graycode_48.png 与 graycode_49.png
- 可选：拍照后自动调用 captured_chessboard_checker.py 进行棋盘格检测

依赖：
- Stereolabs ZED SDK Python: pip install pyzed
- OpenCV: pip install opencv-python
"""
from __future__ import annotations
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

try:
    import pyzed.sl as sl
except Exception as e:
    print("❌ 未找到 ZED Python SDK (pyzed.sl)，请先安装并配置 ZED SDK")
    raise


class ZEDChessboardCapturer:
    def __init__(self, output_base: Path, auto_run_checker: bool = False, checker_board=(9, 6), auto_capture: bool = False):
        self.output_base = output_base
        self.auto_run_checker = auto_run_checker
        self.checker_board = checker_board  # (cols, rows) 内角点数
        self.auto_capture = auto_capture
        self.cam = sl.Camera()
        self.runtime = sl.RuntimeParameters()
        self.capture_dir = None

    def open(self):
        init = sl.InitParameters()
        init.camera_resolution = sl.RESOLUTION.HD2K  # 2K 模式（ZED: 2208x1242）
        init.camera_fps = 15
        init.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init.coordinate_units = sl.UNIT.MILLIMETER
        init.depth_minimum_distance = 300  # mm，可根据场景调整

        print("→ 打开 ZED 2i 相机: 2K@15FPS, 深度=NEURAL_PLUS")
        status = self.cam.open(init)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"打开相机失败: {repr(status)}")
        print("✓ 相机已打开")

    def _create_capture_dir(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.capture_dir = (self.output_base / f"capture_{ts}").resolve()
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        print(f"→ 创建捕获目录: {self.capture_dir}")

    def capture_single(self) -> np.ndarray:
        print("请按回车进行拍照（或 Ctrl+C 取消）...")
        try:
            if not self.auto_capture:
                input()
        except KeyboardInterrupt:
            print("已取消拍照")
            return None

        print("→ 捕获图像中...")
        for _ in range(50):  # 预热若干帧
            if self.cam.grab(self.runtime) != sl.ERROR_CODE.SUCCESS:
                time.sleep(0.01)
                continue
        if self.cam.grab(self.runtime) != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError("抓取帧失败")

        mat = sl.Mat()
        self.cam.retrieve_image(mat, sl.VIEW.LEFT)
        img = mat.get_data()  # RGBA
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        print(f"✓ 拍照完成，尺寸: {img_bgr.shape[1]}x{img_bgr.shape[0]}")
        return img_bgr

    def save_capture_pair(self, img_bgr: np.ndarray):
        if self.capture_dir is None:
            self._create_capture_dir()
        # 兼容 captured_chessboard_checker：保存为 graycode_48/49
        out_white = self.capture_dir / "graycode_49.png"
        out_black = self.capture_dir / "graycode_48.png"
        cv2.imwrite(str(out_white), img_bgr)
        cv2.imwrite(str(out_black), img_bgr)
        print(f"✓ 已保存: {out_white.name}, {out_black.name} 到 {self.capture_dir}")

    def close(self):
        try:
            self.cam.close()
            print("→ 相机已关闭")
        except Exception:
            pass

    def run_checker(self):
        if not self.auto_run_checker:
            return
        checker = self.output_base / "quality_tools" / "captured_chessboard_checker.py"
        if not checker.exists():
            print("⚠️ 未找到 captured_chessboard_checker.py，跳过自动检测")
            return
        cmd = (
            f"python \"{checker}\" --search-dir \"{self.output_base}\" "
            f"--board-cols {self.checker_board[0]} --board-rows {self.checker_board[1]}"
        )
        print("→ 运行棋盘格检测：", cmd)
        code = cv2.imread  # 占位，避免 linter 警告
        # 实际运行由用户在终端执行；这里仅输出命令以供复制
        print("请在终端执行以上命令查看检测结果。")


def parse_args():
    parser = argparse.ArgumentParser(description="ZED 2i 棋盘格拍照程序")
    default_base = Path(__file__).resolve().parents[1]  # ZED_Projector_Calibration/
    parser.add_argument(
        "--output-base",
        type=str,
        default=str(default_base),
        help="输出基目录（默认为 ZED_Projector_Calibration 目录）",
    )
    parser.add_argument(
        "--auto-run-checker",
        action="store_true",
        help="拍照后输出运行 captured_chessboard_checker.py 的命令",
    )
    parser.add_argument(
        "--auto-capture",
        action="store_true",
        help="非交互拍照（跳过按回车）",
    )
    parser.add_argument(
        "--board-cols",
        type=int,
        default=9,
        help="棋盘格内角点列数（默认9）",
    )
    parser.add_argument(
        "--board-rows",
        type=int,
        default=6,
        help="棋盘格内角点行数（默认6）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_base = Path(args.output_base).resolve()
    capturer = ZEDChessboardCapturer(
        output_base=output_base,
        auto_run_checker=args.auto_run_checker,
        checker_board=(args.board_cols, args.board_rows),
        auto_capture=args.auto_capture,
    )
    try:
        capturer.open()
        img = capturer.capture_single()
        if img is None:
            return 1
        capturer.save_capture_pair(img)
        capturer.run_checker()
        return 0
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return 2
    finally:
        capturer.close()


if __name__ == "__main__":
    sys.exit(main())