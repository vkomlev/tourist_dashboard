# app/data/imports/import_xls.py

import pandas as pd
from typing import Dict, Any, List
import os

from app.data.database import Database
from app.models import LocationType
from app.logging_config import logger


def import_xls(file_path: str, sheet_name: str = 'Sheet1') -> None:
    """
    Импортирует данные из Excel-файла в таблицу базы данных.

    Args:
        file_path (str): Путь к Excel-файлу.
        sheet_name (str, optional): Название листа в Excel-файле. По умолчанию 'Sheet1'.

    Raises:
        FileNotFoundError: Если файл не существует.
        Exception: Если происходит ошибка при импорте данных.
    """
    logger.info(f"Начало импорта данных из Excel-файла: {file_path}, лист: {sheet_name}")

    # Проверка существования файла
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не существует.")
        raise FileNotFoundError(f"Файл {file_path} не существует.")

    # Создание экземпляра Database
    db = Database()
    logger.debug("Экземпляр Database успешно создан.")

    try:
        # Чтение Excel-файла
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.debug(f"Excel-файл {file_path} прочитан успешно.")

        # Преобразование DataFrame в список объектов LocationType
        location_types: List[LocationType] = []
        for _, row in df.iterrows():
            try:
                lt = LocationType(
                    location_type_value=row['location_type_value'],
                    name=row['name_loc'],
                    general=row['type_loc']
                )
                location_types.append(lt)
                logger.debug(f"Создан LocationType объект: {lt}")
            except KeyError as e:
                logger.warning(f"Ошибка при обработке строки {row}: {e}")
                continue  # Пропустить некорректные строки

        # Добавление всех объектов в базу данных
        db.add_all(location_types)
        logger.info(f"Добавлено {len(location_types)} записей в таблицу LocationType.")

        logger.info(f"Данные из файла {file_path} успешно импортированы в таблицу LocationType.")
    except Exception as e:
        logger.exception(f"Ошибка при импорте данных из файла {file_path}: {e}")
        raise
    finally:
        # Закрытие соединения с базой данных, если требуется
        db.close()
        logger.debug("Соединение с базой данных закрыто.")

def load_yandex_locations(file_path: str, sheet_name: str = 'Sheet1') -> List[Dict[str, Any]]:
    """
    Загружает типы локаций для Яндекс Карт из Excel-файла.
    
    Args:
        file_path (str): Путь к Excel-файлу.
        sheet_name (str, optional): Название листа в Excel-файле. По умолчанию 'Sheet1'.
    
    Returns:
        List[Dict[str, Any]]: Список словарей с данными типов локаций.
    
    Raises:
        FileNotFoundError: Если файл не существует.
        Exception: Если происходит ошибка при чтении файла.
    """
    logger.info(f"Начало загрузки типов локаций из файла: {file_path}, лист: {sheet_name}")
    
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не существует.")
        raise FileNotFoundError(f"Файл {file_path} не существует.")
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.info(f"Успешно загружен Excel-файл: {file_path}")
    except Exception as e:
        logger.exception(f"Ошибка при чтении Excel-файла {file_path}: {e}")
        raise
    
    required_columns = {"name_loc", "type_loc"}
    if not required_columns.issubset(df.columns):
        logger.error(f"Excel-файл должен содержать столбцы: {required_columns}")
        raise ValueError(f"Excel-файл должен содержать столбцы: {required_columns}")
    
    locations = df.to_dict(orient='records')
    logger.debug(f"Загружено {len(locations)} записей типов локаций.")
    return locations