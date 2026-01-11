import os
from flask import Flask
from db import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("WATCHPOINT_SECRET_KEY", "insecure-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "WATCHPOINT_DATABASE_URI", "postgresql://watchpoint@/watchpoint"
        ),
        WATCHPOINT_WATCHMODE_API_KEY=os.environ["WATCHPOINT_WATCHMODE_API_KEY"],
    )
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env()

    # create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    import title.blueprint

    app.register_blueprint(title.blueprint.bp)
    app.add_url_rule("/", "index")

    import auth.blueprint

    app.register_blueprint(auth.blueprint.bp)

    import watchlist.blueprint

    app.register_blueprint(watchlist.blueprint.bp)

    import review.blueprint

    app.register_blueprint(review.blueprint.bp)

    with app.app_context():
        db.create_all()

    return app
