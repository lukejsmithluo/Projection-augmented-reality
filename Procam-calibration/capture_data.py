# coding: UTF-8

import os
import sys
import time
import argparse
import cv2
import numpy as np
import pyzed.sl as sl
from screeninfo import get_monitors

class ProcamCapturer:
    """
    Automated ProCam calibration data acquisition system.
    Controls a projector to display Gray Code patterns and triggers a ZED camera to capture images.
    """

    def __init__(self, proj_width, proj_height, graycode_step=1, monitor_index=1, output_dir=".", pattern_dir=None):
        self.proj_width = proj_width
        self.proj_height = proj_height
        self.graycode_step = graycode_step
        self.monitor_index = monitor_index
        self.output_dir = output_dir
        self.pattern_dir = pattern_dir
        
        self.zed = sl.Camera()
        self.window_name = "Projector Pattern"
        self.patterns = []
        
        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def initialize_camera(self):
        """Initialize ZED 2i Camera with user preferences."""
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD2K  # User preference: 2K
        init_params.camera_fps = 15  # User preference: 15FPS
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS  # User preference: NEURAL PLUS
        init_params.coordinate_units = sl.UNIT.MILLIMETER
        
        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Error opening ZED camera: {err}")
            sys.exit(1)
            
        print(f"ZED Camera initialized: {self.zed.get_camera_information().camera_model}")

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
                
                print(f"Loaded {len(self.patterns)} patterns.")
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
        monitors = get_monitors()
        if len(monitors) <= self.monitor_index:
            print(f"Warning: Monitor index {self.monitor_index} not found. Available monitors: {len(monitors)}")
            print("Falling back to primary monitor (index 0).")
            target_monitor = monitors[0]
        else:
            target_monitor = monitors[self.monitor_index]
            
        print(f"Displaying on monitor: {target_monitor.name} ({target_monitor.width}x{target_monitor.height}) at ({target_monitor.x}, {target_monitor.y})")
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
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
        
        image_zed = sl.Mat()
        
        for i, pattern in enumerate(self.patterns):
            # 1. Project pattern
            cv2.imshow(self.window_name, pattern)
            key = cv2.waitKey(500) # Wait 500ms for projector to stabilize and camera to adjust exposure if needed
            # Note: For gray codes, fixed exposure is recommended, but ZED auto-exposure usually adapts quickly.
            # Ideally, lock AE before starting.
            
            if key == 27: # ESC
                return False
                
            # 2. Capture image
            if self.zed.grab() == sl.ERROR_CODE.SUCCESS:
                # Retrieve the left image (standard for single-camera calibration)
                self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                image_ocv = image_zed.get_data() # Returns BGRA
                
                # Convert BGRA to BGR or Grayscale? calibrate.py reads as Grayscale.
                # Saving as PNG preserves quality.
                filename = os.path.join(capture_dir, f"graycode_{i:02d}.png")
                cv2.imwrite(filename, image_ocv)
                print(f"  Saved {filename}", end='\r')
            else:
                print("  Failed to grab ZED frame")
                
        print(f"\nCapture {capture_idx} completed.")
        
        # Show white after done to light up the room/board
        white_img = 255 * np.ones((self.proj_height, self.proj_width), np.uint8)
        cv2.imshow(self.window_name, white_img)
        cv2.waitKey(100)
        return True

    def run(self):
        self.initialize_camera()
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
            self.zed.close()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProCam Calibration Data Acquisition")
    parser.add_argument("proj_height", type=int, help="Projector pixel height (e.g., 720)")
    parser.add_argument("proj_width", type=int, help="Projector pixel width (e.g., 1280)")
    parser.add_argument("--step", type=int, default=1, help="Graycode step size")
    parser.add_argument("--monitor", type=int, default=1, help="Monitor index for projector (default: 1)")
    parser.add_argument("--output", type=str, default=".", help="Output directory")
    parser.add_argument("--pattern_dir", type=str, default=None, help="Directory containing pre-generated pattern images (optional)")
    
    args = parser.parse_args()
    
    capturer = ProcamCapturer(args.proj_width, args.proj_height, args.step, args.monitor, args.output, args.pattern_dir)
    capturer.run()
