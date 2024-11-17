# app/logging_config.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Создание директории для логов, если она не существует
log_directory: Path = Path('logs')
log_directory.mkdir(exist_ok=True)

handler = RotatingFileHandler(
    log_directory / 'app.log',  # Использование Path для построения пути
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=5  # Количество резервных файлов
)

logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Исправлено на %(levelname)s
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)
