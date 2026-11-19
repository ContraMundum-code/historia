"""文本抽取接口。"""

from flask import Blueprint, jsonify, request

nlp_bp = Blueprint("nlp", __name__)


@nlp_bp.post("/nlp/extract")
def extract():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    tasks = payload.get("tasks", ["ner", "relation", "event"])

    from app.nlp import extract_entities, extract_events, extract_relations

    entities = extract_entities(text) if "ner" in tasks else []
    relations = extract_relations(text, entities) if "relation" in tasks else []
    events = extract_events(text, entities) if "event" in tasks else []

    return jsonify({"entities": entities, "relations": relations, "events": events})
