"""关系图谱接口。"""

from flask import Blueprint, jsonify, request

graph_bp = Blueprint("graph", __name__)


@graph_bp.get("/graph")
def graph():
    person_id = request.args.get("person_id", type=int)
    depth = request.args.get("depth", default=1, type=int)
    return jsonify({"nodes": [], "edges": [],
                    "person_id": person_id, "depth": depth})
