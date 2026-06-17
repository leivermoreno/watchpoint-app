import os
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from .db import db

load_dotenv()

csrf = CSRFProtect()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env()
    app.config.from_mapping(
        SECRET_KEY=os.environ["WATCHPOINT_SECRET_KEY"],
        SQLALCHEMY_DATABASE_URI=os.environ["WATCHPOINT_DATABASE_URI"],
        # keep pooled connections healthy across networked databases
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 1800,  # recycle conns older than 30 min; keep under the DB/proxy idle timeout
            # return timestamptz values as UTC so the backend works only in UTC
            "connect_args": {"options": "-c timezone=utc"},
        },
        WATCHPOINT_WATCHMODE_API_KEY=os.environ["WATCHPOINT_WATCHMODE_API_KEY"],
    )

    # create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .title.blueprint import bp as title_bp

    app.register_blueprint(title_bp)
    app.add_url_rule("/", "index")

    from .auth.blueprint import bp as auth_bp

    app.register_blueprint(auth_bp)

    from .watchlist.blueprint import bp as watchlist_bp

    app.register_blueprint(watchlist_bp)

    from .review.blueprint import bp as review_bp

    app.register_blueprint(review_bp)

    return app
