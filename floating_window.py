"""悬浮窗：显示截图 + 识别文字 + 翻译，支持置顶/透明/配色/复制/可编辑。"""
import os
import time

from PyQt5.QtCore import QPoint, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMenu, QPushButton, QSizeGrip, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)

import capture
import external_open
from image_viewer import ImageViewer
import config
import ocr
import themes
import translator
from workers import Worker


class _PreviewLabel(QLabel):
    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class FloatingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(380, 420)
        self.resize(500, 640)

        self._pixmap = None
        self._custom_bg = None
        self._drag_offset = QPoint()
        self._dragging = False
        self._title_height = 0
        self._ocr_worker = None
        self._trans_worker = None
        self._viewer = None
        self._capture_callback = None
        self._settings_callback = None

        self._build_ui()
        self.reload_config()

    # ---------- UI 构建 ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(8)

        # 标题栏
        self.title_bar = QWidget()
        tb = QHBoxLayout(self.title_bar)
        tb.setContentsMargins(6, 2, 2, 2)
        tb.setSpacing(6)

        self.btn_capture = QPushButton("截图")
        self.btn_capture.setObjectName("icon")
        self.btn_capture.setToolTip("框选截图（内置）")
        self.btn_capture.clicked.connect(self.request_capture)

        self.btn_pin = QPushButton("置顶")
        self.btn_pin.setObjectName("icon")
        self.btn_pin.setToolTip("保持窗口置顶")
        self.btn_pin.setCheckable(True)
        self.btn_pin.clicked.connect(self.toggle_pin)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setObjectName("icon")
        self.btn_settings.setToolTip("打开设置")
        self.btn_settings.clicked.connect(self.request_settings)

        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("icon")
        self.btn_close.setToolTip("隐藏窗口（仍在托盘运行）")
        self.btn_close.clicked.connect(self.hide)

        tb.addStretch(1)
        tb.addWidget(self.btn_capture)
        tb.addWidget(self.btn_pin)
        tb.addWidget(self.btn_settings)
        tb.addWidget(self.btn_close)
        root.addWidget(self.title_bar)

        # 截图预览（双击打开 Windows 截图工具）
        self.preview = _PreviewLabel()
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(140)
        self.preview.setToolTip("双击用「截图工具」打开编辑；右键更多")
        self.preview.doubleClicked.connect(self.open_in_snipping_tool)
        self.preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self._on_preview_menu)
        self.preview.hide()
        root.addWidget(self.preview)

        # 识别文字区 header
        row1 = QHBoxLayout()
        self.lbl_ocr = QLabel("识别文字")
        self.lbl_ocr.setObjectName("section")
        self.btn_copy_ocr = QPushButton("复制")
        self.btn_copy_ocr.setObjectName("icon")
        self.btn_copy_ocr.clicked.connect(self.copy_ocr)
        row1.addWidget(self.lbl_ocr)
        row1.addStretch(1)
        row1.addWidget(self.btn_copy_ocr)
        root.addLayout(row1)

        # 分割器：识别文字框 / 译文区（可拖动调整大小）
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("截图后自动识别……（可手动编辑）")
        self.ocr_text.setMinimumHeight(80)
        self.splitter.addWidget(self.ocr_text)

        # 译文面板
        trans_panel = QWidget()
        tpl = QVBoxLayout(trans_panel)
        tpl.setContentsMargins(0, 0, 0, 0)
        tpl.setSpacing(8)

        self.btn_translate = QPushButton("翻 译")
        self.btn_translate.setObjectName("accent")
        self.btn_translate.clicked.connect(self.start_translate)
        tpl.addWidget(self.btn_translate)

        row2 = QHBoxLayout()
        self.lbl_trans = QLabel("译文")
        self.lbl_trans.setObjectName("section")
        self.btn_copy_trans = QPushButton("复制")
        self.btn_copy_trans.setObjectName("icon")
        self.btn_copy_trans.clicked.connect(self.copy_translation)
        row2.addWidget(self.lbl_trans)
        row2.addStretch(1)
        row2.addWidget(self.btn_copy_trans)
        tpl.addLayout(row2)

        self.trans_text = QTextEdit()
        self.trans_text.setPlaceholderText("点击上方「翻译」按钮……（可手动编辑）")
        self.trans_text.setMinimumHeight(80)
        tpl.addWidget(self.trans_text)

        self.splitter.addWidget(trans_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 5)
        root.addWidget(self.splitter, 1)

        # 状态栏 + 右下角缩放手柄
        bottom = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("status")
        bottom.addWidget(self.lbl_status)
        bottom.addStretch(1)
        self.grip = QSizeGrip(self)
        bottom.addWidget(self.grip, 0, Qt.AlignBottom | Qt.AlignRight)
        root.addLayout(bottom)

        # 复制按钮的「复制成功」提示（2 秒后复原）
        self._timer_copy_ocr = QTimer(self)
        self._timer_copy_ocr.setSingleShot(True)
        self._timer_copy_ocr.timeout.connect(lambda: self.btn_copy_ocr.setText("复制"))
        self._timer_copy_trans = QTimer(self)
        self._timer_copy_trans.setSingleShot(True)
        self._timer_copy_trans.timeout.connect(lambda: self.btn_copy_trans.setText("复制"))

        self._title_height = 34

    # ---------- 配置与主题 ----------
    def reload_config(self):
        cfg = config.get_all()
        self.theme_key = cfg.get("theme", "blue_pink")
        self.opacity = max(0, min(100, int(cfg.get("opacity", 15))))

        always_top = bool(cfg.get("always_on_top", True))
        self._apply_always_on_top(always_top)
        self.btn_pin.setChecked(always_top)

        self._load_custom_bg(cfg.get("custom_bg_path", ""))
        self.preview.setVisible(bool(cfg.get("show_preview", True)) and self._pixmap is not None)
        self._apply_theme()
        self.update()

    def _load_custom_bg(self, path):
        self._custom_bg = None
        if path and self.theme_key == "custom":
            pm = QPixmap(path)
            if not pm.isNull():
                self._custom_bg = pm

    def _apply_always_on_top(self, on):
        was_visible = self.isVisible()
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)  # 副作用：会隐藏窗口
        if was_visible:
            self.show()

    def _apply_theme(self):
        t = themes.get_theme(self.theme_key)
        cfg = config.get_all()
        # 字体颜色：用户设置优先，否则用主题自带
        text = cfg.get("font_color") or t["text"]
        try:
            fsize = int(cfg.get("font_size", 13) or 13)
        except (TypeError, ValueError):
            fsize = 13
        fsize = max(9, min(40, fsize))
        label_size = max(9, fsize - 1)
        status_size = max(8, fsize - 2)

        qss = """
        QLabel#section { color: %(text)s; font-size: %(label_size)dpx; }
        QLabel#status { color: %(text)s; font-size: %(status_size)dpx; }
        QLabel#preview { background-color: rgba(0,0,0,60); border-radius: 8px; }
        QTextEdit {
            background-color: %(panel)s; color: %(text)s;
            border: 1px solid %(border)s; border-radius: 8px;
            padding: 6px; font-size: %(font_size)dpx;
        }
        QPushButton#accent {
            background-color: %(accent)s; color: %(accent_text)s;
            border: none; border-radius: 6px; padding: 7px 14px;
            font-weight: 600; font-size: %(label_size)dpx;
        }
        QPushButton#accent:hover { opacity: 0.9; }
        QPushButton#accent:disabled { background-color: rgba(128,128,128,120); color: rgba(255,255,255,180); }
        QPushButton#icon {
            background: transparent; color: %(text)s; border: none;
            border-radius: 4px; padding: 4px 8px; font-size: %(label_size)dpx;
        }
        QPushButton#icon:hover { background-color: rgba(128,128,128,60); }
        QPushButton#icon:checked { background-color: %(accent)s; color: %(accent_text)s; }
        QSplitter::handle { background: transparent; height: 6px; }
        """ % {
            "text": text, "panel": t["panel"], "border": t["border"],
            "accent": t["accent"], "accent_text": t["accent_text"],
            "font_size": fsize, "label_size": label_size, "status_size": status_size,
        }
        self.setStyleSheet(qss)

    # ---------- 背景绘制（透明背景 + 不透明文字） ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = 14
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        p.setClipPath(path)

        t = themes.get_theme(self.theme_key)
        if self.theme_key == "custom" and self._custom_bg is not None:
            pm = self._custom_bg.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - pm.width()) // 2
            y = (self.height() - pm.height()) // 2
            p.drawPixmap(x, y, pm)
            # 透明度越大（100）遮罩越浅、图片越清晰
            overlay = max(40, int((100 - self.opacity) * 1.6))
            p.fillRect(rect, QColor(0, 0, 0, overlay))
        else:
            # 透明度越大背景越透明（100 全透明，0 全不透明）
            alpha = int(t["bg_alpha"] * (100 - self.opacity) / 100)
            col = QColor(t["bg"][0], t["bg"][1], t["bg"][2], alpha)
            p.setBrush(col)
            pen = QPen(QColor(t["border"]))
            pen.setWidth(1)
            p.setPen(pen)
            p.drawRoundedRect(rect, radius, radius)

    # ---------- 拖拽移动 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= self._title_height:
            self._dragging = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    # ---------- 截图/OCR 流程 ----------
    def _is_same_pixmap(self, pixmap):
        """两张图是否完全相同（按像素比较，不受重新编码影响）。"""
        if self._pixmap is None or pixmap is None:
            return False
        a = pixmap.toImage().convertToFormat(QImage.Format_RGB32)
        b = self._pixmap.toImage().convertToFormat(QImage.Format_RGB32)
        if a.size() != b.size():
            return False
        try:
            n = a.byteCount()
            return a.bits().asstring(n) == b.bits().asstring(n)
        except Exception:
            return False

    def set_screenshot(self, pixmap):
        """收到一张截图（QPixmap），显示并启动 OCR。

        若与当前图完全相同则直接返回 —— 否则「用截图工具打开」时，
        截图工具会把同一张图放回剪贴板，被剪贴板监听当成新截图，
        导致识别文字和译文被清空。
        """
        if pixmap is None or pixmap.isNull():
            return
        if self._is_same_pixmap(pixmap):
            return
        self._pixmap = pixmap
        self._update_preview()
        self.ocr_text.clear()
        self.trans_text.clear()
        self.lbl_status.setText("识别中…")
        self.btn_translate.setEnabled(False)

        pil = capture.qpixmap_to_pil(pixmap)
        self._ocr_worker = Worker(ocr.ocr_pil_image, pil)
        self._ocr_worker.result.connect(self._on_ocr_done)
        self._ocr_worker.error.connect(self._on_ocr_error)
        self._ocr_worker.start()

    def _on_ocr_done(self, text):
        self.ocr_text.setPlainText(text or "")
        self.lbl_status.setText("识别完成" if text else "未识别到文字")
        self.btn_translate.setEnabled(bool(text and text.strip()))

    def _on_ocr_error(self, msg):
        self.lbl_status.setText("识别失败：%s" % msg)
        self.btn_translate.setEnabled(False)

    def _update_preview(self):
        if self._pixmap is None:
            self.preview.hide()
            return
        if not config.get("show_preview", True):
            self.preview.hide()
            return
        self.preview.show()
        scaled = self._pixmap.scaled(
            self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(scaled)

    # ---------- 翻译流程 ----------
    def start_translate(self):
        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.lbl_status.setText("没有可翻译的文字")
            return
        self.btn_translate.setEnabled(False)
        self.btn_translate.setText("翻译中…")
        self.lbl_status.setText("翻译中…")
        self._trans_worker = Worker(translator.translate, text)
        self._trans_worker.result.connect(self._on_trans_done)
        self._trans_worker.error.connect(self._on_trans_error)
        self._trans_worker.start()

    def _on_trans_done(self, text):
        self.trans_text.setPlainText(text or "")
        self.lbl_status.setText("翻译完成")
        self.btn_translate.setText("翻 译")
        self.btn_translate.setEnabled(True)

    def _on_trans_error(self, msg):
        self.lbl_status.setText("翻译失败：%s" % msg)
        self.btn_translate.setText("翻 译")
        self.btn_translate.setEnabled(True)

    # ---------- 复制 ----------
    def _copy_text(self, text):
        if not text:
            return
        capture.self_copying = True
        QApplication.clipboard().setText(text)
        QTimer.singleShot(200, lambda: setattr(capture, "self_copying", False))

    def copy_ocr(self):
        self._copy_text(self.ocr_text.toPlainText())
        self.btn_copy_ocr.setText("复制成功")
        self._timer_copy_ocr.start(2000)

    def copy_translation(self):
        self._copy_text(self.trans_text.toPlainText())
        self.btn_copy_trans.setText("复制成功")
        self._timer_copy_trans.start(2000)

    # ---------- 行为 ----------
    def toggle_pin(self, checked=None):
        if checked is None:
            checked = self.btn_pin.isChecked()
        self._apply_always_on_top(checked)
        config.set("always_on_top", checked, save_now=True)
        self.btn_pin.setChecked(checked)

    def _save_current_pixmap(self):
        """把当前截图存成 PNG，返回路径（截图工具需要一个真实文件）。"""
        folder = os.path.join(os.path.expanduser("~"), "Pictures", "ZhaoCamera")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, time.strftime("snip_%Y%m%d_%H%M%S.png"))
        self._pixmap.save(path, "PNG")
        return path

    def open_in_snipping_tool(self):
        """双击预览：把图片交给 Windows 截图工具打开（可裁剪/标注/保存）。"""
        if self._pixmap is None:
            return
        try:
            path = self._save_current_pixmap()
        except Exception as exc:
            self.lbl_status.setText("保存图片失败：%s" % exc)
            return
        # 截图工具打开后会把图放回剪贴板，短时间内忽略剪贴板变化，避免误清空结果
        capture.self_copying = True
        QTimer.singleShot(2500, lambda: setattr(capture, "self_copying", False))
        if external_open.open_in_snipping_tool(path):
            self.lbl_status.setText("已用截图工具打开：%s" % os.path.basename(path))
        else:
            external_open.open_with_default_app(path)
            self.lbl_status.setText("已用默认程序打开：%s" % os.path.basename(path))

    def show_builtin_viewer(self):
        """用内置查看器看大图（滚轮缩放）。复用同一个窗口。"""
        if self._pixmap is None:
            return
        if self._viewer is not None:
            try:
                self._viewer.set_pixmap(self._pixmap)
                self._viewer.show()
                self._viewer.raise_()
                self._viewer.activateWindow()
                return
            except RuntimeError:
                # 底层 C++ 对象已被销毁
                self._viewer = None
        self._viewer = ImageViewer(self._pixmap, self)
        self._viewer.show()

    def _on_preview_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("用「截图工具」编辑", self.open_in_snipping_tool)
        menu.addAction("内置查看器看大图", self.show_builtin_viewer)
        menu.exec_(self.preview.mapToGlobal(pos))

    def request_capture(self):
        if self._capture_callback:
            self._capture_callback()

    def request_settings(self):
        if self._settings_callback:
            self._settings_callback()

    def set_callbacks(self, capture_cb=None, settings_cb=None):
        """由 main.py 注入「截图」「设置」的外部入口（不直接改私有属性）。"""
        if capture_cb is not None:
            self._capture_callback = capture_cb
        if settings_cb is not None:
            self._settings_callback = settings_cb

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()

    def shutdown(self):
        """退出前等待后台线程结束，避免 QThread 被销毁时报错。"""
        for w in (self._ocr_worker, self._trans_worker):
            if w is not None and w.isRunning():
                w.wait(3000)
