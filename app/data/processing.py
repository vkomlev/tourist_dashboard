# app/data/processing.py

import random
import time
import logging
from typing import Any, Dict, List, Tuple, Optional

from app.data.compare import CompareRegions, CompareCities, CompareYandex
from app.data.database import (
    SyncRepository, Database, LocationsRepository, ReviewRepository, PhotoRepository, CitiesRepository,
    MetricValueRepository, LocationTypeRepository
)
from app.data.parsing import ParseYandexMap, ParseWeather
from app.models import City, Region, Location

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ProcessingError(Exception):
    """Исключение, возникающее при ошибках обработки данных."""
    pass


class DataProcessor:
    """Класс для обработки данных: парсинг, сравнение и заполнение базы данных."""

    def __init__(self) -> None:
        """Инициализирует DataProcessor."""
        self.compare_yandex = CompareYandex()
        self.parse_yandex = ParseYandexMap()
        self.parse_weather = ParseWeather()
        self.database = Database()
        self.MAX_RETRIES = 3

    def process_yandex_locations(self, specific_region: Tuple[str, str] = '', level_loc_type: int = 1, restart = False) -> None:
        """
        Обрабатывает локации из Яндекс.Карт для указанного региона.

        Args:
            specific_region (Tuple[str, str], optional): Кортеж с названием региона и города.
            level_loc_type int: определяем уровень парсящихся локаций (1 самый важные)
            restart False: начинать вэб-скрапинг города/городов с нуля или нет
        """
        # Загрузка регионов, городов и типов локаций из базы данных
        self.compare_yandex.load_regions_city_location_from_database(level_loc_type=level_loc_type)
        regions_cities = self.compare_yandex.input_data_r_c
        type_locations = self.compare_yandex.input_data_yandex_locations_type
        try:
            for key_name_r_c, value_id_r_c in regions_cities.items():
                if specific_region and not specific_region[:len(specific_region)] == key_name_r_c[:len(specific_region)]:
                    continue
                skipping_loaded_types = True
                # Перебор типов локаций
                for type_name, type_id in type_locations.items():
                    cities_repo = CitiesRepository()
                    if not restart and skipping_loaded_types:
                        last_type_loc = cities_repo.check_type_loc(id_city=value_id_r_c[1], first_type=type_id)
                        # если тип локации из цикла совпал с локацией из БД на которой остановили ранее
                        if skipping_loaded_types and int(last_type_loc) == type_id:
                            skipping_loaded_types = False
                        # если не совпал и осталась True
                        if skipping_loaded_types:
                            logger.info(f"Тип локации {type_name} уже обработан для города ID {value_id_r_c[1]}. Пропускаем.")
                            continue                    
                    cities_repo.load_next_type_loc(id_city=value_id_r_c[1], type_loc=type_id)
                    # time.sleep(random.uniform(1, 15))

                    region_city_loc = f'{key_name_r_c[0]} {key_name_r_c[1]} {type_name}'
                    logger.info(f'Начали обработку: {region_city_loc}')

                    # Парсинг локаций с Яндекс.Карт
                    dict_locations = self.parse_yandex.get_locations(region_city_loc)
                    if not dict_locations:
                        logger.warning(f'Локации для {region_city_loc} не найдены.')
                        continue

                    for i, (loc_name, loc_url) in enumerate(dict_locations.items(), 1):
                        loc_name = loc_name.split(';')[0]
                        logger.info(f'Обработка локации {i}: {loc_name}')
                        id_yandex = self.extract_id_yandex(loc_url)
                        if not id_yandex:
                            logger.warning(f'Локация {loc_name} имеет некорректный URL: {loc_url}')
                            continue
                        locations_repo = LocationsRepository()
                        bd_location = locations_repo.check_loc_yandex(
                            # location_name=loc_name,
                            # coordinates = self.parse_yandex.loc_info.get('coordinates'),
                            id_yandex = id_yandex
                        )

                        if bd_location and bd_location.characters.get('id_yandex') == id_yandex:
                            logger.info(f'Локация {loc_name} - {id_yandex} уже есть')

                        else:
                            logger.info(f'Создание новой локации: {loc_name}')
                            logger.info(f'Ссылка на локацию: {loc_url}')

                            reviews_repo = ReviewRepository()
                            photos_repo = PhotoRepository()

                            self.create_new_location(
                                loc_name=loc_name,
                                loc_url=loc_url,
                                locations_repo=locations_repo,
                                reviews_repo=reviews_repo,
                                photos_repo=photos_repo
                            )

        except ProcessingError as e:
            logger.error(f"Ошибка обработки данных: {e}")
        except Exception as e:
            logger.exception(f"Неизвестная ошибка при обработке локаций: {e}")

    def extract_id_yandex(self, loc_url: str) -> Optional[int]:
        """
        Извлекает ID Yandex из URL локации.

        Args:
            loc_url (str): URL локации.

        Returns:
            Optional[int]: ID Yandex или None, если не найден.
        """
        try:
            id_yandex = [int(part) for part in loc_url.split('/') if part.isdigit()]
            if id_yandex:
                return id_yandex[0]
            return None
        except ValueError:
            logger.error(f"Не удалось извлечь ID Yandex из URL: {loc_url}")
            return None

    def update_existing_location(self, loc_serial: int, loc_url: str) -> None:
        """
        Обновляет существующую локацию, если типы отличаются.

        Args:
            loc_serial (int): Сериал ID локации.
            loc_url (str): URL локации.
            sql_city (str): Название города из базы данных.
        """
        try:
            locations_repo = LocationsRepository()
            types = self.parse_yandex.get_loc_only_type(url=loc_url)
            existing_types = locations_repo.get_json_value(
                model_class=Location,
                loc_serial = loc_serial,
                json_field='characters',
                key='types'
            )
            existing_types = eval(existing_types) if existing_types else []

            if set(types) != set(existing_types):
                new_types = list(set(types + existing_types))
                locations_repo._update_json_value(
                    model_class=Location,
                    name_id='id_location',
                    item_id=loc_serial,
                    json_field='characters',
                    new_value=new_types,
                    key='types'
                )
                logger.info(f'\t\t\tТипы локации {loc_serial} обновлены.')
            else:
                logger.info(f'\t\t\tТипы локации {loc_serial} совпадают. Пропускаем.')
        except Exception as e:
            logger.error(f'\t\t\tОшибка обновления локации {loc_serial}: {e}')

    def create_new_location(
        self,
        loc_name: str,
        loc_url: str,
        locations_repo: LocationsRepository,
        reviews_repo: ReviewRepository,
        photos_repo: PhotoRepository
    ) -> None:
        """
        Создает новую локацию и добавляет отзывы и фото в базу данных.

        Args:
            loc_name (str): Название локации.
            loc_url (str): URL локации.
            id_region (int): ID региона.
            id_city (int): ID города.
            locations_repo (LocationsRepo): Репозиторий для локаций.
            reviews_repo (ReviewRepo): Репозиторий для отзывов.
            photos_repo (PhotoRepo): Репозиторий для фото.
        """
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                self.parse_yandex.get_loc_type_td(url=loc_url)
                coordinates = self.parse_yandex.loc_info.get('coordinates', [None, None])
                id_region_city = self.parse_yandex.coordinates_address(lat=coordinates[1], lon=coordinates[0])
                if not id_region_city:
                    logger.warning (f'{loc_name} не совпал ни с чем из базы')
                    retries += 1                                   
                    continue
                self.parse_yandex.get_location_reviews_and_photos(loc_url=loc_url)
        
                locations_repo.load_info_loc_yandex(
                    location_name=loc_name, 
                    coordinates=coordinates, 
                    id_city=id_region_city[1] if len(id_region_city) == 2 else None,
                    id_region=id_region_city[0],
                    characters={k: v for k, v in self.parse_yandex.loc_info.items() if k != 'coordinates'}
                    )
                logger.info(f'Локация {loc_name} добавлена в базу данных.')

                # Получение ID добавленной локации
                id_loc = locations_repo.id_loc_yandex
                if not id_loc:
                    logger.error(f'Не удалось найти добавленную локацию {loc_name} в базе данных.')
                    return

                # Добавление отзывов
                for review in self.parse_yandex.loc_reviews.values():
                    reviews_repo.load_review_loc_yandex(
                        id_loc=id_loc,
                        like=int(review.get('like', 0)),
                        text=review.get('text', ''),
                        data=review.get('data', '')
                    )
                logger.info(f'{len(self.parse_yandex.loc_reviews)} отзыва для локации {loc_name} добавлены.')

                # Добавление фото
                for photo_url in self.parse_yandex.loc_photos.values():
                    photos_repo.load_photo_loc_yandex(
                        id_loc=id_loc,
                        url=photo_url
                    )
                logger.info(f'{len(self.parse_yandex.loc_photos)} фото для локации {loc_name} добавлены.')
                break

            except Exception as e:
                logger.error(f'Ошибка создания локации {loc_name}: {e}')
                retries += 1                                   


class WeatherProcessor:
    """Класс для обработки погодных данных."""

    def __init__(self) -> None:
        """Инициализирует WeatherProcessor."""
        self.parse_weather = ParseWeather()
        self.mv_repo = MetricValueRepository()

    def process_weather_data(self) -> None:
        """
        Собирает погодные данные для всех городов и загружает их в базу данных.
        """
        try:
            full_cities_data = self.parse_weather.get_all_temperature()
            for id_city, temperatures in full_cities_data.items():
                self.mv_repo.fill_weather(id_city, temperatures)
                logger.info(f'Погодные данные для города ID {id_city} загружены.')
            logger.info('Загрузка всех погодных данных завершена.')
        except Exception as e:
            logger.error(f"Ошибка при обработке погодных данных: {e}")
            raise ProcessingError(f"Ошибка обработки погодных данных: {e}") from e


class SyncProcessor:
    """Класс для синхронизации данных."""

    def __init__(self) -> None:
        """Инициализирует SyncProcessor."""
        self.sync_repo = SyncRepository()

    def sync_regions_and_cities(self, compare_regions: CompareRegions) -> None:
        """
        Синхронизирует регионы и города из внешнего источника с базой данных.

        Args:
            compare_regions (CompareRegions): Объект для сравнения регионов.
        """
        try:
            found_regions, not_found_regions = compare_regions.compare_regions_from_weather()
            self.sync_repo.fill(Region, 'weather', found_regions)
            logger.info(f"Синхронизировано {len(found_regions)} регионов.")
            logger.warning(f"Не найдены регионы: {not_found_regions}")
        except Exception as e:
            logger.error(f"Ошибка при синхронизации регионов и городов: {e}")
            raise ProcessingError(f"Ошибка синхронизации: {e}") from e
