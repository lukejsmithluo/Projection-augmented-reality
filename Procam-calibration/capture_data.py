# coding: UTF-8

import os
import sys
import time
import argparse
import cv2
import numpy as np
import subprocess
import platform

try:
    import pyzed.sl as sl
except Exception:
    sl = None

try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None


def _is_windows():
    return platform.system().lower() == "windows"


def _run_powershell(command):
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout or ""
    except Exception:
        return ""


def _list_camera_friendly_names_windows():
    if not _is_windows():
        return []
    out = _run_powershell(
        "Get-PnpDevice -Class Camera -Status OK | Select-Object -ExpandProperty FriendlyName"
    )
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines


def _probe_opencv_cameras(max_indices=12):
    candidates = []
    for idx in range(max_indices):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if _is_windows() else cv2.CAP_ANY)
        if not cap.isOpened():
            cap.release()
            continue
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None and frame.size > 0:
            candidates.append(idx)
    return candidates


def _dedupe_resolutions(resolutions):
    seen = set()
    out = []
    for w, h in resolutions:
        key = (int(w), int(h))
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _probe_supported_resolutions_opencv(device_index):
    candidate_res = [
        (3840, 2160),
        (2560, 1440),
        (1920, 1080),
        (1600, 900),
        (1280, 720),
        (1024, 768),
        (800, 600),
        (640, 480),
        (320, 240),
    ]
    supported = []
    cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW if _is_windows() else cv2.CAP_ANY)
    if not cap.isOpened():
        cap.release()
        return []

    for w, h in candidate_res:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
        ok = False
        frame = None
        for _ in range(10):
            ok, frame = cap.read()
            if ok and frame is not None and frame.size > 0:
                break
        if not ok or frame is None:
            continue
        actual_h, actual_w = frame.shape[:2]
        supported.append((actual_w, actual_h))

    cap.release()
    return _dedupe_resolutions(supported)


def _choose_from_list(title, items):
    print(f"\n{title}")
    for i, item in enumerate(items):
        print(f"  [{i}] {item}")
    while True:
        try:
            s = input("请输入序号: ").strip()
        except KeyboardInterrupt:
            raise
        if s.isdigit():
            idx = int(s)
            if 0 <= idx < len(items):
                return idx
        print("输入无效，请重试。")


def _preview_camera_opencv(cap, window_name="Camera Preview"):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    print("预览窗口已打开：按 Enter 确认；按 q 或 Esc 取消。")
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 13:
            cv2.destroyWindow(window_name)
            return True
        if key == 27 or key == ord("q"):
            cv2.destroyWindow(window_name)
            return False


def _preview_camera_zed(zed, view, window_name="Camera Preview"):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    print("预览窗口已打开：按 Enter 确认；按 q 或 Esc 取消。")
    image_zed = sl.Mat()
    while True:
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_zed, view)
            frame = image_zed.get_data()
            if frame is None:
                continue
            if frame.shape[-1] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 13:
            cv2.destroyWindow(window_name)
            return True
        if key == 27 or key == ord("q"):
            cv2.destroyWindow(window_name)
            return False

class ProcamCapturer:
    """
    Automated ProCam calibration data acquisition system.
    Controls a projector to display Gray Code patterns and triggers a ZED camera to capture images.
    """

    def __init__(
        self,
        proj_width,
        proj_height,
        graycode_step=1,
        monitor_index=1,
        output_dir=".",
        pattern_dir=None,
        camera_mode="auto",
    ):
        self.proj_width = proj_width
        self.proj_height = proj_height
        self.graycode_step = graycode_step
        self.monitor_index = monitor_index
        self.output_dir = output_dir
        self.pattern_dir = pattern_dir
        self.camera_mode = camera_mode

        self.zed = None
        self.zed_view = None
        self.opencv_cap = None
        self.window_name = "Projector Pattern"
        self.patterns = []
        
        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _initialize_zed(self):
        if sl is None:
            print("Error: pyzed is not available, cannot use ZED mode.")
            sys.exit(1)

        zed = sl.Camera()

        resolutions = [
            ("HD2K (2208x1242)", sl.RESOLUTION.HD2K),
            ("HD1080 (1920x1080)", sl.RESOLUTION.HD1080),
            ("HD720 (1280x720)", sl.RESOLUTION.HD720),
            ("VGA (672x376)", sl.RESOLUTION.VGA),
        ]

        res_idx = _choose_from_list("请选择 ZED 分辨率:", [r[0] for r in resolutions])
        eye_idx = _choose_from_list("请选择 ZED 使用哪一目:", ["LEFT", "RIGHT"])
        zed_view = sl.VIEW.LEFT if eye_idx == 0 else sl.VIEW.RIGHT

        init_params = sl.InitParameters()
        init_params.camera_resolution = resolutions[res_idx][1]
        init_params.camera_fps = 15
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init_params.coordinate_units = sl.UNIT.MILLIMETER

        err = zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Error opening ZED camera: {err}")
            sys.exit(1)

        self.zed = zed
        self.zed_view = zed_view
        print(f"Camera initialized: {self.zed.get_camera_information().camera_model}")
        ok = _preview_camera_zed(self.zed, self.zed_view)
        if not ok:
            print("用户取消。")
            sys.exit(0)

    def _initialize_opencv(self):
        friendly = _list_camera_friendly_names_windows()
        indices = _probe_opencv_cameras()
        if len(indices) == 0:
            print("Error: no camera device found by OpenCV.")
            sys.exit(1)

        items = []
        for i, idx in enumerate(indices):
            name = friendly[i] if i < len(friendly) else "Unknown Camera"
            items.append(f"{name} (OpenCV index {idx})")

        pick = _choose_from_list("检测到以下相机设备:", items)
        device_index = indices[pick]

        resolutions = _probe_supported_resolutions_opencv(device_index)
        if len(resolutions) == 0:
            resolutions = [(1280, 720), (1920, 1080), (640, 480)]
        res_items = [f"{w}x{h}" for (w, h) in resolutions]
        res_pick = _choose_from_list("请选择相机分辨率:", res_items)
        w, h = resolutions[res_pick]

        cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW if _is_windows() else cv2.CAP_ANY)
        if not cap.isOpened():
            cap.release()
            print("Error: failed to open camera.")
            sys.exit(1)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
        ok = _preview_camera_opencv(cap)
        if not ok:
            cap.release()
            print("用户取消。")
            sys.exit(0)

        self.opencv_cap = cap

    def initialize_camera(self):
        if self.camera_mode not in {"auto", "zed", "opencv"}:
            print("Error: invalid camera_mode.")
            sys.exit(1)

        if self.camera_mode == "zed":
            self._initialize_zed()
            return
        if self.camera_mode == "opencv":
            self._initialize_opencv()
            return

        modes = []
        if sl is not None:
            modes.append("ZED (pyzed)")
        modes.append("Generic Camera (OpenCV)")
        mode_idx = _choose_from_list("请选择相机类型:", modes)
        if sl is not None and mode_idx == 0:
            self._initialize_zed()
        else:
            self._initialize_opencv()

    def generate_patterns(self):
        """Generate Gray Code patterns or load from directory."""
        if self.pattern_dir:
            if os.path.exists(self.pattern_dir):
                print(f"Loading patterns from {self.pattern_dir}...")
                import glob
                files = sorted(glob.glob(os.path.join(self.pattern_dir, "pattern_*.png")))
                if not files:
                    print(f"No 'pattern_*.png' files found in {self.pattern_dir}")
                    sys.exit(1)
                
                self.patterns = []
                for f in files:
                    img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        print(f"Failed to load {f}")
                        sys.exit(1)
                    
                    if img.shape[1] != self.proj_width or img.shape[0] != self.proj_height:
                        print(f"Error: Pattern {os.path.basename(f)} size ({img.shape[1]}x{img.shape[0]}) "
                              f"does not match projector configuration ({self.proj_width}x{self.proj_height})")
                        sys.exit(1)
                        
                    self.patterns.append(img)

                # Check if we need to append White/Black patterns
                gc_height = int((self.proj_height - 1) / self.graycode_step) + 1
                gc_width = int((self.proj_width - 1) / self.graycode_step) + 1
                try:
                    graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
                    expected_count = graycode.getNumberOfPatternImages()
                    
                    if len(self.patterns) == expected_count:
                        print(f"Loaded {len(self.patterns)} patterns (matches expected pure Gray Code count). Appending White and Black.")
                        self.patterns.append(255 * np.ones((self.proj_height, self.proj_width), np.uint8))
                        self.patterns.append(np.zeros((self.proj_height, self.proj_width), np.uint8))
                    elif len(self.patterns) == expected_count + 2:
                        print(f"Loaded {len(self.patterns)} patterns (matches expected count + 2). Assuming White and Black are included.")
                    else:
                        print(f"Warning: Loaded pattern count ({len(self.patterns)}) does not match expected ({expected_count}) or expected+2 ({expected_count+2}).")
                        if len(self.patterns) > expected_count:
                             print("Assuming White and Black are already included or extra patterns exist. NOT appending.")
                        else:
                             print("Pattern count is low. Appending White and Black anyway.")
                             self.patterns.append(255 * np.ones((self.proj_height, self.proj_width), np.uint8))
                             self.patterns.append(np.zeros((self.proj_height, self.proj_width), np.uint8))
                except Exception as e:
                    print(f"Warning: Could not verify pattern count using OpenCV: {e}")
                    # Fallback behavior: if count is even, assume white/black might be missing? 
                    # Or just append if user says so? 
                    # Given the user's issue, let's look at the filenames maybe?
                    # But safest is: if we loaded 'enough', assume it's fine.
                    # Let's just append if < 40 (heuristic) otherwise don't? No, that's dangerous.
                    # Let's just append for now if validation fails, as legacy behavior.
                    self.patterns.append(255 * np.ones((self.proj_height, self.proj_width), np.uint8))
                    self.patterns.append(np.zeros((self.proj_height, self.proj_width), np.uint8))
                
                print(f"Total patterns to project: {len(self.patterns)}")
                return
            else:
                print(f"Warning: Pattern directory {self.pattern_dir} does not exist. Falling back to generation.")

        print("Generating Gray Code patterns...")
        gc_height = int((self.proj_height - 1) / self.graycode_step) + 1
        gc_width = int((self.proj_width - 1) / self.graycode_step) + 1
        
        graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
        ret, patterns = graycode.generate()
        
        if not ret:
            print("Failed to generate Gray Code patterns")
            sys.exit(1)
            
        # Expand image size to projector resolution
        self.patterns = []
        for pat in patterns:
            img = np.zeros((self.proj_height, self.proj_width), np.uint8)
            # Vectorized expansion for better performance than nested loops
            # Note: The original script used loops, but we can optimize.
            # However, to ensure exact compatibility with calibrate.py decoding logic,
            # we should stick to the logic or ensure the resize is nearest-neighbor.
            # Using cv2.resize with INTER_NEAREST is faster and equivalent.
            img = cv2.resize(pat, (self.proj_width, self.proj_height), interpolation=cv2.INTER_NEAREST)
            self.patterns.append(img)
            
        # Add White and Black patterns at the end (as expected by calibrate.py)
        self.patterns.append(255 * np.ones((self.proj_height, self.proj_width), np.uint8)) # White
        self.patterns.append(np.zeros((self.proj_height, self.proj_width), np.uint8))      # Black
        
        print(f"Generated {len(self.patterns)} patterns.")

    def setup_projector_window(self):
        """Setup full-screen window on the specified monitor."""
        target_monitor = None
        if get_monitors is not None:
            monitors = get_monitors()
            if len(monitors) <= self.monitor_index:
                print(f"Warning: Monitor index {self.monitor_index} not found. Available monitors: {len(monitors)}")
                print("Falling back to primary monitor (index 0).")
                target_monitor = monitors[0]
            else:
                target_monitor = monitors[self.monitor_index]
            print(
                f"Displaying on monitor: {target_monitor.name} ({target_monitor.width}x{target_monitor.height}) at ({target_monitor.x}, {target_monitor.y})"
            )

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        if target_monitor is not None:
            cv2.moveWindow(self.window_name, target_monitor.x, target_monitor.y)
        # Set to fullscreen
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        # Show a black image initially
        black_img = np.zeros((self.proj_height, self.proj_width), np.uint8)
        cv2.imshow(self.window_name, black_img)
        cv2.waitKey(100)

    def capture_sequence(self, capture_idx):
        """Run the projection and capture sequence for one pose."""
        capture_dir = os.path.join(self.output_dir, f"capture_{capture_idx}")
        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir)
            
        print(f"Starting capture sequence {capture_idx}...")

        image_zed = sl.Mat() if self.zed is not None else None
        
        for i, pattern in enumerate(self.patterns):
            # 1. Project pattern
            cv2.imshow(self.window_name, pattern)
            key = cv2.waitKey(500) # Wait 500ms for projector to stabilize and camera to adjust exposure if needed
            # Note: For gray codes, fixed exposure is recommended, but ZED auto-exposure usually adapts quickly.
            # Ideally, lock AE before starting.
            
            if key == 27: # ESC
                return False
                
            # 2. Capture image
            filename = os.path.join(capture_dir, f"graycode_{i:02d}.png")

            if self.zed is not None:
                if self.zed.grab() == sl.ERROR_CODE.SUCCESS:
                    self.zed.retrieve_image(image_zed, self.zed_view)
                    image_ocv = image_zed.get_data()
                    if image_ocv is None:
                        continue
                    if image_ocv.shape[-1] == 4:
                        image_ocv = cv2.cvtColor(image_ocv, cv2.COLOR_BGRA2BGR)
                    cv2.imwrite(filename, image_ocv)
                    print(f"  Saved {filename}", end="\r")
                else:
                    print("  Failed to grab ZED frame")
            else:
                ok, frame = self.opencv_cap.read()
                if ok and frame is not None:
                    cv2.imwrite(filename, frame)
                    print(f"  Saved {filename}", end="\r")
                else:
                    print("  Failed to grab OpenCV frame")
                
        print(f"\nCapture {capture_idx} completed.")
        
        # Show white after done to light up the room/board
        white_img = 255 * np.ones((self.proj_height, self.proj_width), np.uint8)
        cv2.imshow(self.window_name, white_img)
        cv2.waitKey(100)
        return True

    def run(self):
        self.initialize_camera()

        if self.pattern_dir is None:
            try:
                s = input("请输入 graycode_pattern 目录（回车则自动生成）: ").strip()
            except KeyboardInterrupt:
                print("\nExiting...")
                return
            if s:
                self.pattern_dir = s

        self.generate_patterns()
        self.setup_projector_window()
        
        print("\n=== Controls ===")
        print("  Press 'Enter' to capture a sequence (ensure chessboard is visible)")
        print("  Press 'q' or 'Esc' to quit")
        print("================\n")
        
        capture_count = 0
        
        # Check existing captures to increment counter
        while os.path.exists(os.path.join(self.output_dir, f"capture_{capture_count}")):
            capture_count += 1
            
        try:
            while True:
                # Live view for adjustment (optional, requires another window or just terminal prompt)
                # Since we are using the projector window for patterns, we can't easily show live view there.
                # But we can just wait for user input.
                
                print(f"Ready for capture_{capture_count}. Press Enter to start, q to quit.")
                
                # Simple input loop
                while True:
                    # Keep window responsive
                    cv2.imshow(self.window_name, 255 * np.ones((self.proj_height, self.proj_width), np.uint8)) # Show white for setup
                    key = cv2.waitKey(100)
                    if key == 13: # Enter
                        break
                    if key == ord('q') or key == 27:
                        raise KeyboardInterrupt
                
                success = self.capture_sequence(capture_count)
                if not success:
                    break
                    
                capture_count += 1
                
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            if self.zed is not None:
                self.zed.close()
            if self.opencv_cap is not None:
                self.opencv_cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProCam Calibration Data Acquisition")
    parser.add_argument("proj_height", type=int, help="Projector pixel height (e.g., 720)")
    parser.add_argument("proj_width", type=int, help="Projector pixel width (e.g., 1280)")
    parser.add_argument("--step", type=int, default=1, help="Graycode step size")
    parser.add_argument("--monitor", type=int, default=1, help="Monitor index for projector (default: 1)")
    parser.add_argument("--output", type=str, default=".", help="Output directory")
    parser.add_argument("--pattern_dir", type=str, default=None, help="Directory containing pre-generated pattern images (optional)")
    parser.add_argument(
        "--camera_mode",
        type=str,
        default="auto",
        choices=["auto", "zed", "opencv"],
        help="Camera mode: auto/zed/opencv",
    )
    
    args = parser.parse_args()
    
    capturer = ProcamCapturer(
        args.proj_width,
        args.proj_height,
        args.step,
        args.monitor,
        args.output,
        args.pattern_dir,
        camera_mode=args.camera_mode,
    )
    capturer.run()
