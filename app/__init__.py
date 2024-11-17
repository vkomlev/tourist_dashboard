# app/__init__.py

from flask import Flask
from app.logging_config import logger

def create_app() -> Flask:
    """
    Создание и настройка Flask приложения.

    Возвращает:
        Flask: Инстанс Flask приложения.
    """
    logger.info('Creating app')  # Логирование создания приложения
    app = Flask(__name__, static_folder='static', template_folder='templates')

    from app.main.routes import main
    app.register_blueprint(main)

    return app
