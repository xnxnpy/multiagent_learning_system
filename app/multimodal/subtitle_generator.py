"""SRT 字幕生成器：根据文本和音频时长生成时间轴对齐的字幕"""
import re
from typing import List, Tuple
from app.core.ppt_video_config import SENTENCE_DELIMITERS, CLAUSE_DELIMITERS


def _split_sentences(text: str) -> List[str]:
    """将文本按句子分割"""
    if not text or not text.strip():
        return []

    pattern = f"([{re.escape(SENTENCE_DELIMITERS)}])"
    parts = re.split(pattern, text.strip())

    sentences = []
    current = ""
    for part in parts:
        if not part:
            continue
        if part in SENTENCE_DELIMITERS:
            current += part
            if current.strip():
                sentences.append(current.strip())
            current = ""
        else:
            if current.strip():
                sentences.append(current.strip())
            current = part

    if current.strip():
        sentences.append(current.strip())

    final = []
    for s in sentences:
        if len(s) > 30:
            sub = _split_by_clauses(s)
            final.extend(sub)
        else:
            final.append(s)

    return final if final else [text.strip()]


def _split_by_clauses(text: str) -> List[str]:
    """按逗号等弱分隔符拆分长句"""
    pattern = f"([{re.escape(CLAUSE_DELIMITERS)}])"
    parts = re.split(pattern, text)

    result = []
    current = ""
    for part in parts:
        if not part:
            continue
        if part in CLAUSE_DELIMITERS:
            current += part
            if current.strip():
                result.append(current.strip())
            current = ""
        else:
            current += part

    if current.strip():
        result.append(current.strip())

    return result if result else [text]


def _format_srt_time(seconds: float) -> str:
    """将秒数转为 SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(text: str, audio_duration: float) -> str:
    """根据文本和音频时长生成 SRT 字幕"""
    if not text or not text.strip():
        return ""

    sentences = _split_sentences(text)
    if not sentences:
        return ""

    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return ""

    srt_blocks = []
    current_time = 0.0

    for i, sentence in enumerate(sentences):
        char_ratio = len(sentence) / total_chars
        duration = char_ratio * audio_duration

        start_time = current_time
        end_time = current_time + duration
        current_time = end_time

        start_str = _format_srt_time(start_time)
        end_str = _format_srt_time(end_time)

        srt_blocks.append(f"{i + 1}\n{start_str} --> {end_str}\n{sentence}")

    return "\n\n".join(srt_blocks) + "\n"
