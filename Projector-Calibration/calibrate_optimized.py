# coding: UTF-8

import os
import os.path
import glob
import argparse
import cv2
import numpy as np
import json
import logging
from typing import Tuple, List, Optional, Union
import warnings

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedChessboardDetector:
    """优化的棋盘格检测器，包含多种预处理和容错机制"""
    
    def __init__(self, chess_shape: Tuple[int, int]):
        self.chess_shape = chess_shape
        
    def detect_corners(self, image: np.ndarray, debug: bool = False) -> Tuple[bool, Optional[np.ndarray]]:
        """
        使用多种策略检测棋盘格角点
        
        Args:
            image: 输入图像
            debug: 是否输出调试信息
            
        Returns:
            (success, corners): 检测结果和角点坐标
        """
        if debug:
            logger.info(f"开始检测棋盘格角点，目标尺寸: {self.chess_shape}")
        
        # 策略1: 直接检测
        ret, corners = cv2.findChessboardCorners(image, self.chess_shape, 
                                                cv2.CALIB_CB_ADAPTIVE_THRESH + 
                                                cv2.CALIB_CB_NORMALIZE_IMAGE + 
                                                cv2.CALIB_CB_FAST_CHECK)
        if ret:
            corners = cv2.cornerSubPix(image, corners, (11, 11), (-1, -1),
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1))
            if debug:
                logger.info("策略1成功：直接检测")
            return True, corners
        
        # 策略2: 直方图均衡化
        equalized = cv2.equalizeHist(image)
        ret, corners = cv2.findChessboardCorners(equalized, self.chess_shape,
                                                cv2.CALIB_CB_ADAPTIVE_THRESH + 
                                                cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ret:
            corners = cv2.cornerSubPix(equalized, corners, (11, 11), (-1, -1),
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1))
            if debug:
                logger.info("策略2成功：直方图均衡化")
            return True, corners
        
        # 策略3: CLAHE (对比度限制自适应直方图均衡化)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(image)
        ret, corners = cv2.findChessboardCorners(clahe_img, self.chess_shape,
                                                cv2.CALIB_CB_ADAPTIVE_THRESH + 
                                                cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ret:
            corners = cv2.cornerSubPix(clahe_img, corners, (11, 11), (-1, -1),
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1))
            if debug:
                logger.info("策略3成功：CLAHE处理")
            return True, corners
        
        # 策略4: 高斯模糊 + 锐化
        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(blurred, -1, kernel)
        ret, corners = cv2.findChessboardCorners(sharpened, self.chess_shape,
                                                cv2.CALIB_CB_ADAPTIVE_THRESH + 
                                                cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ret:
            corners = cv2.cornerSubPix(sharpened, corners, (11, 11), (-1, -1),
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1))
            if debug:
                logger.info("策略4成功：高斯模糊+锐化")
            return True, corners
        
        # 策略5: 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        ret, corners = cv2.findChessboardCorners(opened, self.chess_shape,
                                                cv2.CALIB_CB_ADAPTIVE_THRESH + 
                                                cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ret:
            corners = cv2.cornerSubPix(opened, corners, (11, 11), (-1, -1),
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1))
            if debug:
                logger.info("策略5成功：形态学操作")
            return True, corners
        
        if debug:
            logger.warning("所有策略都失败了")
        return False, None

class OptimizedGrayCodeDecoder:
    """优化的格雷码解码器，提高鲁棒性"""
    
    def __init__(self, graycode_pattern, black_thr: int = 40, white_thr: int = 5):
        self.graycode = graycode_pattern
        self.black_thr = black_thr
        self.white_thr = white_thr
        
    def decode_with_validation(self, imgs: List[np.ndarray], x: int, y: int, 
                             white_img: np.ndarray, black_img: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """
        带验证的格雷码解码
        
        Args:
            imgs: 格雷码图像序列
            x, y: 像素坐标
            white_img: 白色参考图像
            black_img: 黑色参考图像
            
        Returns:
            (success, proj_pixel): 解码结果和投影仪像素坐标
        """
        # 检查像素是否在投影区域内
        if int(white_img[y, x]) - int(black_img[y, x]) <= self.black_thr:
            return False, None
        
        # 基本解码
        err, proj_pix = self.graycode.getProjPixel(imgs, x, y)
        if err:
            return False, None
        
        # 验证解码结果的一致性
        if not self._validate_decoded_pixel(imgs, x, y, proj_pix, white_img, black_img):
            return False, None
        
        return True, proj_pix
    
    def _validate_decoded_pixel(self, imgs: List[np.ndarray], x: int, y: int, 
                               proj_pix: Tuple[int, int], white_img: np.ndarray, 
                               black_img: np.ndarray) -> bool:
        """验证解码像素的一致性"""
        # 检查邻域像素的一致性
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < white_img.shape[1] and 0 <= ny < white_img.shape[0]):
                    if int(white_img[ny, nx]) - int(black_img[ny, nx]) > self.black_thr:
                        err, neighbor_pix = self.graycode.getProjPixel(imgs, nx, ny)
                        if not err:
                            # 检查邻域像素解码结果的合理性
                            if abs(neighbor_pix[0] - proj_pix[0]) > 2 or abs(neighbor_pix[1] - proj_pix[1]) > 2:
                                return False
        return True

class OptimizedCalibrator:
    """优化的标定器，使用现代标定技术"""
    
    def __init__(self):
        self.detector = None
        self.decoder = None
        
    def calibrate_camera_modern(self, objps_list: List[np.ndarray], 
                               corners_list: List[np.ndarray], 
                               image_shape: Tuple[int, int],
                               camera_matrix: Optional[np.ndarray] = None,
                               dist_coeffs: Optional[np.ndarray] = None) -> Tuple[float, np.ndarray, np.ndarray, List[np.ndarray], List[np.ndarray]]:
        """
        使用现代技术进行相机标定
        
        Args:
            objps_list: 物体点列表
            corners_list: 角点列表
            image_shape: 图像尺寸
            camera_matrix: 预设相机内参
            dist_coeffs: 预设畸变系数
            
        Returns:
            (rms, camera_matrix, dist_coeffs, rvecs, tvecs): 标定结果
        """
        # 设置标定标志，使用更现代的方法
        flags = (cv2.CALIB_RATIONAL_MODEL +  # 使用有理畸变模型
                cv2.CALIB_THIN_PRISM_MODEL +  # 使用薄棱镜模型
                cv2.CALIB_TILTED_MODEL)       # 使用倾斜模型
        
        # 如果提供了初始参数，使用它们
        if camera_matrix is not None and dist_coeffs is not None:
            flags |= cv2.CALIB_USE_INTRINSIC_GUESS
        
        # 设置终止条件
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
        
        try:
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                objps_list, corners_list, image_shape, camera_matrix, dist_coeffs, 
                flags=flags, criteria=criteria)
            
            logger.info(f"相机标定完成，RMS误差: {ret:.6f}")
            return ret, camera_matrix, dist_coeffs, rvecs, tvecs
            
        except cv2.error as e:
            logger.warning(f"现代标定方法失败，回退到基础方法: {e}")
            # 回退到基础方法
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                objps_list, corners_list, image_shape, None, None)
            return ret, camera_matrix, dist_coeffs, rvecs, tvecs
    
    def stereo_calibrate_modern(self, objps_list: List[np.ndarray],
                               cam_corners_list: List[np.ndarray],
                               proj_corners_list: List[np.ndarray],
                               cam_matrix: np.ndarray, cam_dist: np.ndarray,
                               proj_matrix: np.ndarray, proj_dist: np.ndarray,
                               image_shape: Tuple[int, int]) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        使用现代技术进行立体标定
        """
        # 设置立体标定标志
        flags = (cv2.CALIB_FIX_INTRINSIC +     # 固定内参
                cv2.CALIB_RATIONAL_MODEL +      # 使用有理畸变模型
                cv2.CALIB_SAME_FOCAL_LENGTH)    # 假设相同焦距（可选）
        
        # 设置终止条件
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
        
        try:
            ret, cam_matrix, cam_dist, proj_matrix, proj_dist, R, T, E, F = cv2.stereoCalibrate(
                objps_list, cam_corners_list, proj_corners_list,
                cam_matrix, cam_dist, proj_matrix, proj_dist, image_shape,
                flags=flags, criteria=criteria)
            
            logger.info(f"立体标定完成，RMS误差: {ret:.6f}")
            return ret, cam_matrix, cam_dist, proj_matrix, proj_dist, R, T, E, F
            
        except cv2.error as e:
            logger.warning(f"现代立体标定失败，回退到基础方法: {e}")
            # 回退到基础方法
            ret, cam_matrix, cam_dist, proj_matrix, proj_dist, R, T, E, F = cv2.stereoCalibrate(
                objps_list, cam_corners_list, proj_corners_list,
                cam_matrix, cam_dist, proj_matrix, proj_dist, image_shape)
            return ret, cam_matrix, cam_dist, proj_matrix, proj_dist, R, T, E, F

def main():
    parser = argparse.ArgumentParser(
        description='Optimized Calibrate pro-cam system using chessboard and structured light projection\n'
        '  Place captured images as \n'
        '    ./ --- capture_1/ --- graycode_00.png\n'
        '        |              |- graycode_01.png\n'
        '        |              |        .\n'
        '        |              |        .\n'
        '        |              |- graycode_??.png\n'
        '        |- capture_2/ --- graycode_00.png\n'
        '        |              |- graycode_01.png\n'
        '        |      .       |        .\n'
        '        |      .       |        .\n',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('proj_height', type=int, help='projector pixel height')
    parser.add_argument('proj_width', type=int, help='projector pixel width')
    parser.add_argument('chess_vert', type=int,
                        help='number of cross points of chessboard in vertical direction')
    parser.add_argument('chess_hori', type=int,
                        help='number of cross points of chessboard in horizontal direction')
    parser.add_argument('chess_block_size', type=float,
                        help='size of blocks of chessboard (mm or cm or m)')
    parser.add_argument('graycode_step', type=int,
                        default=1, help='step size of graycode')
    parser.add_argument('-black_thr', type=int, default=40,
                        help='threshold to determine whether a camera pixel captures projected area or not (default : 40)')
    parser.add_argument('-white_thr', type=int, default=5,
                        help='threshold to specify robustness of graycode decoding (default : 5)')
    parser.add_argument('-camera', type=str, default=str(), help='camera internal parameter json file')
    parser.add_argument('-debug', action='store_true', help='enable debug mode')
    parser.add_argument('-output', type=str, default='calibration_result_optimized.xml', 
                        help='output calibration file name')

    args = parser.parse_args()

    proj_shape = (args.proj_height, args.proj_width)
    chess_shape = (args.chess_vert, args.chess_hori)
    chess_block_size = args.chess_block_size
    gc_step = args.graycode_step
    black_thr = args.black_thr
    white_thr = args.white_thr
    debug_mode = args.debug
    output_file = args.output

    camera_param_file = args.camera

    dirnames = sorted(glob.glob('./capture_*'))
    if len(dirnames) == 0:
        logger.error('Directories \'./capture_*\' were not found')
        return

    logger.info('Searching input files ...')
    used_dirnames = []
    gc_fname_lists = []
    for dname in dirnames:
        gc_fnames = sorted(glob.glob(dname + '/graycode_*'))
        if len(gc_fnames) == 0:
            continue
        used_dirnames.append(dname)
        gc_fname_lists.append(gc_fnames)
        logger.info(f' \'{dname}\' was found')

    camP = None
    cam_dist = None
    if camera_param_file:
        path, ext = os.path.splitext(camera_param_file)
        if ext == ".json":
            camP, cam_dist = loadCameraParam(camera_param_file)
            logger.info('Loaded camera parameters')
            if debug_mode:
                logger.info(f'Camera matrix:\n{camP}')
                logger.info(f'Distortion coefficients:\n{cam_dist}')

    calibrate_optimized(used_dirnames, gc_fname_lists,
                       proj_shape, chess_shape, chess_block_size, gc_step, 
                       black_thr, white_thr, camP, cam_dist, debug_mode, output_file)

def printNumpyWithIndent(tar, indentchar):
    print(indentchar + str(tar).replace('\n', '\n' + indentchar))

def loadCameraParam(json_file):
    try:
        with open(json_file, 'r') as f:
            param_data = json.load(f)
            P = param_data['camera']['P']
            d = param_data['camera']['distortion']
            return np.array(P).reshape([3, 3]), np.array(d)
    except Exception as e:
        logger.error(f"Failed to load camera parameters: {e}")
        return None, None

def calibrate_optimized(dirnames, gc_fname_lists, proj_shape, chess_shape, chess_block_size, 
                       gc_step, black_thr, white_thr, camP, camD, debug_mode=False, 
                       output_file='calibration_result_optimized.xml'):
    """优化的标定函数"""
    
    # 创建物体点
    objps = np.zeros((chess_shape[0] * chess_shape[1], 3), np.float32)
    objps[:, :2] = chess_block_size * \
        np.mgrid[0:chess_shape[0], 0:chess_shape[1]].T.reshape(-1, 2)

    logger.info('开始优化标定流程...')
    
    # 创建格雷码模式
    gc_height = int((proj_shape[0] - 1) / gc_step) + 1
    gc_width = int((proj_shape[1] - 1) / gc_step) + 1
    graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
    graycode.setBlackThreshold(black_thr)
    graycode.setWhiteThreshold(white_thr)

    # 获取图像尺寸
    cam_shape = cv2.imread(gc_fname_lists[0][0], cv2.IMREAD_GRAYSCALE).shape
    patch_size_half = max(3, int(np.ceil(cam_shape[1] / 180)))  # 最小patch大小为3
    logger.info(f'  patch size : {patch_size_half * 2 + 1}')

    # 创建优化的检测器和解码器
    detector = OptimizedChessboardDetector(chess_shape)
    decoder = OptimizedGrayCodeDecoder(graycode, black_thr, white_thr)
    calibrator = OptimizedCalibrator()

    cam_corners_list = []
    cam_objps_list = []
    cam_corners_list2 = []
    proj_objps_list = []
    proj_corners_list = []
    
    successful_captures = 0
    
    for dname, gc_filenames in zip(dirnames, gc_fname_lists):
        logger.info(f'  processing \'{dname}\'')
        
        expected_images = graycode.getNumberOfPatternImages() + 2
        actual_images = len(gc_filenames)
        
        if actual_images < expected_images:
            logger.error(f'Insufficient number of images in \'{dname}\' (expected at least {expected_images}, got {actual_images})')
            continue
        elif actual_images > expected_images:
            logger.warning(f'More images than expected in \'{dname}\' (expected {expected_images}, got {actual_images}). Using first {expected_images} images.')
            gc_filenames = gc_filenames[:expected_images]

        # 加载图像
        imgs = []
        try:
            for fname in gc_filenames:
                img = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError(f"Cannot read image: {fname}")
                if cam_shape != img.shape:
                    raise ValueError(f"Image size mismatch in '{fname}'")
                imgs.append(img)
        except Exception as e:
            logger.error(f"Error loading images from '{dname}': {e}")
            continue
            
        black_img = imgs.pop()
        white_img = imgs.pop()

        # 使用优化的棋盘格检测
        res, cam_corners = detector.detect_corners(white_img, debug=debug_mode)
        if not res:
            logger.warning(f'Chessboard was not found in \'{gc_filenames[-2]}\', skipping this capture')
            continue
            
        cam_objps_list.append(objps)
        cam_corners_list.append(cam_corners)

        # 处理投影仪角点
        proj_objps = []
        proj_corners = []
        cam_corners2 = []
        successful_corners = 0
        
        for corner, objp in zip(cam_corners, objps):
            c_x = int(round(corner[0][0]))
            c_y = int(round(corner[0][1]))
            src_points = []
            dst_points = []
            
            # 在patch内搜索有效像素
            for dx in range(-patch_size_half, patch_size_half + 1):
                for dy in range(-patch_size_half, patch_size_half + 1):
                    x = c_x + dx
                    y = c_y + dy
                    
                    # 边界检查
                    if x < 0 or x >= cam_shape[1] or y < 0 or y >= cam_shape[0]:
                        continue
                    
                    # 使用优化的解码器
                    success, proj_pix = decoder.decode_with_validation(imgs, x, y, white_img, black_img)
                    if success:
                        src_points.append((x, y))
                        dst_points.append(gc_step * np.array(proj_pix))
            
            # 检查是否有足够的点进行单应性计算
            min_points = max(4, patch_size_half)  # 至少需要4个点
            if len(src_points) < min_points:
                if debug_mode:
                    logger.warning(f'    Corner ({c_x}, {c_y}) skipped: insufficient decoded pixels ({len(src_points)} < {min_points})')
                continue
            
            try:
                # 使用RANSAC计算单应性矩阵，提高鲁棒性
                h_mat, inliers = cv2.findHomography(
                    np.array(src_points), np.array(dst_points),
                    cv2.RANSAC, 1.0)  # RANSAC阈值
                
                if h_mat is None:
                    if debug_mode:
                        logger.warning(f'    Corner ({c_x}, {c_y}) skipped: homography calculation failed')
                    continue
                
                # 计算投影仪坐标
                point = h_mat @ np.array([corner[0][0], corner[0][1], 1]).transpose()
                if abs(point[2]) < 1e-8:  # 避免除零
                    if debug_mode:
                        logger.warning(f'    Corner ({c_x}, {c_y}) skipped: invalid homogeneous coordinate')
                    continue
                    
                point_pix = point[0:2] / point[2]
                
                # 验证投影仪坐标的合理性
                if (0 <= point_pix[0] < proj_shape[1] and 0 <= point_pix[1] < proj_shape[0]):
                    proj_objps.append(objp)
                    proj_corners.append([point_pix])
                    cam_corners2.append(corner)
                    successful_corners += 1
                elif debug_mode:
                    logger.warning(f'    Corner ({c_x}, {c_y}) skipped: projected point out of bounds ({point_pix[0]:.1f}, {point_pix[1]:.1f})')
                    
            except Exception as e:
                if debug_mode:
                    logger.warning(f'    Corner ({c_x}, {c_y}) skipped: {e}')
                continue
        
        # 检查是否有足够的角点
        if len(proj_corners) < 6:  # 增加最小角点要求
            logger.warning(f'Too few corners found in \'{dname}\' ({len(proj_corners)} < 6), skipping')
            continue
            
        proj_objps_list.append(np.float32(proj_objps))
        proj_corners_list.append(np.float32(proj_corners))
        cam_corners_list2.append(np.float32(cam_corners2))
        successful_captures += 1
        
        logger.info(f'    Successfully processed {successful_corners}/{len(cam_corners)} corners')

    if successful_captures == 0:
        logger.error('No valid captures found for calibration')
        return None
        
    logger.info(f'Successfully processed {successful_captures} captures')

    # 相机标定
    logger.info('Calibrating camera with modern methods...')
    cam_rvecs = []
    cam_tvecs = []
    
    if camP is None:
        ret, cam_int, cam_dist, cam_rvecs, cam_tvecs = calibrator.calibrate_camera_modern(
            cam_objps_list, cam_corners_list, cam_shape)
        logger.info(f'  Camera calibration RMS : {ret:.6f}')
    else:
        # 使用预设参数进行PnP求解
        for objp, corners in zip(cam_objps_list, cam_corners_list):
            ret, cam_rvec, cam_tvec = cv2.solvePnP(objp, corners, camP, camD)
            cam_rvecs.append(cam_rvec)
            cam_tvecs.append(cam_tvec)
        cam_int = camP
        cam_dist = camD
        logger.info('  Using provided camera parameters')
    
    logger.info('  Camera intrinsic parameters :')
    printNumpyWithIndent(cam_int, '    ')
    logger.info('  Camera distortion parameters :')
    printNumpyWithIndent(cam_dist, '    ')

    # 投影仪标定
    logger.info('Calibrating projector with modern methods...')
    ret, proj_int, proj_dist, proj_rvecs, proj_tvecs = calibrator.calibrate_camera_modern(
        proj_objps_list, proj_corners_list, proj_shape)
    logger.info(f'  Projector calibration RMS : {ret:.6f}')
    logger.info('  Projector intrinsic parameters :')
    printNumpyWithIndent(proj_int, '    ')
    logger.info('  Projector distortion parameters :')
    printNumpyWithIndent(proj_dist, '    ')

    # 立体标定
    logger.info('Performing stereo calibration with modern methods...')
    ret, cam_int, cam_dist, proj_int, proj_dist, cam_proj_rmat, cam_proj_tvec, E, F = calibrator.stereo_calibrate_modern(
        proj_objps_list, cam_corners_list2, proj_corners_list, 
        cam_int, cam_dist, proj_int, proj_dist, cam_shape)
    
    logger.info('=== Final Results ===')
    logger.info(f'  Final RMS error : {ret:.6f}')
    logger.info('  Camera intrinsic parameters :')
    printNumpyWithIndent(cam_int, '    ')
    logger.info('  Camera distortion parameters :')
    printNumpyWithIndent(cam_dist, '    ')
    logger.info('  Projector intrinsic parameters :')
    printNumpyWithIndent(proj_int, '    ')
    logger.info('  Projector distortion parameters :')
    printNumpyWithIndent(proj_dist, '    ')
    logger.info('  Rotation matrix / translation vector from camera to projector')
    logger.info('  (they translate points from camera coord to projector coord) :')
    printNumpyWithIndent(cam_proj_rmat, '    ')
    printNumpyWithIndent(cam_proj_tvec, '    ')

    # 保存结果
    try:
        fs = cv2.FileStorage(output_file, cv2.FILE_STORAGE_WRITE)
        fs.write('img_shape', cam_shape)
        fs.write('rms', ret)
        fs.write('cam_int', cam_int)
        fs.write('cam_dist', cam_dist)
        fs.write('proj_int', proj_int)
        fs.write('proj_dist', proj_dist)
        fs.write('rotation', cam_proj_rmat)
        fs.write('translation', cam_proj_tvec)
        fs.write('successful_captures', successful_captures)
        fs.release()
        logger.info(f'Calibration results saved to {output_file}')
    except Exception as e:
        logger.error(f'Failed to save calibration results: {e}')

    return ret

if __name__ == '__main__':
    main()