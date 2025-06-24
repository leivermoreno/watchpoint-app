import os
from flask import Flask, render_template


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    @app.get("/hello")
    def hello():
        return render_template("base.html")

    return app
