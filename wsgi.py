# app/__init__.py

import logging
from flask import Flask
from app.logging_config import logger  # Импортируем настроенный логгер

def create_app() -> Flask:
    """
    Создание и настройка Flask приложения.

    Возвращает:
        Flask: Инстанс Flask приложения.
    """
    logger.info('Создание Flask приложения')  # Логирование создания приложения
    app = Flask(__name__, static_folder='static', template_folder='templates')

    from app.main.routes import main
    app.register_blueprint(main)

    return app
