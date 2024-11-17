# app\data\imports\import_csv.py

import csv
import os
from typing import List

from app.data.database import Database
from app.models import Sync
from app.logging_config import logger


def import_csv(file_path: str, delimiter: str = ',') -> None:
    """
    Импортирует данные из CSV-файла в таблицу sync базы данных.

    Эта функция читает данные из указанного CSV-файла и добавляет их
    в таблицу sync базы данных.

    Args:
        file_path (str): Путь к CSV-файлу.
        delimiter (str, optional): Разделитель в CSV-файле. По умолчанию ','.

    Raises:
        FileNotFoundError: Если файл не существует.
        Exception: Если происходит ошибка при импорте данных.
    """
    logger.info(f"Начало импорта данных из файла: {file_path}")

    # Проверка существования файла
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не существует.")
        raise FileNotFoundError(f"Файл {file_path} не существует.")

    # Создание экземпляра Database
    db = Database()
    logger.debug("Экземпляр Database успешно создан.")

    try:
        # Открытие CSV-файла и чтение данных
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            logger.debug(f"CSV-файл {file_path} открыт для чтения.")

            # Перебор строк в CSV и добавление их в список объектов Sync
            sync_records: List[Sync] = []
            for row in reader:
                try:
                    sync_record = Sync(
                        id_to=int(row['id_to']),
                        object_type=row['object_type'],
                        input_value=row['input_value'],
                        input_from=row['input_from']
                    )
                    sync_records.append(sync_record)
                    logger.debug(f"Создан Sync объект: {sync_record}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"Ошибка при обработке строки {row}: {e}")
                    continue  # Пропустить некорректные строки

            # Добавление всех объектов в базу данных
            db.add_all(sync_records)
            logger.info(f"Добавлено {len(sync_records)} записей в таблицу sync.")

        logger.info(f"Данные из файла {file_path} успешно импортированы в таблицу sync.")
    except Exception as e:
        logger.exception(f"Ошибка при импорте данных из файла {file_path}: {e}")
        raise
    finally:
        # Закрытие соединения с базой данных, если требуется
        db.close()
        logger.debug("Соединение с базой данных закрыто.")
