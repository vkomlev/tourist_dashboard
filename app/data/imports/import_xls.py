# app/data/imports/import_xls.py

import pandas as pd
from typing import Dict, Any, List
import os

from app.logging_config import logger



def load_yandex_locations(file_path: str, sheet_name: str = 'Лист1') -> List[Dict[str, Any]]:
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
