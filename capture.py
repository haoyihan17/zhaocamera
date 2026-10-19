"""截图与剪贴板：内置框选截图 + QImage/QPixmap 转 PIL。"""
import io

from PIL import Image
from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget

# 剪贴板写入守卫：App 自己写剪贴板（复制文字）时不触发截图监听
self_copying = False


def qimage_to_pil(qimage):
    """QImage -> PIL Image（RGB）。经 PNG 无损中转，规避内存对齐问题。"""
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    qimage.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(bytes(ba))).convert("RGB")


def qpixmap_to_pil(pixmap):
    """QPixmap -> PIL Image（RGB）。"""
    return qimage_to_pil(pixmap.toImage())


def qpixmap_to_qimage(pixmap):
    return pixmap.toImage()


class CaptureOverlay(QWidget):
    """全屏框选截图遮罩：按住左键拖选，松开回传选区 QPixmap。"""

    def __init__(self, on_captured):
        super().__init__()
        self._on_captured = on_captured
        self._screenshot = None
        self._origin = QPoint()
        self._rect = QRect()
        self._dragging = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

    def start(self):
        screen = QApplication.primaryScreen()
        self._screenshot = screen.grabWindow(0)
        self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def _device_rect(self):
        # grabWindow 返回的是设备像素，需按 DPR 换算选区
        dpr = self._screenshot.devicePixelRatio() or 1.0
        return QRect(
            int(self._rect.x() * dpr),
            int(self._rect.y() * dpr),
            int(self._rect.width() * dpr),
            int(self._rect.height() * dpr),
        )

    def paintEvent(self, event):
        if self._screenshot is None:
            return
        p = QPainter(self)
        # 1) 全屏铺满截图（缩放到窗口逻辑尺寸）
        p.drawPixmap(self.rect(), self._screenshot)
        # 2) 盖一层半透明暗色
        p.fillRect(self.rect(), QColor(0, 0, 0, 100))
        # 3) 选区恢复原图亮度 + 描边
        if not self._rect.isNull():
            p.drawPixmap(self._rect, self._screenshot, self._device_rect())
            p.setPen(QPen(QColor(0, 140, 255), 2))
            p.drawRect(self._rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._rect = QRect(self._origin, self._origin)
            self._dragging = True
        elif event.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._rect = QRect(self._origin, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            result = None
            if self._rect.width() > 5 and self._rect.height() > 5:
                result = self._screenshot.copy(self._device_rect())
            self.close()
            if result is not None:
                self._on_captured(result)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
