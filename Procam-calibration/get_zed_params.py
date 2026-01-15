# coding: UTF-8
import pyzed.sl as sl
import numpy as np
import json
import sys

def main():
    # Initialize ZED camera with the same settings used for capture
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD1080
    init_params.camera_fps = 15
    init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
    init_params.coordinate_units = sl.UNIT.MILLIMETER

    print("Opening ZED camera...")
    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Error opening ZED camera: {err}")
        sys.exit(1)

    # Get camera information
    cam_info = zed.get_camera_information()
    # We use the LEFT camera for calibration (standard)
    calib_params = cam_info.camera_configuration.calibration_parameters.left_cam

    # Extract Intrinsic Matrix (fx, fy, cx, cy)
    fx = calib_params.fx
    fy = calib_params.fy
    cx = calib_params.cx
    cy = calib_params.cy

    # Construct Projection Matrix (K) - 3x3 flattened to list
    # [fx,  0, cx]
    # [ 0, fy, cy]
    # [ 0,  0,  1]
    P = [
        fx, 0, cx,
        0, fy, cy,
        0, 0, 1
    ]

    # Extract Distortion Coefficients
    # ZED uses [k1, k2, p1, p2, k3] which matches OpenCV's standard 5-param model
    # Note: ZED SDK disto is [k1, k2, p1, p2, k3, k4, k5, k6], but standard OpenCV uses first 5 usually.
    # Let's verify what calibrate.py expects. It expects a list.
    dist = calib_params.disto
    # Usually we take the first 5 for standard OpenCV calibration models
    D = dist[:5]

    print("\n=== ZED Camera Parameters ===")
    print(f"Resolution: {cam_info.camera_configuration.resolution.width}x{cam_info.camera_configuration.resolution.height}")
    print(f"fx: {fx:.4f}, fy: {fy:.4f}")
    print(f"cx: {cx:.4f}, cy: {cy:.4f}")
    print(f"Distortion: {D}")

    # Create dictionary structure
    data = {
        "camera": {
            "P": P,
            "distortion": list(D)
        }
    }

    # Save to JSON
    output_file = "camera_config.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"\nSuccessfully saved parameters to {output_file}")
    
    zed.close()

if __name__ == "__main__":
    main()
