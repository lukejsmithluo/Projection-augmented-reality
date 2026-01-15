import os
from typing import List

import cv2
import numpy as np
from screeninfo import get_monitors

try:
    import pyzed.sl as sl
except ImportError:
    sl = None


class CaptureService:
    def __init__(self, output_dir: str = "capture_data"):
        self.output_dir = output_dir
        self.zed = sl.Camera() if sl else None
        self.patterns: List[np.ndarray] = []
        self.window_name = "Projector Pattern"
        self.monitor_index = 0
        self.proj_width = 0
        self.proj_height = 0
        self.graycode_step = 1
        self._is_initialized = False

    def initialize(
        self,
        proj_width: int,
        proj_height: int,
        graycode_step: int = 1,
        monitor_index: int = 1,
    ):
        if not sl:
            raise ImportError("ZED SDK not installed.")

        self.proj_width = proj_width
        self.proj_height = proj_height
        self.graycode_step = graycode_step
        self.monitor_index = monitor_index

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Initialize Camera
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD2K
        init_params.camera_fps = 15
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init_params.coordinate_units = sl.UNIT.MILLIMETER

        if not self.zed.is_opened():
            err = self.zed.open(init_params)
            if err != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(f"Error opening ZED camera: {err}")

        # Generate Patterns
        self._generate_patterns()

        # Setup Window
        self._setup_window()
        self._is_initialized = True

    def _generate_patterns(self):
        gc_height = int((self.proj_height - 1) / self.graycode_step) + 1
        gc_width = int((self.proj_width - 1) / self.graycode_step) + 1

        graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
        ret, patterns = graycode.generate()

        if not ret:
            raise RuntimeError("Failed to generate Gray Code patterns")

        self.patterns = []
        for pat in patterns:
            # Resize using nearest neighbor to preserve sharp edges
            img = cv2.resize(
                pat,
                (self.proj_width, self.proj_height),
                interpolation=cv2.INTER_NEAREST,
            )
            self.patterns.append(img)

        # Add White and Black patterns at the end
        self.patterns.append(
            255 * np.ones((self.proj_height, self.proj_width), np.uint8)
        )  # White
        self.patterns.append(
            np.zeros((self.proj_height, self.proj_width), np.uint8)
        )  # Black

    def _setup_window(self):
        monitors = get_monitors()
        if len(monitors) <= self.monitor_index:
            target_monitor = monitors[0]
            print(
                f"Warning: Monitor index {self.monitor_index} not found. Using primary monitor."
            )
        else:
            target_monitor = monitors[self.monitor_index]

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(self.window_name, target_monitor.x, target_monitor.y)

        # Some systems require waitKey after window creation
        cv2.imshow(
            self.window_name, np.zeros((self.proj_height, self.proj_width), np.uint8)
        )
        cv2.waitKey(100)
        cv2.setWindowProperty(
            self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        cv2.waitKey(100)

        # Show white initially
        white_img = 255 * np.ones((self.proj_height, self.proj_width), np.uint8)
        cv2.imshow(self.window_name, white_img)
        cv2.waitKey(100)

    def capture_pose(self, capture_idx: int) -> bool:
        """Captures one sequence (all patterns) for a given index."""
        if not self._is_initialized:
            raise RuntimeError(
                "CaptureService not initialized. Call initialize() first."
            )

        capture_dir = os.path.join(self.output_dir, f"capture_{capture_idx}")
        os.makedirs(capture_dir, exist_ok=True)

        image_zed = sl.Mat()

        try:
            for i, pattern in enumerate(self.patterns):
                cv2.imshow(self.window_name, pattern)
                cv2.waitKey(500)  # Wait 500ms for projector to stabilize

                # Capture image
                if self.zed.grab() == sl.ERROR_CODE.SUCCESS:
                    self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                    image_ocv = image_zed.get_data()  # Returns BGRA

                    filename = os.path.join(capture_dir, f"graycode_{i:02d}.png")
                    cv2.imwrite(filename, image_ocv)
                else:
                    print("Failed to grab ZED frame")
                    return False

            # Show white after done
            white_img = 255 * np.ones((self.proj_height, self.proj_width), np.uint8)
            cv2.imshow(self.window_name, white_img)
            cv2.waitKey(100)
            return True
        except Exception as e:
            print(f"Error during capture: {e}")
            return False

    def close(self):
        if self.zed and self.zed.is_opened():
            self.zed.close()
        try:
            cv2.destroyWindow(self.window_name)
        except Exception:
            pass
        self._is_initialized = False
