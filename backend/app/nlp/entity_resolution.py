"""人物消歧。别名词典 + 上下文规则，把字号谥号归一到人物 ID。"""


def resolve_entities(entities: list[dict], alias_map: dict[str, int]) -> list[dict]:
    """把提及映射到人物 ID。未命中时 person_id 为 None，等待人工审核。"""
    for ent in entities:
        ent["person_id"] = alias_map.get(ent.get("name", ""))
    return entities
