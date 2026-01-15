from typing import Any, Dict

try:
    import pyzed.sl as sl
except ImportError:
    sl = None


class CameraService:
    def __init__(self):
        self.zed = sl.Camera() if sl else None

    def get_camera_params(self) -> Dict[str, Any]:
        if not sl:
            raise ImportError("ZED SDK not installed or pyzed module missing.")

        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD2K
        init_params.camera_fps = 15
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init_params.coordinate_units = sl.UNIT.MILLIMETER

        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"Error opening ZED camera: {err}")

        try:
            cam_info = self.zed.get_camera_information()
            calib_params = cam_info.camera_configuration.calibration_parameters.left_cam

            fx = calib_params.fx
            fy = calib_params.fy
            cx = calib_params.cx
            cy = calib_params.cy

            # Construct Projection Matrix (K)
            P = [fx, 0, cx, 0, fy, cy, 0, 0, 1]
            dist = calib_params.disto
            # Take first 5 for standard OpenCV model
            D = list(dist[:5])

            return {
                "camera": {
                    "P": P,
                    "distortion": D,
                    "resolution": {
                        "width": cam_info.camera_configuration.resolution.width,
                        "height": cam_info.camera_configuration.resolution.height,
                    },
                    "model": str(cam_info.camera_model),
                }
            }
        finally:
            if self.zed.is_opened():
                self.zed.close()
