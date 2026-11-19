"""文本预处理：清洗、分句、繁简统一。"""

import re

SENT_END = re.compile(r"(?<=[。！？；])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_END.split(text) if s.strip()]
