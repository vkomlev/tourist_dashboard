'''from flask import Flask

def create_app():
    print('Creating app2')
    app = Flask(__name__)

    from .routes import main
    app.register_blueprint(main)

    return app'''
