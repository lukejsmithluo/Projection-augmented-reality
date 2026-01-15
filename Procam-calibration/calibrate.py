# coding: UTF-8

import os
import os.path
import glob
import argparse
import cv2
import numpy as np
import json


import re

def main():
    parser = argparse.ArgumentParser(
        description='Calibrate pro-cam system using chessboard and structured light projection\n'
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
                        help='threashold to determine whether a camera pixel captures projected area or not (default : 40)')
    parser.add_argument('-white_thr', type=int, default=5,
                        help='threashold to specify robustness of graycode decoding (default : 5)')
    parser.add_argument('-camera', type=str, default=str(),help='camera internal parameter json file')
    parser.add_argument('-input_dir', type=str, default='./', help='directory containing capture_* folders (default: ./)')
    parser.add_argument('-output_xml', type=str, default='calibration_result.xml', help='output calibration result xml file (default: calibration_result.xml)')
    parser.add_argument('-viz_tag', type=str, default=str(), help='tag prefix for visualization images (default: empty)')
    parser.add_argument('-enable_subpix', type=int, default=1, help='enable corner subpixel refinement (default: 1)')
    parser.add_argument('-enable_view_filter', type=int, default=1, help='enable outlier view filtering (default: 1)')

    args = parser.parse_args()

    proj_shape = (args.proj_height, args.proj_width)
    chess_shape = (args.chess_vert, args.chess_hori)
    chess_block_size = args.chess_block_size
    gc_step = args.graycode_step
    black_thr = args.black_thr
    white_thr = args.white_thr
    input_dir = args.input_dir

    camera_param_file = args.camera

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        return

    # Use os.path.join for correct path construction
    search_pattern = os.path.join(input_dir, 'capture_*')
    
    # Natural sort to ensure capture_2 comes before capture_10
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]
                
    dirnames = sorted(glob.glob(search_pattern), key=natural_sort_key)
    if len(dirnames) == 0:
        print(f"Directories '{search_pattern}' were not found")
        return

    used_dirnames = []
    gc_fname_lists = []
    for dname in dirnames:
        gc_fnames = sorted(glob.glob(os.path.join(dname, 'graycode_*')))
        if len(gc_fnames) == 0:
            continue
        used_dirnames.append(dname)
        gc_fname_lists.append(gc_fnames)
    print('Found ' + str(len(used_dirnames)) + ' capture views')

    camP = None
    cam_dist = None
    path, ext = os.path.splitext(camera_param_file)
    if(ext == ".json"):
        camP,cam_dist = loadCameraParam(camera_param_file)
        print('load camera parameters')
        print(camP)
        print(cam_dist)

    calibrate(used_dirnames, gc_fname_lists,
              proj_shape, chess_shape, chess_block_size, gc_step, black_thr, white_thr,
               camP, cam_dist, args.output_xml, args.viz_tag, bool(args.enable_subpix), bool(args.enable_view_filter))


def printNumpyWithIndent(tar, indentchar):
    print(indentchar + str(tar).replace('\n', '\n' + indentchar))

def loadCameraParam(json_file):
    with open(json_file, 'r') as f:
        param_data = json.load(f)
        P = param_data['camera']['P']
        d = param_data['camera']['distortion']
        return np.array(P).reshape([3,3]), np.array(d)

def calibrate(dirnames, gc_fname_lists, proj_shape, chess_shape, chess_block_size, gc_step, black_thr, white_thr, camP, camD, output_xml, viz_tag, enable_subpix, enable_view_filter):
    objps = np.zeros((chess_shape[0]*chess_shape[1], 3), np.float32)
    objps[:, :2] = chess_block_size * \
        np.mgrid[0:chess_shape[0], 0:chess_shape[1]].T.reshape(-1, 2)

    print('Calibrating ...')
    gc_height = int((proj_shape[0]-1)/gc_step)+1
    gc_width = int((proj_shape[1]-1)/gc_step)+1
    graycode = cv2.structured_light_GrayCodePattern.create(
        gc_width, gc_height)
    graycode.setBlackThreshold(black_thr)
    graycode.setWhiteThreshold(white_thr)

    first_img = cv2.imread(gc_fname_lists[0][0], cv2.IMREAD_GRAYSCALE)
    if first_img is None:
        print('Error : failed to load \'' + gc_fname_lists[0][0] + '\'')
        return None

    cam_shape = first_img.shape
    cam_size = (cam_shape[1], cam_shape[0])
    proj_size = (proj_shape[1], proj_shape[0])
    view_names = []

    cam_corners_list = []
    cam_objps_list = []
    cam_corners_list2 = []
    proj_objps_list = []
    proj_corners_list = []
    for dname, gc_filenames in zip(dirnames, gc_fname_lists):
        if len(gc_filenames) != graycode.getNumberOfPatternImages() + 2:
            print('Error : invalid number of images in \'' + dname + '\'')
            return None
        imgs = []
        for fname in gc_filenames:
            # Load as color then convert to gray to match debug script behavior
            # (IMREAD_GRAYSCALE sometimes differs slightly from BGR2GRAY)
            img_color = cv2.imread(fname)
            if img_color is None:
                print('Error : failed to load \'' + fname + '\'')
                return None
            img = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
            
            if cam_shape != img.shape:
                print('Error : image size of \'' + fname + '\' is mismatch')
                return None
            imgs.append(img)
        black_img = imgs.pop()
        white_img = imgs.pop()

        res, cam_corners = cv2.findChessboardCorners(white_img, chess_shape, cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)
        if not res:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            white_img_clahe = clahe.apply(white_img)
            res, cam_corners = cv2.findChessboardCorners(white_img_clahe, chess_shape, cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)
            
        if not res:
            print('Error : chessboard was not found in \'' +
                  gc_filenames[-2] + '\'')
            return None
        if enable_subpix:
            term_crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            cv2.cornerSubPix(white_img, cam_corners, (11, 11), (-1, -1), term_crit)
        cols = chess_shape[0]
        rows = chess_shape[1]
        grid = cam_corners.reshape((rows, cols, 2))
        dists = []
        if cols > 1:
            dists.extend(np.linalg.norm(grid[:, 1:, :] - grid[:, :-1, :], axis=2).reshape(-1).tolist())
        if rows > 1:
            dists.extend(np.linalg.norm(grid[1:, :, :] - grid[:-1, :, :], axis=2).reshape(-1).tolist())

        if len(dists) == 0:
            square_px = 10.0
        else:
            square_px = float(np.median(np.array(dists, dtype=np.float32)))

        patch_size_half = int(np.clip(int(round(square_px * 0.6)), 3, 15))
        patch_area = (patch_size_half * 2 + 1) * (patch_size_half * 2 + 1)
        min_decoded = max(20, int(round(patch_area * 0.15)))
        min_inliers = max(15, int(round(min_decoded * 0.6)))

        proj_objps = []
        proj_corners = []
        cam_corners2 = []
        viz_proj_points = np.zeros(proj_shape, np.uint8)
        for corner, objp in zip(cam_corners, objps):
            c_x = int(round(corner[0][0]))
            c_y = int(round(corner[0][1]))
            src_points = []
            dst_points = []
            for dx in range(-patch_size_half, patch_size_half + 1):
                for dy in range(-patch_size_half, patch_size_half + 1):
                    x = c_x + dx
                    y = c_y + dy
                    if x < 0 or y < 0 or x >= cam_shape[1] or y >= cam_shape[0]:
                        continue
                    if int(white_img[y, x]) - int(black_img[y, x]) <= black_thr:
                        continue
                    ok, proj_pix = graycode.getProjPixel(imgs, x, y)
                    if ok:
                        src_points.append((x, y))
                        dst_points.append(gc_step*np.array(proj_pix))
            if len(src_points) < min_decoded:
                print(
                    '    Warning : corner', c_x, c_y,
                    'was skiped because decoded pixels were too few (check your images and threasholds)')
                continue
            
            # Use RANSAC to be robust against gray code decoding errors
            h_mat, inliers = cv2.findHomography(
                np.array(src_points), np.array(dst_points), cv2.RANSAC, 3.0)
                
            if h_mat is None:
                continue

            if inliers is None or int(np.count_nonzero(inliers)) < min_inliers:
                continue
                
            point = h_mat@np.array([corner[0][0], corner[0][1], 1]).transpose()
            point_pix = point[0:2]/point[2]
            if not np.isfinite(point_pix).all():
                continue
            proj_objps.append(objp)
            proj_corners.append([point_pix])
            cam_corners2.append(corner)
            
            # Ensure coordinates are within image bounds before drawing
            px, py = int(round(point_pix[0])), int(round(point_pix[1]))
            if 0 <= px < proj_shape[1] and 0 <= py < proj_shape[0]:
                viz_proj_points[py, px] = 255

        min_view_corners = max(10, int(round(len(objps) * 0.15)))
        if len(proj_corners) < min_view_corners:
            print('  Warning : too few corners were found in \'' +
                  dname + '\' (' + str(len(proj_corners)) + ' < ' + str(min_view_corners) + '), this view will be skipped')
            tag_prefix = (viz_tag + '_') if viz_tag else ''
            cv2.imwrite('visualize_corners_projector_' + tag_prefix +
                        os.path.basename(dname) + '.png', viz_proj_points)
            continue
        
        view_names.append(os.path.basename(dname))
        cam_objps_list.append(objps)
        cam_corners_list.append(cam_corners)
        proj_objps_list.append(np.float32(proj_objps))
        proj_corners_list.append(np.float32(proj_corners))
        cam_corners_list2.append(np.float32(cam_corners2))
        
        # Visualize detected projector corners for debugging
        tag_prefix = (viz_tag + '_') if viz_tag else ''
        cv2.imwrite('visualize_corners_projector_' + tag_prefix +
                    os.path.basename(dname) + '.png', viz_proj_points)

    if len(proj_corners_list) == 0:
        print('Error : no valid capture views were found')
        return None

    print('Initial solution of camera\'s intrinsic parameters')
    cam_rvecs = []
    cam_tvecs = []
    if(camP is None):
        ret, cam_int, cam_dist, cam_rvecs, cam_tvecs = cv2.calibrateCamera(
            cam_objps_list, cam_corners_list, cam_size, None, None, None, None)
        print('  RMS :', ret)
    else:
        for objp, corners in zip(cam_objps_list, cam_corners_list):
            ret, cam_rvec, cam_tvec = cv2.solvePnP(objp, corners, camP, camD) 
            cam_rvecs.append(cam_rvec)
            cam_tvecs.append(cam_tvec)
            
            # Calculate actual RMS for solvePnP
            imgpts, _ = cv2.projectPoints(objp, cam_rvec, cam_tvec, camP, camD)
            error = np.sqrt(cv2.norm(corners, imgpts, cv2.NORM_L2)**2 / len(imgpts))
            print('  RMS (PnP) :', error)
            
        cam_int = camP
        cam_dist = camD
    print('  Intrinsic parameters :')
    printNumpyWithIndent(cam_int, '    ')
    print('  Distortion parameters :')
    printNumpyWithIndent(cam_dist, '    ')
    print()

    print('Initial solution of projector\'s parameters')
    ret, proj_int, proj_dist, proj_rvecs, proj_tvecs = cv2.calibrateCamera(
        proj_objps_list, proj_corners_list, proj_size, None, None, None, None)
    print('  RMS :', ret)
    
    print('  Per-view Projector RMS:')
    proj_view_errors = []
    proj_view_names_before = list(view_names)
    for i, (objp, corners, rvec, tvec) in enumerate(zip(proj_objps_list, proj_corners_list, proj_rvecs, proj_tvecs)):
        imgpts, _ = cv2.projectPoints(objp, rvec, tvec, proj_int, proj_dist)
        error = np.sqrt(cv2.norm(corners, imgpts, cv2.NORM_L2)**2 / len(imgpts))
        proj_view_errors.append(error)
        view_name = view_names[i] if i < len(view_names) else str(i)
        print(f'    View {i} ({view_name}): {error:.4f}')
    proj_view_errors_before = list(proj_view_errors)
    view_filter_median = None
    view_filter_threshold = None
    removed_view_names = []
    removed_view_rms = []
    if enable_view_filter and len(proj_view_errors) > 0:
        err_median = float(np.median(np.array(proj_view_errors, dtype=np.float32)))
        err_thr = max(2.0, err_median * 1.5)
        kept_indices = [i for i, e in enumerate(proj_view_errors) if e <= err_thr]
        if 0 < len(kept_indices) < len(proj_objps_list):
            removed = [(view_names[i] if i < len(view_names) else str(i), float(proj_view_errors[i])) for i in range(len(proj_view_errors)) if i not in set(kept_indices)]
            removed_sorted = sorted(removed, key=lambda x: x[1], reverse=True)
            print('  Filtering views by Projector RMS')
            print('    Median : ' + str(err_median))
            print('    Threshold : ' + str(err_thr))
            print('    Kept : ' + str(len(kept_indices)) + ' / ' + str(len(proj_view_errors)))
            if len(removed_sorted) > 0:
                print('    Removed:')
                for name, e in removed_sorted:
                    print('      ' + str(name) + ' : ' + str(e))
            view_filter_median = err_median
            view_filter_threshold = err_thr
            removed_view_names = [name for name, _ in removed_sorted]
            removed_view_rms = [e for _, e in removed_sorted]
            proj_objps_list = [proj_objps_list[i] for i in kept_indices]
            proj_corners_list = [proj_corners_list[i] for i in kept_indices]
            cam_objps_list = [cam_objps_list[i] for i in kept_indices]
            cam_corners_list = [cam_corners_list[i] for i in kept_indices]
            cam_corners_list2 = [cam_corners_list2[i] for i in kept_indices]
            view_names = [view_names[i] for i in kept_indices]
            ret, proj_int, proj_dist, proj_rvecs, proj_tvecs = cv2.calibrateCamera(
                proj_objps_list, proj_corners_list, proj_size, None, None, None, None)
            print('  RMS (filtered) :', ret)
            print('  Per-view Projector RMS (filtered):')
            for i, (objp, corners, rvec, tvec) in enumerate(zip(proj_objps_list, proj_corners_list, proj_rvecs, proj_tvecs)):
                imgpts, _ = cv2.projectPoints(objp, rvec, tvec, proj_int, proj_dist)
                error = np.sqrt(cv2.norm(corners, imgpts, cv2.NORM_L2)**2 / len(imgpts))
                view_name = view_names[i] if i < len(view_names) else str(i)
                print(f'    View {i} ({view_name}): {error:.4f}')

    print('  Intrinsic parameters :')
    printNumpyWithIndent(proj_int, '    ')
    print('  Distortion parameters :')
    printNumpyWithIndent(proj_dist, '    ')
    print()

    print('=== Result ===')
    flags = cv2.CALIB_USE_INTRINSIC_GUESS | \
            cv2.CALIB_FIX_K1 | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3 | \
            cv2.CALIB_FIX_TANGENT_DIST | cv2.CALIB_FIX_K4 | cv2.CALIB_FIX_K5 | cv2.CALIB_FIX_K6
        
    ret, cam_int, cam_dist, proj_int, proj_dist, cam_proj_rmat, cam_proj_tvec, E, F = cv2.stereoCalibrate(
        proj_objps_list, cam_corners_list2, proj_corners_list, cam_int, cam_dist, proj_int, proj_dist, cam_size, flags=flags)
    print('  RMS :', ret)
    print('  Camera intrinsic parameters :')
    printNumpyWithIndent(cam_int, '    ')
    print('  Camera distortion parameters :')
    printNumpyWithIndent(cam_dist, '    ')
    print('  Projector intrinsic parameters :')
    printNumpyWithIndent(proj_int, '    ')
    print('  Projector distortion parameters :')
    printNumpyWithIndent(proj_dist, '    ')
    print('  Rotation matrix / translation vector from camera to projector')
    print('  (they translate points from camera coord to projector coord) :')
    printNumpyWithIndent(cam_proj_rmat, '    ')
    printNumpyWithIndent(cam_proj_tvec, '    ')
    print()

    fs = cv2.FileStorage(output_xml, cv2.FILE_STORAGE_WRITE)
    fs.write('img_shape', cam_shape)
    fs.write('rms', ret)
    fs.write('cam_int', cam_int)
    fs.write('cam_dist', cam_dist)
    fs.write('proj_int', proj_int)
    fs.write('proj_dist', proj_dist)
    fs.write('rotation', cam_proj_rmat)
    fs.write('translation', cam_proj_tvec)
    fs.write('proj_view_names_before', '\n'.join(proj_view_names_before))
    fs.write('proj_view_rms_before', np.array(proj_view_errors_before, dtype=np.float64).reshape(-1, 1))
    fs.write('proj_view_names_after', '\n'.join(view_names))
    if view_filter_median is not None and view_filter_threshold is not None:
        fs.write('view_filter_median', float(view_filter_median))
        fs.write('view_filter_threshold', float(view_filter_threshold))
        fs.write('removed_view_names', '\n'.join(removed_view_names))
        fs.write('removed_view_rms', np.array(removed_view_rms, dtype=np.float64).reshape(-1, 1))
    fs.release()


if __name__ == '__main__':
    main()
