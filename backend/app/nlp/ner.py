"""人物识别。第一版用 HanLP 预训练模型做推理，不训练。"""


def extract_entities(text: str) -> list[dict]:
    """识别人物提及。

    返回 [{"name": str, "start": int, "end": int}, ...]，下标为左闭右开。
    """
    return []
