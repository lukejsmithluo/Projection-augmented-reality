from __future__ import annotations

import os
import sys

import requests
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QFileDialog,
    QScrollArea,
    QHBoxLayout,
    QBoxLayout,
    QFrame,
)
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    """主窗口：模块化Tab界面"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XProjection UI")
        # 默认设置为 16:9 比例（例如 1280x720）
        self.resize(1280, 720)
        tabs = QTabWidget()
        tabs.addTab(self._mapping_tab(), "空间映射")
        tabs.addTab(self._calibration_tab(), "投影标定")
        tabs.addTab(self._ai_image_tab(), "AI图像生成")
        self.setCentralWidget(tabs)

    def _mapping_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        status = QLabel("映射控制")
        layout.addWidget(status)

        btn_start = QPushButton("开始映射")
        btn_stop = QPushButton("停止映射")

        def do_start():
            try:
                resp = requests.post(
                    "http://127.0.0.1:8000/mapping/start",
                    json={"build_mesh": True, "save_texture": True},
                    timeout=5,
                )
                status.setText(f"开始映射: {resp.status_code}")
            except Exception as e:
                status.setText(f"开始映射失败: {e}")

        def do_stop():
            try:
                resp = requests.post("http://127.0.0.1:8000/mapping/stop", timeout=5)
                status.setText(f"停止映射: {resp.status_code}")
            except Exception as e:
                status.setText(f"停止映射失败: {e}")

        btn_start.clicked.connect(do_start)
        btn_stop.clicked.connect(do_stop)
        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)
        w.setLayout(layout)
        return w

    def _calibration_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        status = QLabel("标定控制")
        layout.addWidget(status)

        btn_run = QPushButton("开始标定")

        def do_run():
            try:
                resp = requests.post(
                    "http://127.0.0.1:8000/calibration/run",
                    json={"proj_height": 1080, "proj_width": 1920, "rounds": 1},
                    timeout=5,
                )
                status.setText(f"开始标定: {resp.status_code}")
            except Exception as e:
                status.setText(f"开始标定失败: {e}")

        btn_run.clicked.connect(do_run)
        layout.addWidget(btn_run)
        w.setLayout(layout)
        return w

    def _ai_image_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()

        status = QLabel("AI图像生成：上传图片+提示词")
        layout.addWidget(status)

        prompt_input = QLineEdit()
        prompt_input.setPlaceholderText("请输入提示词（如：make it look like watercolor）")
        layout.addWidget(prompt_input)

        size_input = QLineEdit()
        size_input.setPlaceholderText("尺寸（可选，默认1024x1024，例如：512x512）")
        layout.addWidget(size_input)

        # OpenAI API Key 输入（默认隐藏），右侧按钮可切换显示
        api_key_row = QHBoxLayout()
        api_key_input = QLineEdit()
        api_key_input.setPlaceholderText("OpenAI API Key（可选）")
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        btn_toggle_key = QPushButton("显示")

        def do_toggle_key():
            if api_key_input.echoMode() == QLineEdit.EchoMode.Password:
                api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
                btn_toggle_key.setText("隐藏")
            else:
                api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
                btn_toggle_key.setText("显示")

        btn_toggle_key.clicked.connect(do_toggle_key)
        api_key_row.addWidget(QLabel("OpenAI API Key:"))
        api_key_row.addWidget(api_key_input)
        api_key_row.addWidget(btn_toggle_key)
        layout.addLayout(api_key_row)

        file_label = QLabel("未选择图片")
        layout.addWidget(file_label)

        btn_choose = QPushButton("选择图片")
        btn_clear = QPushButton("清空已选图片")
        btn_generate = QPushButton("生成图片")
        btn_open_dir = QPushButton("打开输出目录")
        btn_preview_latest = QPushButton("预览最新输出")

        # 多图选择：维护已选择图片列表
        file_paths: list[str] = []

        # 选择图片后进行缩略图预览（右到左排布）
        # 16:9 框（例如 640x360），内部为横向滚动的缩略图区域
        thumbs_frame = QFrame()
        thumbs_frame.setFrameShape(QFrame.Shape.StyledPanel)
        thumbs_frame.setFixedSize(640, 360)  # 16:9 框

        uploads_area = QScrollArea(thumbs_frame)
        uploads_area.setWidgetResizable(True)
        uploads_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        uploads_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        uploads_container = QWidget()
        uploads_layout = QHBoxLayout()
        uploads_layout.setSpacing(8)
        # 使用 LeftToRight 方向，但每次将新缩略图插入到最前（index 0），
        # 保证最新选择的图片显示在最左，最早的在最右。
        uploads_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        uploads_container.setLayout(uploads_layout)
        uploads_area.setWidget(uploads_container)
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(6, 6, 6, 6)
        frame_layout.addWidget(uploads_area)
        thumbs_frame.setLayout(frame_layout)
        layout.addWidget(QLabel("已选择图片预览（左→右，最多3张可见，更多可滑动）："))
        layout.addWidget(thumbs_frame)

        def _add_thumbnail(path: str) -> None:
            lbl = QLabel()
            # 16:9 缩略图尺寸，保证比例不破坏，同时尽量填充显示
            lbl.setFixedSize(200, 112)
            lbl.setScaledContents(True)
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(200, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
            else:
                lbl.setText("无法加载")
            # 追加到末尾，保证最早在左、最新在右
            uploads_layout.addWidget(lbl)

        def do_choose():
            paths, _ = QFileDialog.getOpenFileNames(
                w, "选择图片（可多选）", "", "Images (*.png *.jpg *.jpeg)"
            )
            if paths:
                file_paths.extend(paths)
                file_label.setText(f"已选择 {len(file_paths)} 张，最新：{paths[-1]}")
                for p in paths:
                    _add_thumbnail(p)
            else:
                file_label.setText("未选择图片")

        def do_clear():
            file_paths.clear()
            file_label.setText("未选择图片")
            # 清理缩略图
            while uploads_layout.count():
                item = uploads_layout.takeAt(0)
                wdg = item.widget()
                if wdg is not None:
                    wdg.deleteLater()

        # 预览区域
        preview = QLabel("预览区域")
        preview.setMinimumHeight(320)
        preview.setScaledContents(True)
        layout.addWidget(preview)

        def _guess_mime(path: str) -> str:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                return "image/jpeg"
            return "image/png"

        def do_generate():
            p = prompt_input.text().strip()
            s = size_input.text().strip()
            api_key = api_key_input.text().strip()
            fp = file_paths[-1] if file_paths else None
            if not p:
                status.setText("提示：请先填写提示词")
                return
            if not fp:
                status.setText("提示：请先选择图片")
                return
            try:
                # multipart/form-data：按选择顺序（最早→最新）传递多图
                opened_files = []
                try:
                    files_arg = []
                    for pth in file_paths:
                        f = open(pth, "rb")
                        opened_files.append(f)
                        fname = os.path.basename(pth)
                        files_arg.append((
                            "images",
                            (fname, f, _guess_mime(pth)),
                        ))
                    data = {"prompt": p}
                    if s:
                        data["size"] = s
                    if api_key:
                        data["api_key"] = api_key
                    resp = requests.post(
                        "http://127.0.0.1:8000/ai-image/edit", files=files_arg, data=data, timeout=30
                    )
                finally:
                    for f in opened_files:
                        try:
                            f.close()
                        except Exception:
                            pass
                if resp.ok:
                    payload = resp.json()
                    if payload.get("accepted"):
                        out = payload.get("output_file") or ""
                        status.setText(f"生成成功：{out}")
                        if out and os.path.exists(out):
                            pix = QPixmap(out)
                            if not pix.isNull():
                                # 以保持比例的方式填充预览区域
                                scaled = pix.scaled(preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                                preview.setPixmap(scaled)
                            else:
                                preview.setText("预览失败：无法加载图片")
                    else:
                        status.setText(f"生成失败：{payload.get('error_code')} - {payload.get('error')}")
                else:
                    status.setText(f"请求失败：HTTP {resp.status_code}")
            except Exception as e:
                status.setText(f"生成异常：{e}")

        def do_open_dir():
            try:
                # Windows 打开输出目录
                os.startfile(os.path.abspath("data/ai_images/outputs"))  # type: ignore[attr-defined]
            except Exception as e:
                status.setText(f"打开目录失败：{e}")

        def do_preview_latest():
            try:
                out_dir = os.path.abspath("data/ai_images/outputs")
                if not os.path.isdir(out_dir):
                    status.setText("提示：尚无输出目录或未生成过图片")
                    return
                # 查找最近输出图片（png/jpg/jpeg）
                import glob
                files = []
                for pat in ("*.png", "*.jpg", "*.jpeg"):
                    files.extend(glob.glob(os.path.join(out_dir, pat)))
                if not files:
                    status.setText("提示：输出目录中没有图片文件")
                    return
                latest = max(files, key=lambda p: os.path.getmtime(p))
                pix = QPixmap(latest)
                if not pix.isNull():
                    preview.setPixmap(pix)
                    status.setText(f"已预览：{latest}")
                else:
                    preview.setText("预览失败：无法加载图片")
            except Exception as e:
                status.setText(f"预览异常：{e}")

        btn_choose.clicked.connect(do_choose)
        btn_clear.clicked.connect(do_clear)
        btn_generate.clicked.connect(do_generate)
        btn_open_dir.clicked.connect(do_open_dir)
        btn_preview_latest.clicked.connect(do_preview_latest)
        layout.addWidget(btn_choose)
        layout.addWidget(btn_clear)
        layout.addWidget(btn_generate)
        layout.addWidget(btn_open_dir)
        layout.addWidget(btn_preview_latest)

        w.setLayout(layout)
        return w


def main() -> None:
    """启动 PyQt6 UI"""
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
