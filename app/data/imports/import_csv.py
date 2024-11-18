# app\data\imports\import_csv.py

import csv
import os
from typing import List, Dict, Tuple
import pandas as pd


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
    from app.data.database import Database
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

def load_regions_from_csv(self, path: str) -> Dict[str, int]:
        """Загружает регионы из CSV файла.

        Args:
            path (str): Путь к CSV файлу.

        Returns:
            Dict[str, int]: Словарь с названиями регионов и их ID.
        """
        try:
            df = pd.read_csv(path, delimiter=';')
            self.input_data_regions = {row['region_name']: row['id_region'] for _, row in df.iterrows()}
            logger.debug(f"Загружено {len(self.input_data_regions)} регионов из CSV файла {path}.")
            return self.input_data_regions
        except FileNotFoundError:
            logger.error(f"Файл {path} не найден.")
            raise
        except pd.errors.ParserError as e:
            logger.error(f"Ошибка парсинга CSV файла {path}: {e}")
            raise
        except KeyError as e:
            logger.error(f"Отсутствует необходимый столбец в CSV файле {path}: {e}")
            raise

def load_cities_from_csv(self, path: str) -> Dict[Tuple[str, int], int]:
        """Загружает города из CSV файла.

        Args:
            path (str): Путь к CSV файлу.

        Returns:
            Dict[Tuple[str, int], int]: Словарь с кортежами (название города, id региона) и id города.
        """
        try:
            df = pd.read_csv(path, delimiter=';')
            self.input_data_cities = {
                (row['city_name'], row['id_region']): row['id_city']
                for _, row in df.iterrows()
            }
            logger.debug(f"Загружено {len(self.input_data_cities)} городов из CSV файла {path}.")
            return self.input_data_cities
        except FileNotFoundError:
            logger.error(f"Файл {path} не найден.")
            raise
        except pd.errors.ParserError as e:
            logger.error(f"Ошибка парсинга CSV файла {path}: {e}")
            raise
        except KeyError as e:
            logger.error(f"Отсутствует необходимый столбец в CSV файле {path}: {e}")
            raise