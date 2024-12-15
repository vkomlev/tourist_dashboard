# app/data/compare.py

from typing import Any, Dict, List, Optional, Type, Tuple
from app.data.database import Database
from app.models import Region, City, LocationType
import time
import logging

logger = logging.getLogger(__name__)


class Compare:
    """Базовый класс для сравнения данных из базы данных и внешних источников."""

    def __init__(self) -> None:
        """Инициализирует базовый класс."""
        self.input_data: List[Dict[str, Any]] = []
        self.database = Database()

    def load_from_database(self, model: Type[Any]) -> List[Dict[str, Any]]:
        """Загружает все записи из базы данных для указанной модели.

        Args:
            model (Type[Any]): Класс модели SQLAlchemy.

        Returns:
            List[Dict[str, Any]]: Список записей в виде словарей.
        """
        try:
            data = self.database.get_all(model)
            self.input_data = [Database.to_dict(obj=record) for record in data]
            logger.debug(f"Загружено {len(self.input_data)} записей из модели {model.__tablename__}.")
            return self.input_data
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных из базы данных: {e}")
            raise


class CompareRegions(Compare):
    """Класс для сравнения регионов из базы данных и внешних источников."""

    def __init__(self) -> None:
        """Инициализирует класс CompareRegions."""
        super().__init__()
        self.input_data_regions: Dict[str, int] = {}

    
    def load_regions_from_database(self) -> Dict[str, int]:
        """Загружает регионы из базы данных.

        Returns:
            Dict[str, int]: Словарь с названиями регионов и их ID.
        """
        try:
            self.load_from_database(Region)
            self.input_data_regions = {record['region_name']: record['id_region'] for record in self.input_data}
            logger.debug(f"Загружено {len(self.input_data_regions)} регионов из базы данных.")
            return self.input_data_regions
        except Exception as e:
            logger.error(f"Ошибка при загрузке регионов из базы данных: {e}")
            raise

    def compare_regions_from_weather(self) -> Tuple[Dict[str, int], List[str]]:
        """Сравнивает регионы из источника погоды с базой данных.

        Returns:
            Tuple[Dict[str, int], List[str]]: Найденные регионы и не найденные регионы.
        """
        from app.data.parsing import ParseWeather

        try:
            weather = ParseWeather()
            weather_regions = weather.parse_regions()
            self.load_regions_from_database()

            found_regions: Dict[str, int] = {}
            not_found_regions: List[str] = []

            for region_name in weather_regions.keys():
                check = self._check_names(region_name, self.input_data_regions)
                if check:
                    found_regions[check[1]] = self.input_data_regions[check[0]]
                else:
                    not_found_regions.append(region_name)

            logger.debug(
                f"Сравнение регионов завершено. Найдено: {len(found_regions)}, не найдено: {len(not_found_regions)}."
            )
            return found_regions, not_found_regions
        except Exception as e:
            logger.error(f"Ошибка при сравнении регионов: {e}")
            raise

    def _check_names(self, alt_name: str, input_data: Dict[str, int]) -> Optional[List[Any]]:
        """Проверяет соответствие названий регионов.

        Args:
            alt_name (str): Альтернативное название региона.
            input_data (Dict[str, int]): Словарь названий регионов и их ID.

        Returns:
            Optional[List[Any]]: Список с именем региона и его ID или None.
        """
        # Полное совпадение
        for sql_one in input_data.keys():
            sql_name_parts = sql_one.split(' ')
            if alt_name in sql_name_parts:
                return [sql_one, alt_name, input_data[sql_one]]

        # Частичное совпадение (первые 5 символов)
        for sql_one in input_data.keys():
            if sql_one.startswith(alt_name[:5]):
                return [sql_one, alt_name, input_data[sql_one]]

        return None


class CompareCities(CompareRegions):
    """Класс для сравнения городов из базы данных и внешних источников."""

    def __init__(self) -> None:
        """Инициализирует класс CompareCities."""
        super().__init__()
        self.count: int = 0
        self.input_data_cities: Dict[Tuple[str, int], int] = {}
        self.found_cities: Dict[int, Tuple[str, str]] = {}
        self.not_found_cities: Dict[str, List[str]] = {}

    
    def load_cities_from_database(self) -> Dict[Tuple[str, int], int]:
        """Загружает города из базы данных.

        Returns:
            Dict[Tuple[str, int], int]: Словарь с кортежами (название города, id региона) и id города.
        """
        try:
            self.load_from_database(City)
            self.input_data_cities = {
                (record['city_name'], record['id_region']): record['id_city']
                for record in self.input_data
            }
            logger.debug(f"Загружено {len(self.input_data_cities)} городов из базы данных.")
            return self.input_data_cities
        except Exception as e:
            logger.error(f"Ошибка при загрузке городов из базы данных: {e}")
            raise

    def union_cities(self) -> None:
        """Объединяет города из базы данных и источника погоды."""
        from app.data.parsing import ParseWeather

        try:
            self.count += 1
            self.all_found_cities: Dict[int, Tuple[str, str]] = {}
            self.all_not_found_cities: Dict[str, List[str]] = {}

            self.load_cities_from_database()
            time.sleep(2)

            weather = ParseWeather()
            weather_regions = weather.parse_regions()

            for i, (region_name, region_url) in enumerate(weather_regions.items(), 1):
                self.compare_cities_from_weather(region_url, region_name)
                self.all_found_cities.update(self.found_cities)
                self.all_not_found_cities.update(self.not_found_cities)
                logger.info(f"Прошли регион {i}: {region_name} ({region_url})")
                logger.info("-" * 20)

            logger.info(f"Прошли {i} регионов.")
            logger.info(f"Счётчик: {self.count}")
        except Exception as e:
            logger.error(f"Ошибка при объединении городов: {e}")
            raise

    def compare_cities_from_weather(self, region_url: str, region_name: str) -> None:
        """Сравнивает города из источника погоды с базой данных для конкретного региона.

        Args:
            region_url (str): URL региона из источника погоды.
            region_name (str): Название региона из источника погоды.

        Returns:
            None
        """
        from app.data.parsing import ParseWeather

        try:
            time.sleep(2)
            weather = ParseWeather()
            weather_cities = weather.parse_cities(region_url)
            self.load_regions_from_database()

            check_result = self._check_names(region_name, self.input_data_regions)
            if not check_result:
                logger.warning(f"Регион {region_name} не найден в базе данных.")
                return

            id_region = check_result[2]
            sql_cities_from_region = {
                key[0]: value for key, value in self.input_data_cities.items() if key[1] == id_region
            }

            found_cities: Dict[int, Tuple[str, str]] = {}
            not_found_cities: Dict[str, List[str]] = {}

            for city, url in weather_cities.items():
                check = self._check_names(city, {k: v for k, v in sql_cities_from_region.items()})
                if check:
                    found_cities[sql_cities_from_region[check[0]]] = (check[1], url)
                    logger.debug(f"Найден город: {city} (ID: {sql_cities_from_region[check[0]]})")
                else:
                    not_found_cities.setdefault(region_name, []).append(city)

            self.found_cities = found_cities
            self.not_found_cities = not_found_cities

        except Exception as e:
            logger.error(f"Ошибка при сравнении городов для региона {region_name}: {e}")
            raise


class CompareYandex(Compare):
    """Класс для сравнения данных из Yandex с данными из базы данных."""

    def __init__(self) -> None:
        """Инициализирует класс CompareYandex."""
        super().__init__()
        self.input_data_r_c: Dict[Tuple[str, str], List[int]] = {}
        self.input_data_yandex_locations_type: Dict[str, int] = {}

    def load_regions_city_location_from_database(self, level_loc_type = 1) -> Dict[Tuple[str, str], List[int]]:
        """Загружает регионы, города и типы локаций из базы данных для Yandex.

        Returns:
            Dict[Tuple[str, str], List[int]]: Словарь с кортежами (название региона, название города) и списком [id_region, id_city].
        """
        try:
            # Загрузка регионов
            self.load_from_database(Region)
            input_data_regions = self.input_data

            # Загрузка городов
            self.load_from_database(City)
            input_data_cities = self.input_data

            # Объединение регионов и городов
            self.input_data_r_c = {
                (region['region_name'], city['city_name']): [region['id_region'], city['id_city']]
                for region in input_data_regions
                for city in input_data_cities
                if city['id_region'] == region['id_region']
            }

            # Загрузка типов локаций, связанных с Yandex
            self.load_from_database(LocationType)
            self.input_data_yandex_locations_type = {
                record['name']: record['id_location_type']
                for record in self.input_data
                if 'yandex' in record['location_type_value'].lower()
                and int(record['location_type_key']) == level_loc_type
            }

            logger.debug(
                f"Загружено {len(self.input_data_r_c)} регионов и городов, связанных с Yandex: {len(self.input_data_yandex_locations_type)} типов локаций."
            )
            return self.input_data_r_c
        except Exception as e:
            logger.error(f"Ошибка при загрузке регионов, городов и типов локаций из базы данных: {e}")
            raise
