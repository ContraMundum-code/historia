"""统计接口。"""

from flask import Blueprint, jsonify

statistics_bp = Blueprint("statistics", __name__)


@statistics_bp.get("/statistics/overview")
def overview():
    return jsonify({"persons": 0, "documents": 0, "relations": 0, "events": 0})
