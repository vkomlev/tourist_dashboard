# app/additional/textutil.py

from typing import Dict
from app.logging_config import logger

# Словарь для транслитерации символов с русского на латиницу
TRANSLIT_MAP: Dict[str, str] = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', ' ': '_',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
    'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}


def transliterate(name: str) -> str:
    """
    Транслитерация строки с русского на латиницу.

    Эта функция преобразует переданную строку, заменяя русские символы
    на соответствующие латинские, а также заменяет пробелы на подчеркивания.

    Args:
        name (str): Исходная строка на русском языке.

    Returns:
        str: Транслитерированная строка на латинице.

    Raises:
        TypeError: Если входное значение не является строкой.
    """
    if not isinstance(name, str):
        logger.error(f"Неверный тип данных для транслитерации: {type(name)}. Ожидалась строка.")
        raise TypeError("Аргумент 'name' должен быть строкой.")

    logger.debug(f"Начало транслитерации строки: {name}")

    transliterated = ''.join(TRANSLIT_MAP.get(char, char) for char in name)
    transliterated = transliterated.replace(' ', '_')

    logger.debug(f"Результат транслитерации: {transliterated}")
    return transliterated
