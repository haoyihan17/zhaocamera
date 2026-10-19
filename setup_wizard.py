"""首次运行配置引导：让对方自己选翻译方式并填 Key。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout,
)

import config
import offline_translate
import translator


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("赵相机 · 首次使用设置")
        self.setMinimumWidth(560)
        self._build_ui()
        self._load()

    # ---------- UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        title = QLabel("欢迎使用 赵相机")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        intro = QLabel(
            "截图和文字识别已经内置，**完全离线可用**，不需要装任何东西。\n"
            "只有「翻译」需要选一种方式，下面挑一个就行（以后可在「设置」里改）。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #444; font-size: 12px; padding: 6px;")
        layout.addWidget(self.lbl_status)

        form = QFormLayout()
        self.cmb_backend = QComboBox()
        self.cmb_backend.addItem("自动：本地 AI → 云端 API → 内置离线模型（推荐）", "auto")
        self.cmb_backend.addItem("本地 AI（LM Studio）", "local")
        self.cmb_backend.addItem("云端 API（填自己的 Key）", "cloud")
        self.cmb_backend.addItem("内置离线模型（完全不用联网）", "offline")
        form.addRow("翻译方式", self.cmb_backend)

        self.edit_cloud_url = QLineEdit()
        self.edit_cloud_url.setPlaceholderText("https://api.deepseek.com/v1")
        form.addRow("云端 API 地址", self.edit_cloud_url)

        self.edit_cloud_key = QLineEdit()
        self.edit_cloud_key.setEchoMode(QLineEdit.Password)
        self.edit_cloud_key.setPlaceholderText("没有本地 AI 时填这里，例如 sk-...")
        form.addRow("云端 API Key", self.edit_cloud_key)

        self.edit_cloud_model = QLineEdit()
        self.edit_cloud_model.setPlaceholderText("deepseek-chat")
        form.addRow("云端模型名", self.edit_cloud_model)
        layout.addLayout(form)

        hint = QLabel("提示：云端 Key 只保存在你自己电脑的 config.json 里，不会外传。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_ok = QPushButton("开始使用")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._save)
        self.btn_skip = QPushButton("跳过")
        self.btn_skip.clicked.connect(self.reject)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_skip)
        layout.addLayout(btns)

    # ---------- 逻辑 ----------
    def _load(self):
        cfg = config.get_all()

        local_ok, local_detail = translator.local_status()
        offline_ok = offline_translate.is_available()

        lines = []
        lines.append("本机检测：")
        lines.append("  · 本地 AI（LM Studio）：%s   [%s]" % (
            "已就绪 ✓" if local_ok else "未检测到 ✗", local_detail))
        lines.append("  · 内置离线模型：%s" % ("已安装 ✓" if offline_ok else "未安装（可跳过）✗"))
        lines.append("  · 文字识别：已内置，随时可用 ✓")
        self.lbl_status.setText("\n".join(lines))

        self.edit_cloud_url.setText(cfg.get("cloud_base_url", ""))
        self.edit_cloud_key.setText(cfg.get("cloud_api_key", ""))
        self.edit_cloud_model.setText(cfg.get("cloud_model", ""))

        # 三种兜底方式只要有一种可用就选「自动」，全都没有才被迫选云端
        any_available = bool(local_ok or cfg.get("cloud_api_key") or offline_ok)
        default = "auto" if any_available else "cloud"
        idx = self.cmb_backend.findData(default)
        if idx >= 0:
            self.cmb_backend.setCurrentIndex(idx)

    def _save(self):
        cfg = config.get_all()
        cfg["translate_backend"] = self.cmb_backend.currentData()
        cfg["cloud_base_url"] = self.edit_cloud_url.text().strip()
        cfg["cloud_api_key"] = self.edit_cloud_key.text().strip()
        cfg["cloud_model"] = self.edit_cloud_model.text().strip()
        cfg["first_run_done"] = True
        config.save(cfg)
        self.accept()
