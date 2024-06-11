from flask import Flask

def create_app():
    print('Creating app')
    app = Flask(__name__, static_folder='static', template_folder='templates')

    from app.main.routes import main
    app.register_blueprint(main)

    return app
