from __future__ import annotations

import os
import sys

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


def _api_get(path: str, **kwargs):
    return requests.get(
        API_BASE_URL + path,
        proxies={"http": None, "https": None},
        **kwargs,
    )


def _api_post(path: str, **kwargs):
    return requests.post(
        API_BASE_URL + path,
        proxies={"http": None, "https": None},
        **kwargs,
    )


class MainWindow(QMainWindow):
    """主窗口：模块化Tab界面"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XProjection UI")
        # 默认设置为 16:9 比例（例如 1280x720）
        self.resize(1280, 720)
        # AI 标签页中的预览与选择窗口（用于自适应调整）
        self._ai_tab: QWidget | None = None
        self._ai_preview_frame: QFrame | None = None
        self._ai_preview_label: QLabel | None = None
        self._ai_thumbs_frame: QFrame | None = None
        tabs = QTabWidget()
        tabs.addTab(self._mapping_tab(), "空间映射")
        tabs.addTab(self._calibration_tab(), "投影标定")
        tabs.addTab(self._ai_image_tab(), "AI图像生成")
        self.setCentralWidget(tabs)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # 动态调整 AI 标签页的两个 16:9 窗口尺寸（水平自适应、居中）
        try:
            if (
                self._ai_tab
                and self._ai_preview_frame
                and self._ai_preview_label
                and self._ai_thumbs_frame
            ):
                avail_width = max(
                    320, self._ai_tab.width() - 48
                )  # 左右各留 24px 安全区
                # 统一 16:9 尺寸
                target_w = avail_width
                target_h = int(target_w * 9 / 16)
                # 输出预览窗口
                self._ai_preview_frame.setFixedSize(target_w, target_h)
                self._ai_preview_label.setFixedSize(target_w, target_h)
                # 选择预览窗口
                self._ai_thumbs_frame.setFixedSize(target_w, target_h)
        except Exception:
            pass

    def _mapping_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        status = QLabel("映射控制")
        # 允许选择与复制错误/状态文本
        status.setWordWrap(True)
        status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(status)

        btn_start = QPushButton("开始映射")
        btn_stop = QPushButton("停止映射")

        def do_start():
            try:
                resp = _api_post(
                    "/mapping/start",
                    json={"build_mesh": True, "save_texture": True},
                    timeout=5,
                )
                status.setText(f"开始映射: {resp.status_code}")
            except Exception as e:
                status.setText(f"开始映射失败: {e}")

        def do_stop():
            try:
                resp = _api_post("/mapping/stop", timeout=5)
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
        status.setWordWrap(True)
        status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(status)

        btn_run = QPushButton("开始标定")

        def do_run():
            try:
                resp = _api_post(
                    "/calibration/run",
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
        self._ai_tab = w
        layout = QVBoxLayout()
        # 整体安全区（左右上下均 24px）
        layout.setContentsMargins(24, 24, 24, 24)

        status = QLabel("AI图像生成：上传图片+提示词")
        status.setWordWrap(True)
        status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        # 添加复制按钮，便于快速复制错误/状态文本
        status_row = QHBoxLayout()
        btn_copy_status = QPushButton("复制状态")
        btn_copy_status.clicked.connect(
            lambda: QApplication.clipboard().setText(status.text())
        )
        status_row.addWidget(status)
        status_row.addWidget(btn_copy_status)
        layout.addLayout(status_row)

        # 地区状态展示（细粒度：国家/城市/允许/连通/原因），并提供刷新按钮
        region_label = QLabel("地区状态：查询中…")
        region_label.setWordWrap(True)
        region_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        btn_region_refresh = QPushButton("刷新地区状态")
        btn_copy_region = QPushButton("复制地区状态")
        btn_copy_region.clicked.connect(
            lambda: QApplication.clipboard().setText(region_label.text())
        )

        def refresh_region():
            try:
                resp = _api_get("/policy/region/status", timeout=5)
                if resp.ok:
                    j = resp.json()
                    cc = j.get("country_code") or "UNKNOWN"
                    city = j.get("city") or ""
                    allowed = j.get("allowed")
                    conn = j.get("connectivity_ok")
                    reason = j.get("reason") or ""
                    region_label.setText(
                        f"地区：{cc} {city}｜允许={allowed}｜连通={conn}｜原因={reason}"
                    )
                else:
                    region_label.setText(f"地区状态请求失败：HTTP {resp.status_code}")
            except Exception as e:
                region_label.setText(f"地区状态异常：{e}")

        btn_region_refresh.clicked.connect(refresh_region)
        # 地区状态与操作按钮排成一行
        region_row = QHBoxLayout()
        region_row.addWidget(region_label)
        region_row.addWidget(btn_region_refresh)
        region_row.addWidget(btn_copy_region)
        layout.addLayout(region_row)
        # 初始化拉取一次状态
        refresh_region()

        prompt_input = QLineEdit()
        prompt_input.setPlaceholderText(
            "请输入提示词（如：make it look like watercolor）"
        )
        layout.addWidget(prompt_input)

        # OpenAI 尺寸输入（仅 gpt-image-1 使用）
        size_input = QLineEdit()
        size_input.setPlaceholderText("尺寸（OpenAI：256x256/512x512/1024x1024）")
        layout.addWidget(size_input)

        # Gemini 输入（宽高比 + 分辨率下拉，仅 Gemini 使用）
        gem_row = QHBoxLayout()
        ar_label = QLabel("Aspect Ratio:")
        ar_select = QComboBox()
        ar_select.addItems(
            ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
        )
        res_label = QLabel("Resolution:")
        res_select = QComboBox()
        res_select.addItems(["1K", "2K", "4K"])  # Gemini 3 Pro Image 支持 1K/2K/4K
        gem_row.addWidget(ar_label)
        gem_row.addWidget(ar_select)
        gem_row.addWidget(res_label)
        gem_row.addWidget(res_select)
        layout.addLayout(gem_row)
        # 初始默认：显示 Gemini（与默认模型一致），隐藏 OpenAI 尺寸输入由后续联动处理

        # 模型选择（下拉，限定为图像生成模型；默认使用 Gemini 图像模型）
        model_select = QComboBox()
        model_select.addItems(
            [
                "gemini-2.5-flash-image",
                "gemini-3-pro-image-preview",
                "gpt-image-1",
            ]
        )
        model_select.setCurrentIndex(0)
        layout.addWidget(model_select)

        # 根据模型联动显示/隐藏输入控件
        def update_input_mode():
            lm = model_select.currentText().strip().lower()
            is_gem = lm.startswith("gemini") or lm.startswith("imagen")
            size_input.setVisible(not is_gem)
            ar_label.setVisible(is_gem)
            ar_select.setVisible(is_gem)
            res_label.setVisible(is_gem)
            res_select.setVisible(is_gem)
            if is_gem:
                status.setText(
                    "提示：Gemini 请选择宽高比（必选）与分辨率（1K/2K/4K，可选）"
                )
            else:
                status.setText("提示：OpenAI 尺寸仅支持 256x256 / 512x512 / 1024x1024")

        model_select.currentTextChanged.connect(lambda _: update_input_mode())
        update_input_mode()

        # API Key 输入（默认隐藏），右侧按钮可切换显示；根据选择的模型对应提供者
        api_key_row = QHBoxLayout()
        api_key_input = QLineEdit()
        api_key_input.setPlaceholderText("API Key（根据模型选择对应的提供者）")
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
        api_key_row.addWidget(QLabel("API Key:"))
        api_key_row.addWidget(api_key_input)
        api_key_row.addWidget(btn_toggle_key)
        layout.addLayout(api_key_row)

        # 组织 ID 输入（可选，用于指定组织）
        org_row = QHBoxLayout()
        org_id_input = QLineEdit()
        org_id_input.setPlaceholderText("OpenAI Org ID（仅 OpenAI 使用，可选）")
        org_row.addWidget(QLabel("OpenAI Org ID:"))
        org_row.addWidget(org_id_input)
        layout.addLayout(org_row)

        file_label = QLabel("未选择图片")
        file_label.setWordWrap(True)
        file_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(file_label)

        # 底部按钮将被替换为预览窗口上的内联控件（加号/叉号），因此不再使用传统“选择/清空”按钮
        btn_generate = QPushButton("生成图片")
        btn_open_dir = QPushButton("打开输出目录")
        btn_preview_latest = QPushButton("预览最新输出")

        # 多图选择：维护已选择图片列表
        file_paths: list[str] = []

        # 选择图片后进行缩略图预览（横向滚动）
        # 16:9 框（横向自适应窗口宽度，居中摆放）
        thumbs_frame = QFrame()
        thumbs_frame.setFrameShape(QFrame.Shape.StyledPanel)
        # 初始尺寸将由窗口 resize 时动态调整为 16:9

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
        # 顶部左侧“叉号”：清空选择
        clear_row = QHBoxLayout()
        btn_clear_all = QPushButton("×")
        btn_clear_all.setFixedSize(24, 24)
        btn_clear_all.setToolTip("清空已选图片")
        clear_row.addWidget(btn_clear_all)
        clear_row.addStretch(1)
        frame_layout.addLayout(clear_row)
        frame_layout.addWidget(uploads_area)
        thumbs_frame.setLayout(frame_layout)
        layout.addWidget(QLabel("已选择图片预览（左→右，最多3张可见，更多可滑动）："))
        layout.addWidget(thumbs_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # 内联“加号”添加图片控件（始终位于最右侧）
        add_item = QFrame()
        add_item.setFrameShape(QFrame.Shape.StyledPanel)
        add_item.setFixedSize(200, 112)
        add_item_layout = QVBoxLayout()
        add_item_layout.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton("＋")
        add_btn.setToolTip("添加图片")
        add_btn.setFixedSize(48, 48)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_item_layout.addStretch(1)
        add_item_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        add_item_layout.addStretch(1)
        add_item.setLayout(add_item_layout)

        def _ensure_add_item_rightmost():
            # 保证加号控件始终在最右侧
            uploads_layout.removeWidget(add_item)
            add_item.setParent(uploads_container)
            uploads_layout.addWidget(add_item)

        def _max_images_for_model(model_name: str) -> int:
            """根据当前模型名称返回允许的最大上传图片数量。
            - OpenAI gpt-image-1：1 张
            - Gemini 3 Pro Image Preview：14 张
            - 其他 Gemini/Imagen：默认 16 张
            """
            m = (model_name or "").strip().lower()
            if m == "gpt-image-1":
                return 1
            if m.startswith("gemini-3-pro-image-preview"):
                return 14
            if m.startswith("gemini") or m.startswith("imagen"):
                return 16
            return 16

        def _add_thumbnail(path: str) -> None:
            # 缩略图容器，带右上角减号
            item = QFrame()
            item.setFrameShape(QFrame.Shape.StyledPanel)
            item.setFixedSize(200, 112)
            # 主图
            img = QLabel()
            img.setFixedSize(200, 112)
            img.setScaledContents(True)
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(
                    200,
                    112,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                img.setPixmap(pix)
            else:
                img.setText("无法加载")
            # 将减号按钮直接作为子控件叠放到右上角（避免改变高度）
            v = QVBoxLayout()
            v.setContentsMargins(0, 0, 0, 0)
            v.addWidget(img)
            item.setLayout(v)
            btn_remove = QPushButton("－", parent=item)
            btn_remove.setFixedSize(24, 24)
            btn_remove.setToolTip("移除该图片")
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            # 按钮放在右上角（略微内缩 4px）
            btn_remove.move(200 - 24 - 4, 4)

            # 记录路径以便删除时更新
            item.image_path = path  # 动态属性

            def on_remove():
                # 从布局和列表中移除此项
                try:
                    uploads_layout.removeWidget(item)
                    item.deleteLater()
                except Exception:
                    pass
                try:
                    if path in file_paths:
                        file_paths.remove(path)
                except Exception:
                    pass
                if file_paths:
                    file_label.setText(
                        f"已选择 {len(file_paths)} 张，最新：{file_paths[-1]}"
                    )
                else:
                    file_label.setText("未选择图片")
                _ensure_add_item_rightmost()

            btn_remove.clicked.connect(on_remove)
            # 插入到加号前，使加号位于最右
            count = uploads_layout.count()
            if count == 0:
                uploads_layout.addWidget(item)
            else:
                uploads_layout.insertWidget(count - 1, item)
            _ensure_add_item_rightmost()

        def do_choose():
            paths, _ = QFileDialog.getOpenFileNames(
                w, "选择图片（可多选）", "", "Images (*.png *.jpg *.jpeg)"
            )
            if paths:
                # 计算按模型限制后的列表（保留最新的若干张）
                limit = _max_images_for_model(model_select.currentText())
                merged = file_paths + paths
                if len(merged) > limit:
                    dropped = len(merged) - limit
                    merged = merged[-limit:]
                    status.setText(
                        f"提示：当前模型最多允许 {limit} 张，较早的 {dropped} 张已忽略。"
                    )
                # 重建缩略图视图以与限制后的列表保持一致
                # 先清理现有缩略图（保留加号控件）
                while uploads_layout.count():
                    item = uploads_layout.takeAt(0)
                    wdg = item.widget()
                    if wdg is not None:
                        wdg.deleteLater()
                uploads_layout.addWidget(add_item)
                _ensure_add_item_rightmost()
                # 更新列表并添加缩略图
                file_paths.clear()
                file_paths.extend(merged)
                if file_paths:
                    file_label.setText(
                        f"已选择 {len(file_paths)} 张，最新：{file_paths[-1]}"
                    )
                else:
                    file_label.setText("未选择图片")
                for p in merged:
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
            # 重新放回加号按钮
            uploads_layout.addWidget(add_item)
            _ensure_add_item_rightmost()

        # 初始化：在预览窗口右侧放置加号用于添加图片
        uploads_layout.addWidget(add_item)
        _ensure_add_item_rightmost()
        # 绑定加号与左侧叉号
        add_btn.clicked.connect(do_choose)
        btn_clear_all.clicked.connect(do_clear)

        # 预览区域（输出图片）：16:9 框（横向自适应窗口宽度，居中摆放），内部保持比例显示
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        # 初始尺寸将由窗口 resize 时动态调整为 16:9
        preview = QLabel("预览区域")
        preview.setScaledContents(False)  # 保持比例缩放，由我们手动设置缩放后的 pixmap
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pf_layout = QVBoxLayout()
        pf_layout.setContentsMargins(0, 0, 0, 0)
        pf_layout.addWidget(preview)
        preview_frame.setLayout(pf_layout)
        # 记录以便 resize 时动态调整
        self._ai_preview_frame = preview_frame
        self._ai_preview_label = preview
        self._ai_thumbs_frame = thumbs_frame
        layout.addWidget(preview_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        def _guess_mime(path: str) -> str:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                return "image/jpeg"
            return "image/png"

        def do_generate():
            p = prompt_input.text().strip()
            s = size_input.text().strip()
            m = model_select.currentText().strip()
            api_key = api_key_input.text().strip()
            org_id = org_id_input.text().strip()
            fp = file_paths[-1] if file_paths else None
            if not p:
                status.setText("提示：请先填写提示词")
                return
            if not fp:
                status.setText("提示：请先选择图片")
                return
            # 模型联动输入校验
            lm = m.lower()
            is_gem = lm.startswith("gemini") or lm.startswith("imagen")
            # 选择数量上限校验（防止误操作超限发起请求）
            limit_chk = _max_images_for_model(m)
            if len(file_paths) > limit_chk:
                status.setText(
                    f"输入错误：当前模型最多允许 {limit_chk} 张图片，请移除多余图片。"
                )
                return
            if is_gem:
                # Gemini：必须提供宽高比；分辨率可选（1K/2K/4K）
                ar = ar_select.currentText().strip()
                res = res_select.currentText().strip()
                if ar not in {
                    "1:1",
                    "2:3",
                    "3:2",
                    "3:4",
                    "4:3",
                    "4:5",
                    "5:4",
                    "9:16",
                    "16:9",
                    "21:9",
                }:
                    status.setText("输入错误：Aspect Ratio 仅支持列表中的选项")
                    return
                if res and res.upper() not in {"1K", "2K", "4K"}:
                    status.setText("输入错误：Resolution 仅支持 1K/2K/4K（大写K）")
                    return
            else:
                # OpenAI：size 可选但如提供必须为支持的尺寸
                if s and s.lower() not in {"256x256", "512x512", "1024x1024"}:
                    status.setText("输入错误：尺寸仅支持 256x256 / 512x512 / 1024x1024")
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
                        files_arg.append(
                            (
                                "images",
                                (fname, f, _guess_mime(pth)),
                            )
                        )
                    data = {"prompt": p}
                    if m:
                        data["model"] = m
                    # 根据模型推断并传递提供者及相关尺寸参数
                    if is_gem:
                        data["provider"] = "gemini"
                        data["aspect_ratio"] = ar_select.currentText().strip()
                        res_val = res_select.currentText().strip()
                        if res_val:
                            data["image_resolution"] = res_val
                    else:
                        data["provider"] = "openai"
                        if s:
                            data["size"] = s
                    # 根据模型推断并传递提供者（openai/gemini）
                    # provider 已在上方按模型设置
                    if api_key:
                        data["api_key"] = api_key
                    if org_id:
                        data["api_org_id"] = org_id
                    resp = _api_post(
                        "/ai-image/edit",
                        files=files_arg,
                        data=data,
                        timeout=30,
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
                                scaled = pix.scaled(
                                    preview_frame.size(),
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation,
                                )
                                preview.setPixmap(scaled)
                            else:
                                preview.setText("预览失败：无法加载图片")
                    else:
                        status.setText(
                            f"生成失败：{payload.get('error_code')} - {payload.get('error')}"
                        )
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
                    scaled = pix.scaled(
                        preview_frame.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    preview.setPixmap(scaled)
                    status.setText(f"已预览：{latest}")
                else:
                    preview.setText("预览失败：无法加载图片")
            except Exception as e:
                status.setText(f"预览异常：{e}")

        btn_generate.clicked.connect(do_generate)
        btn_open_dir.clicked.connect(do_open_dir)
        btn_preview_latest.clicked.connect(do_preview_latest)
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
