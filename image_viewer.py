"""图片查看器：双击图片框后，全尺寸查看截图（滚轮缩放、可滚动）。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout


class ImageViewer(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查看图片")
        self._pixmap = pixmap
        self._scale = 1.0
        self._build_ui()

    def _build_ui(self):
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea { background: #2b2b2b; border: none; }")

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("QLabel { background: #2b2b2b; }")
        self.scroll.setWidget(self.label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)

        # 初始窗口大小：尽量展示原图，但不超屏幕 90%
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is None:
            self.resize(min(self._pixmap.width() + 30, 1400),
                        min(self._pixmap.height() + 30, 900))
        else:
            w = min(self._pixmap.width() + 30, int(screen.width() * 0.9))
            h = min(self._pixmap.height() + 30, int(screen.height() * 0.9))
            self.resize(w, h)

        self._update_pixmap()

    def set_pixmap(self, pixmap):
        """换一张图（复用同一个窗口，避免反复创建）。"""
        self._pixmap = pixmap
        self._scale = 1.0
        self._update_pixmap()

    def _update_pixmap(self):
        if self._pixmap is None or self._pixmap.isNull():
            return
        w = max(1, int(self._pixmap.width() * self._scale))
        h = max(1, int(self._pixmap.height() * self._scale))
        pm = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(pm)
        self.label.resize(pm.size())

    def wheelEvent(self, event):
        """滚轮缩放。"""
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.2 if delta > 0 else 1 / 1.2
        self._scale = max(0.05, min(12.0, self._scale * factor))
        self._update_pixmap()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape,):
            self.close()
        elif event.key() == Qt.Key_0:
            self._scale = 1.0
            self._update_pixmap()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.close()
