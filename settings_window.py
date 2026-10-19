"""设置窗口：窗口 / 外观（配色·字体）/ OCR / 翻译。"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

import autostart
import config
import offline_translate
import themes


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("赵相机 · 设置")
        self.resize(480, 720)
        self._bg_path = ""
        self._font_color = ""
        self._build_ui()
        self._load()

    # ---------- 构建 ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(14, 12, 14, 8)
        layout.setSpacing(10)

        # ---- 窗口 ----
        box_win = QGroupBox("窗口")
        f1 = QFormLayout(box_win)
        self.chk_top = QCheckBox("保持窗口置顶")
        f1.addRow("置顶", self.chk_top)
        self.chk_autostart = QCheckBox("开机自动启动")
        f1.addRow("开机自启", self.chk_autostart)

        self.sld_opacity = QSlider(Qt.Horizontal)
        self.sld_opacity.setRange(0, 100)
        self.lbl_opacity = QLabel()
        op = QHBoxLayout()
        op.addWidget(self.sld_opacity, 1)
        op.addWidget(self.lbl_opacity)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity.setText(str(v)))
        f1.addRow("背景透明度（越大越透明）", op)

        self.chk_preview = QCheckBox("显示截图缩略图")
        f1.addRow("预览", self.chk_preview)
        layout.addWidget(box_win)

        # ---- 外观：配色 ----
        box_theme = QGroupBox("配色")
        f2 = QFormLayout(box_theme)
        self.cmb_theme = QComboBox()
        for key, t in themes.THEMES.items():
            self.cmb_theme.addItem(t["name"], key)
        f2.addRow("主题配色", self.cmb_theme)

        bg = QHBoxLayout()
        self.lbl_bg = QLabel("未选择")
        self.lbl_bg.setWordWrap(True)
        self.btn_bg = QPushButton("选择图片…")
        self.btn_bg.clicked.connect(self._pick_bg)
        self.btn_clear = QPushButton("清除")
        self.btn_clear.clicked.connect(self._clear_bg)
        bg.addWidget(self.lbl_bg, 1)
        bg.addWidget(self.btn_bg)
        bg.addWidget(self.btn_clear)
        f2.addRow("自定义背景", bg)
        layout.addWidget(box_theme)

        # ---- 外观：字体 ----
        box_font = QGroupBox("字体")
        f3 = QFormLayout(box_font)
        fc = QHBoxLayout()
        self.btn_font_color = QPushButton()
        self.btn_font_color.setFixedWidth(100)
        self.btn_font_color.clicked.connect(self._pick_font_color)
        self.btn_font_reset = QPushButton("用主题色")
        self.btn_font_reset.clicked.connect(self._reset_font_color)
        fc.addWidget(self.btn_font_color)
        fc.addWidget(self.btn_font_reset)
        fc.addStretch(1)
        f3.addRow("字体颜色", fc)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(9, 40)
        self.spin_font_size.setSuffix(" px")
        f3.addRow("字体大小", self.spin_font_size)
        layout.addWidget(box_font)

        # ---- OCR ----
        box_ocr = QGroupBox("识别（OCR）")
        f4 = QFormLayout(box_ocr)
        self.cmb_ocr = QComboBox()
        self.cmb_ocr.addItem("RapidOCR（深度学习，推荐）", "rapidocr")
        self.cmb_ocr.addItem("Windows 自带 OCR（轻量）", "windows")
        f4.addRow("OCR 引擎", self.cmb_ocr)
        layout.addWidget(box_ocr)

        # ---- 翻译 ----
        box_tr = QGroupBox("翻译")
        f5 = QFormLayout(box_tr)

        self.cmb_dir = QComboBox()
        self.cmb_dir.addItem("自动检测", "auto")
        self.cmb_dir.addItem("中文 → 英文", "zh2en")
        self.cmb_dir.addItem("英文 → 中文", "en2zh")
        f5.addRow("翻译方向", self.cmb_dir)

        self.cmb_backend = QComboBox()
        self.cmb_backend.addItem("自动（本地 → 云端 → 离线）", "auto")
        self.cmb_backend.addItem("只用本地 LM Studio", "local")
        self.cmb_backend.addItem("只用云端 API", "cloud")
        self.cmb_backend.addItem("只用内置离线模型", "offline")
        f5.addRow("翻译后端", self.cmb_backend)

        self.lbl_offline = QLabel()
        self.lbl_offline.setWordWrap(True)
        f5.addRow("离线模型", self.lbl_offline)
        self._refresh_offline_label()

        self.edit_url = QLineEdit()
        f5.addRow("本地 · LM Studio 地址", self.edit_url)
        self.edit_token = QLineEdit()
        self.edit_token.setEchoMode(QLineEdit.Password)
        f5.addRow("本地 · API Token", self.edit_token)
        self.edit_model = QLineEdit()
        f5.addRow("本地 · 模型", self.edit_model)

        self.edit_cloud_url = QLineEdit()
        self.edit_cloud_url.setPlaceholderText("https://api.deepseek.com/v1")
        f5.addRow("云端 · API 地址", self.edit_cloud_url)
        self.edit_cloud_key = QLineEdit()
        self.edit_cloud_key.setEchoMode(QLineEdit.Password)
        f5.addRow("云端 · API Key", self.edit_cloud_key)
        self.edit_cloud_model = QLineEdit()
        self.edit_cloud_model.setPlaceholderText("deepseek-chat")
        f5.addRow("云端 · 模型", self.edit_cloud_model)

        hint = QLabel("没有本地 AI 时：填好「云端」三项并把翻译后端设为自动或云端即可。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        f5.addRow("", hint)
        layout.addWidget(box_tr)

        layout.addStretch(1)

        btns = QHBoxLayout()
        btns.setContentsMargins(14, 4, 14, 12)
        btns.addStretch(1)
        self.btn_ok = QPushButton("保存")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._save)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        outer.addLayout(btns)

    # ---------- 装载 ----------
    def _load(self):
        cfg = config.get_all()
        self.chk_top.setChecked(bool(cfg.get("always_on_top", True)))
        self.chk_autostart.setChecked(autostart.is_enabled())
        self.sld_opacity.setValue(int(cfg.get("opacity", 15)))
        self.lbl_opacity.setText(str(self.sld_opacity.value()))
        self.chk_preview.setChecked(bool(cfg.get("show_preview", True)))

        idx = self.cmb_theme.findData(cfg.get("theme", "blue_pink"))
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)
        self._bg_path = cfg.get("custom_bg_path", "")
        self.lbl_bg.setText(self._bg_path or "未选择")

        self._font_color = cfg.get("font_color", "") or ""
        self._update_font_color_button()
        self.spin_font_size.setValue(int(cfg.get("font_size", 13) or 13))

        idx_ocr = self.cmb_ocr.findData(cfg.get("ocr_engine", "rapidocr"))
        if idx_ocr >= 0:
            self.cmb_ocr.setCurrentIndex(idx_ocr)

        idx_dir = self.cmb_dir.findData(cfg.get("translate_direction", "auto"))
        if idx_dir >= 0:
            self.cmb_dir.setCurrentIndex(idx_dir)
        idx_be = self.cmb_backend.findData(cfg.get("translate_backend", "auto"))
        if idx_be >= 0:
            self.cmb_backend.setCurrentIndex(idx_be)

        self.edit_url.setText(cfg.get("lmstudio_url", ""))
        self.edit_token.setText(cfg.get("api_token", ""))
        self.edit_model.setText(cfg.get("model", ""))
        self.edit_cloud_url.setText(cfg.get("cloud_base_url", ""))
        self.edit_cloud_key.setText(cfg.get("cloud_api_key", ""))
        self.edit_cloud_model.setText(cfg.get("cloud_model", ""))

    # ---------- 交互 ----------
    def _pick_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._bg_path = path
            self.lbl_bg.setText(path)

    def _clear_bg(self):
        self._bg_path = ""
        self.lbl_bg.setText("未选择")

    def _refresh_offline_label(self):
        if offline_translate.is_available():
            self.lbl_offline.setText("已安装 ✓（%s）" % (offline_translate.models_root() or ""))
            self.lbl_offline.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            self.lbl_offline.setText("未安装 —— 把 offline_models 文件夹放到程序目录即可启用")
            self.lbl_offline.setStyleSheet("color: #c62828; font-size: 11px;")

    def _update_font_color_button(self):
        if self._font_color:
            self.btn_font_color.setText(self._font_color)
            self.btn_font_color.setStyleSheet(
                "background-color: %s; color: %s; border: 1px solid #888; border-radius: 4px;"
                % (self._font_color, self._contrast_text(self._font_color)))
        else:
            self.btn_font_color.setText("主题色")
            self.btn_font_color.setStyleSheet("")

    @staticmethod
    def _contrast_text(hex_color):
        c = QColor(hex_color)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return "#000000" if lum > 140 else "#FFFFFF"

    def _pick_font_color(self):
        initial = QColor(self._font_color) if self._font_color else QColor("#2FC2D4")
        color = QColorDialog.getColor(initial, self, "选择字体颜色")
        if color.isValid():
            self._font_color = color.name()
            self._update_font_color_button()

    def _reset_font_color(self):
        self._font_color = ""
        self._update_font_color_button()

    # ---------- 保存 ----------
    def _save(self):
        cfg = config.get_all()
        cfg["always_on_top"] = self.chk_top.isChecked()
        cfg["opacity"] = self.sld_opacity.value()
        cfg["show_preview"] = self.chk_preview.isChecked()
        cfg["theme"] = self.cmb_theme.currentData()
        cfg["custom_bg_path"] = self._bg_path
        cfg["font_color"] = self._font_color
        cfg["font_size"] = self.spin_font_size.value()
        cfg["ocr_engine"] = self.cmb_ocr.currentData()
        cfg["translate_direction"] = self.cmb_dir.currentData()
        cfg["translate_backend"] = self.cmb_backend.currentData()
        cfg["lmstudio_url"] = self.edit_url.text().strip()
        cfg["api_token"] = self.edit_token.text().strip()
        cfg["model"] = self.edit_model.text().strip()
        cfg["cloud_base_url"] = self.edit_cloud_url.text().strip()
        cfg["cloud_api_key"] = self.edit_cloud_key.text().strip()
        cfg["cloud_model"] = self.edit_cloud_model.text().strip()

        cfg["autostart"] = self.chk_autostart.isChecked()
        if self.chk_autostart.isChecked():
            autostart.enable()
        else:
            autostart.disable()

        config.save(cfg)
        self.accept()
