import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

WINDOW_NAME = "Image Center Tuner"


def parse_principal_point(value: float, resolution: int) -> float:
    """Accept either normalized principal point or pixel value."""
    if abs(value) > 2.0:
        return value / float(resolution)
    return value


def to_pixel_value(value_norm: float, resolution: int) -> float:
    return value_norm * float(resolution)


def draw_overlay(image, pairs, pending_target):
    canvas = image.copy()

    for idx, (target, projected) in enumerate(pairs, start=1):
        target_i = tuple(np.round(target).astype(int))
        projected_i = tuple(np.round(projected).astype(int))

        cv2.circle(canvas, target_i, 6, (0, 255, 0), -1)
        cv2.circle(canvas, projected_i, 6, (0, 0, 255), -1)
        cv2.line(canvas, target_i, projected_i, (255, 255, 0), 2)

        label_pos = (target_i[0] + 8, target_i[1] - 8)
        cv2.putText(
            canvas,
            str(idx),
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    if pending_target is not None:
        target_i = tuple(np.round(pending_target).astype(int))
        cv2.circle(canvas, target_i, 7, (0, 255, 0), 2)
        cv2.putText(
            canvas,
            "click projected point",
            (target_i[0] + 10, target_i[1] + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    help_lines = [
        "Left click: target(real) -> projected(actual)",
        "Backspace/U: undo   R: reset   Enter/S: finish   Q/Esc: quit",
    ]
    y = 28
    for line in help_lines:
        cv2.putText(
            canvas,
            line,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        y += 28

    return canvas


def collect_pairs(image_path: Path):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Failed to read image: {image_path}")

    return collect_pairs_from_image(image)


def capture_image_from_camera(
    camera_index: int,
    width: int | None = None,
    height: int | None = None,
    capture_out: Path | None = None,
):
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera index {camera_index}.")

    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    preview_window = "Camera Preview - Space: capture, Q/Esc: quit"
    captured = None

    print("Camera preview opened.")
    print("  Space: capture current frame")
    print("  Q/Esc: quit")
    printed_frame_size = False

    while True:
        ok, frame = cap.read()
        if not ok:
            cap.release()
            cv2.destroyWindow(preview_window)
            raise RuntimeError("Failed to read frame from camera.")

        if not printed_frame_size:
            frame_height, frame_width = frame.shape[:2]
            print(f"Actual camera frame size: {frame_width} x {frame_height}")
            printed_frame_size = True

        display = frame.copy()
        cv2.putText(
            display,
            "Space: capture   Q/Esc: quit",
            (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(preview_window, display)

        key = cv2.waitKey(20) & 0xFF
        if key == 32:
            captured = frame.copy()
            break
        if key in (27, ord("q")):
            cap.release()
            cv2.destroyWindow(preview_window)
            raise KeyboardInterrupt("Camera capture cancelled.")

    cap.release()
    cv2.destroyWindow(preview_window)

    if capture_out:
        cv2.imwrite(str(capture_out), captured)
        print(f"Captured image saved to: {capture_out}")

    return captured


def collect_pairs_from_image(image):
    pairs = []
    pending_target = None

    def on_mouse(event, x, y, flags, userdata):
        nonlocal pending_target
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        point = np.array([float(x), float(y)], dtype=np.float64)
        if pending_target is None:
            pending_target = point
            print(f"Target point:    ({x:.1f}, {y:.1f})")
        else:
            pairs.append((pending_target, point))
            print(f"Projected point: ({x:.1f}, {y:.1f})  -> pair #{len(pairs)}")
            pending_target = None

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    while True:
        cv2.imshow(WINDOW_NAME, draw_overlay(image, pairs, pending_target))
        key = cv2.waitKey(20) & 0xFF

        if key in (13, ord("s")):
            break
        if key in (27, ord("q")):
            cv2.destroyWindow(WINDOW_NAME)
            raise KeyboardInterrupt("Selection cancelled.")
        if key in (8, ord("u")):
            if pending_target is not None:
                pending_target = None
                print("Undo pending target point.")
            elif pairs:
                pairs.pop()
                print("Undo last pair.")
        if key == ord("r"):
            pairs.clear()
            pending_target = None
            print("Reset all pairs.")

    cv2.destroyWindow(WINDOW_NAME)
    return pairs


def load_pairs_from_csv(csv_path: Path):
    pairs = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"target_x", "target_y", "projected_x", "projected_y"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        for row in reader:
            target = np.array(
                [float(row["target_x"]), float(row["target_y"])], dtype=np.float64
            )
            projected = np.array(
                [float(row["projected_x"]), float(row["projected_y"])],
                dtype=np.float64,
            )
            pairs.append((target, projected))
    return pairs


def save_pairs_to_csv(csv_path: Path, pairs):
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["target_x", "target_y", "projected_x", "projected_y"])
        for target, projected in pairs:
            writer.writerow([target[0], target[1], projected[0], projected[1]])


def calculate_update(
    pairs,
    photo_width: int,
    photo_height: int,
    cx_norm: float,
    cy_norm: float,
    gain: float,
):
    targets = np.array([target for target, _ in pairs], dtype=np.float64)
    projected = np.array([projected for _, projected in pairs], dtype=np.float64)
    residuals = projected - targets

    mean_residual = residuals.mean(axis=0)
    rms = float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))

    # Image coordinates are +X right, +Y down. If the projected image appears
    # right/down in the photo, reduce Cx/Cy. If it appears up, Cy increases.
    delta_cx = -gain * mean_residual[0] / float(photo_width)
    delta_cy = -gain * mean_residual[1] / float(photo_height)

    return {
        "num_pairs": len(pairs),
        "mean_dx_photo_px": float(mean_residual[0]),
        "mean_dy_photo_px": float(mean_residual[1]),
        "rms_photo_px": rms,
        "delta_cx_norm": float(delta_cx),
        "delta_cy_norm": float(delta_cy),
        "cx_new_norm": float(cx_norm + delta_cx),
        "cy_new_norm": float(cy_norm + delta_cy),
        "residuals": residuals,
    }


def print_report(result, cx_norm, cy_norm, proj_width, proj_height, gain):
    print("")
    print("=" * 72)
    print("Image Center tuning report")
    print("=" * 72)
    print(f"Pairs: {result['num_pairs']}")
    print(f"Gain:  {gain:g}")
    print("")
    print("Observed photo residual, projected(actual) - target(real):")
    print(f"  Mean dx: {result['mean_dx_photo_px']:+.3f} px  (+ means right)")
    print(f"  Mean dy: {result['mean_dy_photo_px']:+.3f} px  (+ means down)")
    print(f"  RMS:     {result['rms_photo_px']:.3f} px")
    print("")
    print("Current LensFile Image Center:")
    print(f"  Cx: {cx_norm:.8f}  ({to_pixel_value(cx_norm, proj_width):.3f} px)")
    print(f"  Cy: {cy_norm:.8f}  ({to_pixel_value(cy_norm, proj_height):.3f} px)")
    print("")
    print("Suggested next Image Center:")
    print(
        f"  Cx: {result['cx_new_norm']:.8f}  "
        f"({to_pixel_value(result['cx_new_norm'], proj_width):.3f} px)"
    )
    print(
        f"  Cy: {result['cy_new_norm']:.8f}  "
        f"({to_pixel_value(result['cy_new_norm'], proj_height):.3f} px)"
    )
    print("")
    print("Delta:")
    print(
        f"  dCx: {result['delta_cx_norm']:+.8f}  "
        f"({to_pixel_value(result['delta_cx_norm'], proj_width):+.3f} px)"
    )
    print(
        f"  dCy: {result['delta_cy_norm']:+.8f}  "
        f"({to_pixel_value(result['delta_cy_norm'], proj_height):+.3f} px)"
    )
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Semi-manual tuner for UE LensFile Image Center. Click each real "
            "target point first, then the corresponding projected actual point."
        )
    )
    parser.add_argument("--image", type=Path, help="Photo used for manual picking.")
    parser.add_argument(
        "--camera-index",
        type=int,
        help="Open a camera preview and press Space to capture a photo.",
    )
    parser.add_argument("--camera-width", type=int, help="Requested camera width.")
    parser.add_argument("--camera-height", type=int, help="Requested camera height.")
    parser.add_argument(
        "--capture-out",
        type=Path,
        help="Optional path for saving the captured camera frame.",
    )
    parser.add_argument("--pairs-csv", type=Path, help="Load point pairs from CSV.")
    parser.add_argument(
        "--save-pairs-csv", type=Path, help="Save clicked point pairs to CSV."
    )
    parser.add_argument("--cx", type=float, required=True, help="Current Cx.")
    parser.add_argument("--cy", type=float, required=True, help="Current Cy.")
    parser.add_argument("--proj-width", type=int, default=1280)
    parser.add_argument("--proj-height", type=int, default=720)
    parser.add_argument(
        "--gain",
        type=float,
        default=0.5,
        help=(
            "Feedback gain. Use 0.25-0.5 for external-camera photos; increase "
            "only if the correction direction is stable but too small."
        ),
    )
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    if args.pairs_csv is None and args.image is None and args.camera_index is None:
        parser.error("One of --image, --camera-index, or --pairs-csv is required.")

    cx_norm = parse_principal_point(args.cx, args.proj_width)
    cy_norm = parse_principal_point(args.cy, args.proj_height)

    if args.pairs_csv:
        pairs = load_pairs_from_csv(args.pairs_csv)
        if args.image:
            image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(f"Failed to read image: {args.image}")
            photo_height, photo_width = image.shape[:2]
        else:
            photo_width = args.proj_width
            photo_height = args.proj_height
    else:
        if args.camera_index is not None:
            image = capture_image_from_camera(
                args.camera_index,
                width=args.camera_width,
                height=args.camera_height,
                capture_out=args.capture_out,
            )
            pairs = collect_pairs_from_image(image)
        else:
            image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(f"Failed to read image: {args.image}")
            pairs = collect_pairs_from_image(image)
        photo_height, photo_width = image.shape[:2]

    if len(pairs) < 1:
        raise ValueError("At least one point pair is required.")

    if args.save_pairs_csv:
        save_pairs_to_csv(args.save_pairs_csv, pairs)

    result = calculate_update(
        pairs=pairs,
        photo_width=photo_width,
        photo_height=photo_height,
        cx_norm=cx_norm,
        cy_norm=cy_norm,
        gain=args.gain,
    )
    print_report(result, cx_norm, cy_norm, args.proj_width, args.proj_height, args.gain)

    if args.json_out:
        serializable = dict(result)
        serializable.pop("residuals")
        args.json_out.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
