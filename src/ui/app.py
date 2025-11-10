from __future__ import annotations

import sys

import requests
from PyQt6.QtWidgets import (QApplication, QLabel, QMainWindow, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)


class MainWindow(QMainWindow):
    """主窗口：模块化Tab界面"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XProjection UI")
        tabs = QTabWidget()
        tabs.addTab(self._mapping_tab(), "空间映射")
        tabs.addTab(self._calibration_tab(), "投影标定")
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


def main() -> None:
    """启动 PyQt6 UI"""
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
