"""离线翻译：ctranslate2 + sentencepiece 跑 Opus-MT（Argos）模型。

完全不需要联网、不需要 LM Studio、不需要 torch。
模型放在 exe/项目同级的 offline_models/{zh2en,en2zh}/ 目录下。
"""
import os
import re
import sys

_CJK = r"\u2e80-\u9fff\u3000-\u303f\uff00-\uffef"

_engines = {}


def _candidates():
    out = []
    try:
        import config
        configured = config.get("offline_model_dir", "")
        if configured:
            out.append(configured)
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(getattr(sys, "_MEIPASS", here), "offline_models"))
    out.append(os.path.join(here, "offline_models"))
    if getattr(sys, "frozen", False):
        out.append(os.path.join(os.path.dirname(sys.executable), "offline_models"))
    return out


def models_root():
    """返回存在的离线模型根目录；找不到返回 None。"""
    for c in _candidates():
        if c and os.path.isdir(c):
            return c
    return None


def is_available():
    root = models_root()
    if not root:
        return False
    for d in ("zh2en", "en2zh"):
        if not os.path.exists(os.path.join(root, d, "model", "model.bin")):
            return False
    return True


def _load(direction):
    if direction in _engines:
        return _engines[direction]
    root = models_root()
    if not root:
        raise RuntimeError("未找到 offline_models 模型目录")
    d = os.path.join(root, direction)
    spm_path = os.path.join(d, "sentencepiece.model")
    if not os.path.exists(spm_path):
        raise RuntimeError("离线模型不完整（缺少 sentencepiece.model）：%s" % d)

    import ctranslate2
    import sentencepiece as spm

    # 关键：用字节加载，规避 sentencepiece 不支持中文路径的问题
    with open(spm_path, "rb") as f:
        tokenizer = spm.SentencePieceProcessor()
        tokenizer.LoadFromSerializedProto(f.read())

    translator = ctranslate2.Translator(
        os.path.join(d, "model"), device="cpu", compute_type="int8")
    _engines[direction] = (translator, tokenizer)
    return _engines[direction]


def _split_sentences(text, limit=380):
    parts = [p for p in re.split(r"(?<=[。！？!?.;；\n])", text) if p]
    if not parts:
        return [text]
    chunks, buf = [], ""
    for p in parts:
        if len(buf) + len(p) <= limit:
            buf += p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _tidy(text, direction):
    text = text.replace("\u2581", " ").strip()
    if direction == "en2zh":
        # 去掉中文之间、以及中文与标点之间的多余空格
        text = re.sub(r"(?<=[%s])\s+(?=[%s])" % (_CJK, _CJK), "", text)
        text = re.sub(r"\s+([，。！？；：、）】》])", r"\1", text)
        text = re.sub(r"([（【《])\s+", r"\1", text)
        # 中文标点规范化：紧跟汉字的 , . ; : 换成全角（不动数字/英文里的）
        text = re.sub(r"(?<=[%s]),\s*" % _CJK, "，", text)
        text = re.sub(r"(?<=[%s]);\s*" % _CJK, "；", text)
        text = re.sub(r"(?<=[%s]):\s*" % _CJK, "：", text)
        text = re.sub(r"(?<=[%s])\.\s*(?=$|\s)" % _CJK, "。", text)
        text = re.sub(r"\.\s*$", "。", text)
    else:
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text


def _run(translator, tokenizer, text):
    pieces = tokenizer.encode(text, out_type=str)
    if not pieces:
        return ""
    # beam_size=6：实测比 4 略好（predict 能译成「预测」而不是「预言」），耗时几乎不变
    # no_repeat_ngram / repetition_penalty：抑制小模型的重复循环
    res = translator.translate_batch(
        [pieces], beam_size=6, no_repeat_ngram_size=3, repetition_penalty=1.3)
    return "".join(res[0].hypotheses[0])


def _broken(text):
    """小模型偶尔输出私用区乱码（如 \\ue14c），用它判断结果是否崩了。"""
    return bool(re.search(r"[\ue000-\uf8ff]", text))


def translate(text, direction):
    """direction: 'zh2en' | 'en2zh'。按行翻译并保留换行结构。"""
    if not text or not text.strip():
        return ""
    translator, tokenizer = _load(direction)
    sep = " " if direction == "zh2en" else ""

    out_lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        pieces_out = []
        for chunk in _split_sentences(raw):
            out = _tidy(_run(translator, tokenizer, chunk), direction)
            if _broken(out):
                # 无标点的短句容易崩，补个句末标点重试一次（标点要跟输入语言一致）
                tail = "。" if direction == "zh2en" else "."
                retry = _tidy(_run(translator, tokenizer, chunk + tail), direction)
                if not _broken(retry):
                    out = retry
            if out:
                pieces_out.append(out)
        if pieces_out:
            out_lines.append(sep.join(pieces_out))
    return "\n".join(out_lines)
