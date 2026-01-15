import glob
import json
import os
import re
from typing import Any, Dict

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None

try:
    import numpy as np  # type: ignore
except ImportError:
    np = None


class CalibrationService:
    def __init__(self):
        pass

    def _natural_sort_key(self, s):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split("([0-9]+)", s)
        ]

    def load_camera_param(self, json_file: str):
        if np is None:
            raise ImportError(
                "Missing dependency 'numpy'. Install with: python -m pip install numpy"
            )
        with open(json_file, "r") as f:
            param_data = json.load(f)
            P = param_data["camera"]["P"]
            d = param_data["camera"]["distortion"]
            return np.array(P).reshape([3, 3]), np.array(d)

    def run_calibration(
        self,
        input_dir: str,
        camera_param_file: str,
        proj_height: int,
        proj_width: int,
        chess_vert: int,
        chess_hori: int,
        chess_block_size: float,
        graycode_step: int = 1,
        black_thr: int = 40,
        white_thr: int = 5,
    ) -> Dict[str, Any]:

        proj_shape = (proj_height, proj_width)
        chess_shape = (chess_vert, chess_hori)

        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Input directory '{input_dir}' not found.")

        search_pattern = os.path.join(input_dir, "capture_*")
        dirnames = sorted(glob.glob(search_pattern), key=self._natural_sort_key)

        if len(dirnames) == 0:
            raise FileNotFoundError(f"No capture directories found in {input_dir}")

        gc_fname_lists = []
        used_dirnames = []
        for dname in dirnames:
            gc_fnames = sorted(glob.glob(os.path.join(dname, "graycode_*")))
            if len(gc_fnames) == 0:
                continue
            used_dirnames.append(dname)
            gc_fname_lists.append(gc_fnames)

        camP = None
        cam_dist = None
        if camera_param_file and os.path.exists(camera_param_file):
            camP, cam_dist = self.load_camera_param(camera_param_file)

        return self._calibrate_logic(
            used_dirnames,
            gc_fname_lists,
            proj_shape,
            chess_shape,
            chess_block_size,
            graycode_step,
            black_thr,
            white_thr,
            camP,
            cam_dist,
            input_dir,
        )

    def _calibrate_logic(
        self,
        dirnames,
        gc_fname_lists,
        proj_shape,
        chess_shape,
        chess_block_size,
        gc_step,
        black_thr,
        white_thr,
        camP,
        camD,
        output_base_dir,
    ):
        if cv2 is None:
            raise ImportError(
                "Missing dependency 'opencv-contrib-python' (cv2). Install with: python -m pip install opencv-contrib-python"
            )
        if np is None:
            raise ImportError(
                "Missing dependency 'numpy'. Install with: python -m pip install numpy"
            )
        objps = np.zeros((chess_shape[0] * chess_shape[1], 3), np.float32)
        objps[:, :2] = chess_block_size * np.mgrid[
            0 : chess_shape[0], 0 : chess_shape[1]
        ].T.reshape(-1, 2)

        gc_height = int((proj_shape[0] - 1) / gc_step) + 1
        gc_width = int((proj_shape[1] - 1) / gc_step) + 1
        graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
        graycode.setBlackThreshold(black_thr)
        graycode.setWhiteThreshold(white_thr)

        if not gc_fname_lists:
            raise RuntimeError("No graycode images found.")

        cam_shape = cv2.imread(gc_fname_lists[0][0], cv2.IMREAD_GRAYSCALE).shape
        patch_size_half = int(np.ceil(cam_shape[1] / 180))

        cam_corners_list = []
        cam_objps_list = []
        proj_objps_list = []
        proj_corners_list = []
        cam_corners_list2 = (
            []
        )  # For stereo calibration (subset where projector points were also found)

        for dname, gc_filenames in zip(dirnames, gc_fname_lists):
            if len(gc_filenames) != graycode.getNumberOfPatternImages() + 2:
                # print('Error : invalid number of images in \'' + dname + '\'')
                continue

            imgs = []
            for fname in gc_filenames:
                img_color = cv2.imread(fname)
                if img_color is None:
                    continue
                img = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
                if cam_shape != img.shape:
                    continue
                imgs.append(img)

            if len(imgs) < 2:
                continue

            black_img = imgs.pop()
            white_img = imgs.pop()

            res, cam_corners = cv2.findChessboardCorners(
                white_img,
                chess_shape,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
            )
            if not res:
                # print('Error : chessboard was not found in \'' + gc_filenames[-2] + '\'')
                continue

            cam_objps_list.append(objps)
            cam_corners_list.append(cam_corners)

            proj_objps = []
            proj_corners = []
            cam_corners2_subset = []

            # viz_proj_points = np.zeros(proj_shape, np.uint8)

            for corner, objp in zip(cam_corners, objps):
                c_x = int(round(corner[0][0]))
                c_y = int(round(corner[0][1]))
                src_points = []
                dst_points = []
                for dx in range(-patch_size_half, patch_size_half + 1):
                    for dy in range(-patch_size_half, patch_size_half + 1):
                        x = c_x + dx
                        y = c_y + dy
                        if x < 0 or x >= cam_shape[1] or y < 0 or y >= cam_shape[0]:
                            continue
                        if int(white_img[y, x]) - int(black_img[y, x]) <= black_thr:
                            continue
                        err, proj_pix = graycode.getProjPixel(imgs, x, y)
                        if not err:
                            src_points.append((x, y))
                            dst_points.append(gc_step * np.array(proj_pix))

                if len(src_points) < patch_size_half**2:
                    continue

                h_mat, inliers = cv2.findHomography(
                    np.array(src_points), np.array(dst_points), cv2.RANSAC, 3.0
                )

                if h_mat is None:
                    continue

                point = h_mat @ np.array([corner[0][0], corner[0][1], 1]).transpose()
                point_pix = point[0:2] / point[2]

                # Check bounds
                # if 0 <= point_pix[0] < proj_shape[1] and 0 <= point_pix[1] < proj_shape[0]:
                #     viz_proj_points[int(point_pix[1]), int(point_pix[0])] = 255

                proj_objps.append(objp)
                proj_corners.append([point_pix])
                cam_corners2_subset.append(corner)

            if len(proj_corners) < 3:
                continue

            proj_objps_list.append(np.array(proj_objps, np.float32))
            proj_corners_list.append(np.array(proj_corners, np.float32))
            cam_corners_list2.append(np.array(cam_corners2_subset, np.float32))

        if len(proj_corners_list) == 0:
            return {
                "success": False,
                "error": "No valid data points found across all captures.",
            }

        # Calibrate Camera (if needed)
        cam_int = camP
        cam_dist = camD
        if cam_int is None:
            ret, cam_int, cam_dist, cam_rvecs, cam_tvecs = cv2.calibrateCamera(
                cam_objps_list, cam_corners_list, cam_shape, None, None, None, None
            )

        # Calibrate Projector
        ret_proj, proj_int, proj_dist, proj_rvecs, proj_tvecs = cv2.calibrateCamera(
            proj_objps_list,
            proj_corners_list,
            (proj_shape[1], proj_shape[0]),
            None,
            None,
            None,
            None,
        )

        # Stereo Calibration
        flags = 0
        if camP is not None:
            flags |= cv2.CALIB_FIX_INTRINSIC

        (
            ret_stereo,
            cam_int,
            cam_dist,
            proj_int,
            proj_dist,
            cam_proj_rmat,
            cam_proj_tvec,
            E,
            F,
        ) = cv2.stereoCalibrate(
            proj_objps_list,
            cam_corners_list2,
            proj_corners_list,
            cam_int,
            cam_dist,
            proj_int,
            proj_dist,
            None,
            flags=flags,
        )

        # Save to XML (backward compatibility)
        output_xml = os.path.join(output_base_dir, "calibration_result.xml")
        fs = cv2.FileStorage(output_xml, cv2.FILE_STORAGE_WRITE)
        fs.write("img_shape", cam_shape)
        fs.write("rms", ret_stereo)
        fs.write("cam_int", cam_int)
        fs.write("cam_dist", cam_dist)
        fs.write("proj_int", proj_int)
        fs.write("proj_dist", proj_dist)
        fs.write("rotation", cam_proj_rmat)
        fs.write("translation", cam_proj_tvec)
        fs.release()

        return {
            "success": True,
            "rms": ret_stereo,
            "camera": {"intrinsic": cam_int.tolist(), "distortion": cam_dist.tolist()},
            "projector": {
                "intrinsic": proj_int.tolist(),
                "distortion": proj_dist.tolist(),
            },
            "extrinsics": {
                "rotation": cam_proj_rmat.tolist(),
                "translation": cam_proj_tvec.tolist(),
            },
            "poses_used": len(proj_corners_list),
            "output_file": output_xml,
        }
