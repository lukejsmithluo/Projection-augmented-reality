# procam-calibration

This repository provides python scripts to calibrate projector-camera system using a chessboard and structured light (the gray codes).

## Requirement

* Python
    * Python 3 is recommended
* OpenCV
    * `python -m pip install opencv-python opencv-contrib-python`
* ZED SDK (for ZED camera users)
    * `pyzed`
* Screeninfo
    * `python -m pip install screeninfo`
* Printed chessboard
    * You can find PDF [here](http://opencv.jp/sample/pics/chesspattern_7x10.pdf)

## How to use

### Step 0: Automated Data Acquisition (Recommended for ZED users)

If you have a ZED camera and a projector, you can use `capture_data.py` to automate the projection and capture process.

```sh
python capture_data.py <projector_pixel_height> <projector_pixel_width> [--monitor <monitor_index>] [--pattern_dir <pattern_directory>]

# example (generate patterns on the fly)
python capture_data.py 720 1280 --monitor 1

# example (use pre-generated patterns)
python capture_data.py 720 1280 --monitor 1 --pattern_dir "./graycode_pattern"
```

This script will:
1. Initialize the ZED camera (2K, 15FPS, Neural Plus).
2. Generate gray code patterns in memory (or load them from `pattern_dir` if specified).
3. Open a full-screen window on the specified monitor (projector).
4. Wait for you to position the chessboard and press 'Enter'.
5. Automatically project patterns and capture images to `capture_0`, `capture_1`, etc.

### Step 1 : Generate gray code patterns (Manual method)

If you are NOT using the automated script above, you need to generate patterns first.

Open your terminal and type the following command.

```sh
python gen_graycode_imgs.py <projector_pixel_height> <projector_pixel_width> [-graycode_step <graycode_step(default=1)>]

# example
python gen_graycode_imgs.py 768 1024 -graycode_step 1
```

Generated images will be stored in `./graycode_pattern/`.

`graycode_step` is an option to specify the pixel size of bits in the gray code images.
If you get moire pattern in the captured images in the next step, increase this variable.

### Step 2 : Project and capture the gray code patterns

Set up your system and place a chessboard in front of the projector and camera.
Then, project the gray code patterns generated in the previous step from the projector to it and capture it from the camera.

Although minimum required shot is one, it is recommended to capture more than 5 times with different attitudes of the chessboard to improve the calibration accuracy.

Captured images must be saved as `./capture_*/graycode_*.(png/jpg)`.

<table>
   <tr>
      <td><img src="./sample_data/capture_0/graycode_40.png"></td>
      <td><img src="./sample_data/capture_0/graycode_15.png"></td>
   </tr>
</table>

### Step 3 : Calibrate projector & camera parameters

After saving the captured images, run the following command.

```sh
python calibrate.py <projector_pixel_height> <projector_pixel_width> <num_chess_corners_vert> <num_chess_corners_hori> <chess_block_size> <graycode_step> [-black_thr <black_thr(default=40)>] [-white_thr <white_thr(default=5)>] [-camera <camera_parameter_json>] [-input_dir <input_directory(default=./)>]

# example (using sample_data)
python calibrate.py 768 1024 9 7 75 1 -black_thr 40 -white_thr 5 -input_dir "./sample_data"
```

`chess_block_size` means the length (mm cm m) of a block on the chessboard.
The translation vectors will be calculated with the units of length used here.

`black_threashold` is a threashold to determine whether a camera pixel captures projected area or not.
`white_threashold` is a threashold to specify the robustness of gray code decoding.
To avoid decoding errors, increase these variables.

`camera_paramter_json` is a json file, in which internal camera paramters (projection matrix P, camera distortion, and image size) are written.
By indicating this option, the intrinsic camera parameters will be fixed when compute the initial solution of the camera attitudes.
See "camera_config.json" as an example.

`input_dir` is the directory containing the `capture_*` folders. If not specified, the script looks in the current directory.

Calibration result will be displayed on your terminal and saved in `./calibration_result.xml` (with cv::FileStorage format).

#### Debugging & Visualization
*   **Visualizing Detected Projector Corners**: The script automatically saves debug images named `visualize_corners_projector_capture_X.png`. Check these images to verify if the projector's chessboard corners are correctly identified.
*   **High RMS Error**: If you get high RMS error (> 2.0), check the per-view RMS output in the terminal. If specific views have high error, they likely contain outliers (decoding errors) or poor detections.
*   **Robustness**: The script uses RANSAC for homography estimation to filter out gray code decoding errors.

#### 常见问题（Troubleshooting）
*   如果终端频繁出现 `was skiped because decoded pixels were too few` 或 `too few corners were found (less than 3)`，通常表示棋盘角点附近“可被灰码稳定解码”的像素太少（棋盘在图像中太小/离得太远、棋盘不在投影覆盖范围内、投影对比度不足或曝光波动等都会导致）。
*   优先确保：`proj_height/proj_width/graycode_step` 在采集与标定时完全一致，并让棋盘尽量占据相机画面的较大区域且大部分位于投影光斑内；在此基础上再调 `black_thr/white_thr`。
*   如果 `=== Result === RMS` 特别大且内参/畸变参数明显发散，通常说明存在离群对应点或某些视图质量过差；建议检查 `visualize_corners_projector_capture_X.png`，并删除或重拍点数过少的 `capture_X` 视图。

## Additional Resource

This repository utilize the stereo calibration method in OpenCV. See the OpenCV documentation for details on coordinate systems, calibration method and output parameters.

This software calculates local homographies at around chessboard corners to estimate corresponding projector pixels with subpixel accuracy.
This algorithm is based on the following paper.

```
MORENO, Daniel; TAUBIN, Gabriel. Simple, accurate, and robust projector-camera calibration. In: 3D Imaging, Modeling, Processing, Visualization and Transmission (3DIMPVT), 2012 Second International Conference on. IEEE, 2012. p. 464-471.
```
