import os
from flask import Flask, render_template


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY="dev")
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env()

    # create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    import title.blueprint

    app.register_blueprint(title.blueprint.bp)
    app.add_url_rule("/", "index")

    return app
