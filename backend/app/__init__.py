"""Flask 应用工厂。"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_object="app.config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    db.init_app(app)

    from app.routes.person import person_bp
    from app.routes.graph import graph_bp
    from app.routes.nlp import nlp_bp
    from app.routes.statistics import statistics_bp

    for bp in (person_bp, graph_bp, nlp_bp, statistics_bp):
        app.register_blueprint(bp, url_prefix="/api/v1")

    return app
