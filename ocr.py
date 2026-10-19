"""OCR 模块：RapidOCR（深度学习，默认）或 Windows 内置 OCR（轻量，可切换）。"""
import os
import re
import subprocess
import tempfile

import config

_CJK = r"\u2e80-\u9fff\u3000-\u303f\uff00-\uffef"

_rapid_engine = None

# 打包成 exe 后 ocr_ps.ps1 被解包到 sys._MEIPASS
PS_SCRIPT = config.resource_path("ocr_ps.ps1")


def _clean_windows(text):
    """Windows OCR 会在中文间插空格，去掉；保留英文单词间空格。"""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"(?<=[%s])\s+(?=[%s])" % (_CJK, _CJK), "", text)
    return text


def _run_powershell(image_path):
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", PS_SCRIPT, image_path]
    proc = subprocess.run(cmd, capture_output=True, timeout=60)
    out = proc.stdout or b""
    text = None
    for enc in ("utf-8", "gbk"):
        try:
            text = out.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = out.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError("OCR 失败：" + (err.strip() or text.strip()))
    return text


def _save_temp(pil_image):
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = tmp.name
    tmp.close()
    pil_image.convert("RGB").save(tmp_path, "PNG")
    return tmp_path


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _ocr_windows(pil_image):
    if pil_image is None:
        return ""
    tmp_path = _save_temp(pil_image)
    try:
        return _clean_windows(_run_powershell(tmp_path))
    finally:
        _rm(tmp_path)


def _get_rapid():
    global _rapid_engine
    if _rapid_engine is None:
        from rapidocr import RapidOCR
        _rapid_engine = RapidOCR()
    return _rapid_engine


def _ocr_rapid(pil_image):
    if pil_image is None:
        return ""
    tmp_path = _save_temp(pil_image)
    try:
        engine = _get_rapid()
        result = engine(tmp_path)          # RapidOCROutput
        txts = getattr(result, "txts", None) or ()
        return "\n".join(str(t) for t in txts).strip()
    finally:
        _rm(tmp_path)


def ocr_pil_image(pil_image):
    """按配置选择 OCR 引擎；RapidOCR 失败时自动回退 Windows OCR。"""
    if pil_image is None:
        return ""
    engine = config.get("ocr_engine", "rapidocr")
    if engine == "windows":
        return _ocr_windows(pil_image)
    try:
        return _ocr_rapid(pil_image)
    except Exception:
        return _ocr_windows(pil_image)
