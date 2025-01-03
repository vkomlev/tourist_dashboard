# app/__init__.py
from flask import Flask
from app.logging_config import logger
from app.reports.dashboard import create_dashboard  # Импорт функции создания Dash
# Другие импорты...

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

    # Интеграция Dash-приложения
    dashboard = create_dashboard(app)  # Передаем Flask-приложение в Dash
    # Если необходимо, можно сохранить объект Dash в app.extensions или другом месте

    return app