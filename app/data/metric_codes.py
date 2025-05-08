# app/data/metric_codes.py

"""
Модуль с маппингом “ключевых имён” метрик на их реальные id_metrics из БД.
"""

from typing import Dict

METRIC_CODE_MAP: Dict[str, int] = {
    # Комплексная оценка туристской инфраструктуры
    'T_total': (282, 'Комплексная оценка инфраструктуры'),       # complex_like
    # Комплексная оценка сегментов
    'T_segments': (217,'Комплексная оценка сегментов'),    # t_segments
    # Средняя оценка общей инфраструктуры
    'O': (218,'Средняя оценка общей инфраструктуры'),       # O
    # Поток и ночёвки
    'V': (283,'Турпоток'),             # complex_tur
    'N': (284,'Ночёвки'),             # complex_night
    # Климат и цены, дистанция
    'C': (222,'Климат'),             # complex_w
    'P': (286,'Цена'),             # complex_p
    # 'P': <цена — пока не реализовано>,  
    'D': (285, 'Удаленность от столицы'),             # complex_distance
    # Дополнительные компоненты инфраструктуры
    'Q': (240,'Основная инфраструктура кол-во'),             # complex_o
    'L': (241,'Дополнительная инфраструктура  кол-во'),             # complex_l
}

def get_metric_code(metric_name: str) -> int:
    """
    Возвращает целое id_metrics по “ключевому” имени метрики.

    Args:
        metric_name: одно из ключей METRIC_CODE_MAP.

    Returns:
        Целое число, которое является id_metrics из БД.
    """
    if metric_name not in METRIC_CODE_MAP:
        return 3
    return METRIC_CODE_MAP[metric_name]
