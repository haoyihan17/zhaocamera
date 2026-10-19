"""配色主题定义。背景可透明，文字始终不透明。"""

THEMES = {
    "blue_pink": {
        "name": "蓝粉（默认）",
        "bg": (26, 32, 68),          # 背景基础 RGB
        "bg_alpha": 225,             # 背景基础不透明度 0-255
        "panel": "rgba(255,255,255,18)",
        "text": "#2FC2D4",
        "subtext": "#C7CBE8",
        "accent": "#FF7AB8",
        "accent_text": "#FFFFFF",
        "border": "rgba(255,122,184,170)",
    },
    "glass": {
        "name": "iPhone 透明玻璃",
        "bg": (255, 255, 255),
        "bg_alpha": 96,
        "panel": "rgba(255,255,255,130)",
        "text": "#1A1A1A",
        "subtext": "#555555",
        "accent": "#007AFF",
        "accent_text": "#FFFFFF",
        "border": "rgba(255,255,255,220)",
    },
    "light": {
        "name": "浅色",
        "bg": (245, 247, 250),
        "bg_alpha": 240,
        "panel": "rgba(255,255,255,210)",
        "text": "#1A1A1A",
        "subtext": "#666666",
        "accent": "#5B8DEF",
        "accent_text": "#FFFFFF",
        "border": "rgba(180,190,210,190)",
    },
    "custom": {
        "name": "自定义图片",
        "bg": (0, 0, 0),
        "bg_alpha": 210,
        "panel": "rgba(0,0,0,95)",
        "text": "#FFFFFF",
        "subtext": "#DDDDDD",
        "accent": "#FF7AB8",
        "accent_text": "#FFFFFF",
        "border": "rgba(255,255,255,140)",
    },
}

DEFAULT_THEME = "blue_pink"


def get_theme(key):
    return THEMES.get(key, THEMES[DEFAULT_THEME])
