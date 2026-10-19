"""翻译模块：本地 LM Studio 优先，可云端 API 兜底，再兜底内置离线模型。

translate_backend:
- auto   ：先本地 LM Studio → 失败则云端 API → 再失败则内置离线模型
- local  ：只用本地 LM Studio
- cloud  ：只用云端 OpenAI 兼容接口
- offline：只用内置离线模型（无需联网、无需本地 AI）
"""
import os
import re
import subprocess
import time

import requests

import config
import offline_translate

# 本地 LM Studio 是 127.0.0.1，绝不能走系统代理：
# 用户开着代理/VPN 时 requests 默认会把 localhost 也丢给代理，导致本地 AI 直接失效。
_local_session = requests.Session()
_local_session.trust_env = False

_DIRECTIONS = {
    "zh2en": "Translate the following Chinese text into English. "
             "Output only the translation, no explanation, no quotes.",
    "en2zh": "把下面的英文翻译成中文。只输出译文本身，不要任何解释、不要引号。",
}


def _detect_direction(text):
    """按内容猜方向：含中文则中→英，否则英→中。"""
    return "zh2en" if re.search(r"[\u4e00-\u9fff]", text) else "en2zh"


def _resolve_direction(cfg, text):
    """把 auto 解析成明确方向。

    为什么不在提示词里让模型自己判断：hy-mt2-1.8b 这类专用翻译模型对
    「先判断语言再翻译」的指令不敏感，实测会把英文原文原样回显（英文进英文出）。
    所以在本地判断好方向，只给模型一个明确的翻译指令。
    """
    configured = (cfg or {}).get("translate_direction", "auto")
    if configured in _DIRECTIONS:
        return configured
    return _detect_direction(text)


# ---------------- 本地（LM Studio） ----------------
def _headers(cfg):
    h = {"Content-Type": "application/json"}
    if cfg.get("api_token"):
        h["Authorization"] = "Bearer " + cfg["api_token"]
    return h


def _server_up(cfg):
    try:
        r = _local_session.get(cfg["lmstudio_url"].rstrip("/") + "/models",
                               headers=_headers(cfg), timeout=5)
        r.raise_for_status()
        return True
    except Exception:
        return False


def _run_lms(cfg, args, timeout=180):
    lms = cfg.get("lms_exe")
    if not lms:
        raise RuntimeError("未配置 LM Studio CLI 路径（lms_exe）")
    subprocess.run([lms] + args, capture_output=True, timeout=timeout)


def _ensure_server(cfg):
    if _server_up(cfg):
        return
    lms = cfg.get("lms_exe")
    # 没装 LM Studio 时立刻失败，别傻等 15 秒（那 15 秒会拖慢回退到云端/离线）
    if not lms or not os.path.exists(lms):
        raise RuntimeError("未找到 LM Studio（%s），本地翻译不可用" % (lms or "lms_exe 未配置"))
    try:
        _run_lms(cfg, ["server", "start"], timeout=40)
    except Exception:
        pass
    for _ in range(30):
        time.sleep(0.5)
        if _server_up(cfg):
            return
    raise RuntimeError("LM Studio 服务未启动（%s）" % cfg.get("lmstudio_url"))


def _payload(model, text, system):
    """两种后端共用同一套请求体结构。"""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "stream": False,
    }


def _post_completion(cfg, text, system):
    url = cfg["lmstudio_url"].rstrip("/") + "/chat/completions"
    return _local_session.post(url, headers=_headers(cfg),
                               json=_payload(cfg["model"], text, system), timeout=180)


def _local_translate(cfg, text, system):
    _ensure_server(cfg)
    r = _post_completion(cfg, text, system)
    if r.status_code != 200:
        low = r.text.lower()
        if "not loaded" in low or "load" in low or r.status_code in (404, 409, 500):
            try:
                _run_lms(cfg, ["load", cfg["model"], "--gpu", "max", "-y"], timeout=180)
            except Exception:
                pass
            for _ in range(90):
                time.sleep(1)
                r2 = _post_completion(cfg, text, system)
                if r2.status_code == 200:
                    return r2.json()["choices"][0]["message"]["content"].strip()
        raise RuntimeError("HTTP %s：%s" % (r.status_code, r.text[:160]))
    return r.json()["choices"][0]["message"]["content"].strip()


# ---------------- 云端（OpenAI 兼容） ----------------
def _cloud_config(cfg):
    """返回 (base_url, api_key, model, 是否复用了解题配置)。

    翻译有自己的云端配置，但用户往往只在「解题」里填了一次 Key。
    翻译这边没配全时，复用解题的云端配置——否则会白白掉到离线小模型（质量差很多）。
    """
    url = (cfg.get("cloud_base_url") or "").strip()
    key = (cfg.get("cloud_api_key") or "").strip()
    model = (cfg.get("cloud_model") or "").strip()
    if key and model:
        return url, key, model, False
    s_key = (cfg.get("solve_cloud_key") or "").strip()
    s_model = (cfg.get("solve_cloud_model") or "").strip()
    if s_key and s_model:
        return (cfg.get("solve_cloud_url") or url).strip(), s_key, s_model, True
    return url, key, model, False


def _cloud_ready(cfg):
    url, key, model, _ = _cloud_config(cfg)
    return bool(url and key and model)


def _cloud_translate(cfg, text, system):
    base, key, model, _ = _cloud_config(cfg)
    url = base.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    }
    # 云端用默认 session（允许走系统代理，跨境服务常需要）
    r = requests.post(url, headers=headers,
                      json=_payload(model, text, system), timeout=120)
    if r.status_code != 200:
        raise RuntimeError("HTTP %s：%s" % (r.status_code, r.text[:160]))
    return r.json()["choices"][0]["message"]["content"].strip()


# ---------------- 对外入口 ----------------
def local_status():
    """返回 (是否可用, 说明)。说明里带 HTTP 结果和失败原因，方便排查。

    必须用 _local_session：用户开着系统代理时，普通 requests 会把
    127.0.0.1 也丢给代理，检测就会假失败（表现为 401/502），误判成「没装本地 AI」。
    """
    try:
        cfg = config.get_all()
        base = (cfg.get("lmstudio_url") or "").strip()
        if not base:
            return False, "未配置 LM Studio 地址"
        url = base.rstrip("/") + "/models"
        r = _local_session.get(url, headers=_headers(cfg), timeout=6)
        r.raise_for_status()
        return True, "HTTP %s" % r.status_code
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, str(exc)[:80])


_last_backend = None   # 上一次翻译实际用了哪条路：local / cloud / offline


def last_backend():
    """供界面显示「这次翻译是用什么翻的」，方便用户判断质量。"""
    return _last_backend


def translate(text):
    """按配置的优先级翻译文本：本地 → 云端 → 内置离线。"""
    global _last_backend
    if not text or not text.strip():
        return ""
    cfg = config.get_all()

    # 方向在本地定好（auto 也要先解析成具体方向，见 _resolve_direction 说明）
    direction = _resolve_direction(cfg, text)
    system = _DIRECTIONS[direction]

    backend = cfg.get("translate_backend", "auto")
    errors = []

    # ① 本地 LM Studio
    if backend in ("auto", "local"):
        try:
            out = _local_translate(cfg, text, system)
            _last_backend = "local"
            return out
        except Exception as exc:
            errors.append("本地 LM Studio：%s" % exc)
            if backend == "local":
                raise RuntimeError("本地 LM Studio 翻译失败：%s" % exc)

    # ② 云端 API
    if backend in ("auto", "cloud"):
        if _cloud_ready(cfg):
            try:
                out = _cloud_translate(cfg, text, system)
                _last_backend = "cloud"
                return out
            except Exception as exc:
                errors.append("云端 API：%s" % exc)
                if backend == "cloud":
                    raise RuntimeError("云端翻译失败：%s" % exc)
        elif backend == "cloud":
            raise RuntimeError("云端翻译未配置：请在设置里填 API 地址、API Key、模型名")

    # ③ 内置离线模型
    if backend in ("auto", "offline"):
        if offline_translate.is_available():
            try:
                out = offline_translate.translate(text, direction)
                _last_backend = "offline"
                return out
            except Exception as exc:
                errors.append("内置离线模型：%s" % exc)
                if backend == "offline":
                    raise RuntimeError("内置离线翻译失败：%s" % exc)
        elif backend == "offline":
            raise RuntimeError("未安装离线模型：请把 offline_models 文件夹放到程序目录下")

    raise RuntimeError("没有可用的翻译方式：\n" + "\n".join(errors))
