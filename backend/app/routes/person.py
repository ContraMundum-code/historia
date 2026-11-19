"""人物相关接口。"""

from flask import Blueprint, jsonify

person_bp = Blueprint("person", __name__)


@person_bp.get("/persons")
def list_persons():
    return jsonify({"items": [], "total": 0})


@person_bp.get("/persons/<int:person_id>")
def person_detail(person_id: int):
    return jsonify({"person_id": person_id})


@person_bp.get("/persons/<int:person_id>/relations")
def person_relations(person_id: int):
    return jsonify({"person_id": person_id, "relations": []})
