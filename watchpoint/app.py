import os
from flask import Flask
from db import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="postgresql://watchpoint@/watchpoint",
    )
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env()

    # create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    import title.blueprint

    app.register_blueprint(title.blueprint.bp)
    app.add_url_rule("/", "index")

    with app.app_context():
        db.create_all()

    return app
