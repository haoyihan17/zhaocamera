"""自检模式：`ZhaoCamera.exe --selftest`（或 python main.py --selftest）。

把各组件状态写到程序目录的 selftest_report.txt，方便排查「对方电脑上哪一环不可用」。
"""
import os
import sys
import traceback

import config


def run():
    lines = []

    def log(msg=""):
        lines.append(str(msg))

    log("赵相机 自检报告")
    log("=" * 46)
    log("打包运行: %s" % bool(getattr(sys, "frozen", False)))
    log("Python: %s" % sys.version.split()[0])

    try:
        config.load()
        log("配置: theme=%s ocr_engine=%s translate_backend=%s" % (
            config.get("theme"), config.get("ocr_engine"),
            config.get("translate_backend")))
    except Exception as exc:
        log("配置读取失败: %s" % exc)

    # ---- OCR ----
    log()
    log("[文字识别 OCR]")
    try:
        from PIL import Image, ImageDraw, ImageFont
        import ocr
        img = Image.new("RGB", (460, 90), "white")
        d = ImageDraw.Draw(img)
        d.text((12, 26), "SELFTEST 123", font=ImageFont.load_default(), fill="black")
        log("  引擎: %s" % config.get("ocr_engine"))
        log("  识别结果: %r" % ocr.ocr_pil_image(img))
    except Exception as exc:
        log("  失败: %s" % exc)
        log(traceback.format_exc())

    # ---- 离线翻译 ----
    log()
    log("[内置离线翻译]")
    try:
        import offline_translate
        log("  模型可用: %s" % offline_translate.is_available())
        log("  模型目录: %s" % offline_translate.models_root())
        if offline_translate.is_available():
            log("  zh2en: %r" % offline_translate.translate("这是一个测试。", "zh2en"))
            log("  en2zh: %r" % offline_translate.translate("This is a test.", "en2zh"))
    except Exception as exc:
        log("  失败: %s" % exc)
        log(traceback.format_exc())

    # ---- 本地 LM Studio ----
    log()
    log("[本地 AI]")
    try:
        import translator
        ok, detail = translator.local_status()
        log("  LM Studio 服务可用: %s  (%s)" % (ok, detail))
    except Exception as exc:
        log("  失败: %s" % exc)

    # ---- 外部程序 ----
    log()
    log("[系统联动]")
    try:
        import external_open
        log("  截图工具 ProgID: %s" % external_open.find_snipping_tool_progid())
    except Exception as exc:
        log("  失败: %s" % exc)

    log()
    log("（以上内容已写入 selftest_report.txt）")

    out = os.path.join(config.BASE_DIR, "selftest_report.txt")
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        out = os.path.join(os.path.expandvars(r"%TEMP%"), "selftest_report.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    return out
