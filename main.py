"""赵相机 · 入口：托盘常驻 + 监听剪贴板（Win+Shift+S）+ 内置截图。"""
import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import capture
import config
from floating_window import FloatingWindow
from settings_window import SettingsWindow


def make_icon():
    """加载软件图标 icon.png；找不到时退回绘制的简易图标。"""
    path = config.resource_path("icon.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return QIcon(pm)
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#FF7AB8"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(22, 22, 20, 20)
    p.end()
    return QIcon(pm)


class App:
    def __init__(self, qt_app):
        self.qt_app = qt_app
        qt_app.setQuitOnLastWindowClosed(False)

        config.load()
        self.window = FloatingWindow()
        self.window.setWindowIcon(make_icon())
        self.window.set_callbacks(capture_cb=self.trigger_capture,
                                  settings_cb=self.open_settings)
        self.window.reload_config()

        self._overlay = None
        self._setup_tray()
        self._setup_clipboard()

    # ---------- 托盘 ----------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self.qt_app)
        self.tray.setToolTip("赵相机 · 截图 OCR 翻译")
        menu = QMenu()
        menu.addAction("显示窗口", self.show_window)
        menu.addAction("截图", self.trigger_capture)
        menu.addAction("设置", self.open_settings)
        menu.addSeparator()
        menu.addAction("退出", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    # ---------- 剪贴板监听 ----------
    def _setup_clipboard(self):
        self.clipboard = self.qt_app.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)

    def _on_clipboard_changed(self):
        if capture.self_copying:
            return
        md = self.clipboard.mimeData()
        if md.hasImage():
            img = self.clipboard.image()
            if img is None or img.isNull():
                return
            pixmap = QPixmap.fromImage(img)
            self._present(pixmap)

    # ---------- 内置截图 ----------
    def trigger_capture(self):
        # 截图前先收起悬浮窗，避免遮挡
        self.window.hide()
        QTimer.singleShot(120, self._start_overlay)

    def _start_overlay(self):
        self._overlay = capture.CaptureOverlay(self._on_captured)
        self._overlay.start()

    def _on_captured(self, pixmap):
        self._present(pixmap)

    # ---------- 展示 ----------
    def _present(self, pixmap):
        self.window.set_screenshot(pixmap)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def open_settings(self):
        dlg = SettingsWindow(self.window)
        if dlg.exec_():
            self.window.reload_config()

    def maybe_first_run(self):
        """首次运行弹出配置引导。"""
        if config.get("first_run_done", False):
            return
        from setup_wizard import SetupWizard
        dlg = SetupWizard(self.window)
        if dlg.exec_():
            self.window.reload_config()
        else:
            config.set("first_run_done", True, save_now=True)

    def quit(self):
        self.window.shutdown()
        self.tray.hide()
        self.qt_app.quit()


def main():
    # 自检模式：不启动界面，检查各组件并写报告
    if "--selftest" in sys.argv:
        import selftest
        selftest.run()
        return

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("赵相机")
    app = App(qt_app)
    app.maybe_first_run()
    # 首次启动显示主窗口
    app.window.show()
    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    main()
