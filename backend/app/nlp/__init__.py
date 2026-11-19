"""文本抽取模块。不依赖 Flask，可单独调用与测试。"""

from app.nlp.entity_resolution import resolve_entities
from app.nlp.event_extraction import extract_events
from app.nlp.ner import extract_entities
from app.nlp.relation_extraction import extract_relations

__all__ = ["extract_entities", "resolve_entities", "extract_relations", "extract_events"]
