
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.exc import NoResultFound

from app.logging_config import logger
from app.data.database import Database, manage_session, JSONRepository
from app.models import (
    Sync,
    Region,
    MetricValue,
    LocationType,
    Location,
    Photo,
    Review,
    City,
)


Base = declarative_base()
T = TypeVar("T", bound=DeclarativeMeta)

class SyncRepository(Database):
    """
    Репозиторий для работы с моделью Sync.
    """

    @manage_session
    def find_id(
        self, input_value: str, object_type: str, input_from: str
    ) -> Optional[int]:
        """
        Находит id_to по значениям input_value, object_type и input_from.

        Args:
            input_value (str): Входное значение.
            object_type (str): Тип объекта.
            input_from (str): Источник входных данных.

        Returns:
            Optional[int]: Найденный id_to или None.
        """
        sync_entry = (
            self.session.query(Sync)
            .filter(
                Sync.input_value == input_value,
                Sync.object_type == object_type,
                Sync.input_from == input_from,
            )
            .first()
        )
        logger.debug(f"Поиск Sync id_to: {sync_entry.id_to if sync_entry else None}")
        return sync_entry.id_to if sync_entry else None

    @manage_session
    def fill(
        self, model: Type[T], input_from: str, df: Dict[Any, Any]
    ) -> None:
        """
        Заполняет таблицу Sync на основе данных модели и DataFrame.

        Args:
            model (Type[Base]): Класс модели SQLAlchemy.
            input_from (str): Источник данных.
            df (Dict[Any, Any]): Данные для заполнения.
        """
        existing_records = self.get_all(model)
        logger.debug(f"Существующие записи в модели {model.__tablename__}: {len(existing_records)}")

        for row in existing_records:
            pk_name = model.__table__.primary_key.columns.keys()[0]
            pk_value = getattr(row, pk_name)
            if not self.get_by_fields(
                Sync, input_from=input_from, id_to=pk_value
            ):
                sync = Sync(
                    id_to=pk_value,
                    object_type=model.__table__.name,
                    input_from=input_from,
                )
                self.add(sync)
                logger.info(f"Добавлен Sync объект для id_to={pk_value}")

        for key, value in df.items():
            sync = Sync(
                input_value=key if isinstance(key, str) else key[0],
                id_to=value,
                input_from=input_from,
            )
            existing_sync = self.get_by_fields(
                Sync, input_from=input_from, id_to=value
            )
            if existing_sync:
                sync.id_sync = existing_sync[0].id_sync
                self.update(sync)
                logger.info(f"Обновлен Sync объект с id_sync={sync.id_sync}")
            else:
                self.add(sync)
                logger.info(f"Добавлен новый Sync объект с id_to={value}")



class RegionRepository(Database):
    """
    Репозиторий для работы с моделью Region.
    """

    @manage_session
    def find_region_by_id(self, id_region: int) -> Optional[Region]:
        """
        Находит регион по его идентификатору.

        Args:
            id_region (int): Идентификатор региона.

        Returns:
            Optional[Region]: Найденный регион или None.
        """
        region = (
            self.session.query(Region)
            .filter(Region.id_region == id_region)
            .first()
        )
        logger.debug(f"Найден регион с id_region={id_region}: {region is not None}")
        return region


class MetricValueRepository(Database):
    """
    Репозиторий для работы с моделью MetricValue.
    """

    def get_tourist_count_data(self) -> List[MetricValue]:
        """
        Получает данные туристического потока по регионам.

        Returns:
            List[MetricValue]: Список записей MetricValue.
        """
        records = (
            self.get_session()
            .query(
                MetricValue.id_region,
                MetricValue.value,
                MetricValue.month,
                MetricValue.year,
            )
            .filter(MetricValue.id_metric == 2)
            .all()
        )
        logger.debug(f"Получено {len(records)} записей туристического потока.")
        return records

    def get_tourist_count_data_by_region(
        self, region_id: int
    ) -> List[MetricValue]:
        """
        Получает данные туристического потока по конкретному региону.

        Args:
            region_id (int): Идентификатор региона.

        Returns:
            List[MetricValue]: Список записей MetricValue.
        """
        records = (
            self.get_session()
            .query(
                MetricValue.id_region,
                MetricValue.value,
                MetricValue.month,
                MetricValue.year,
            )
            .filter(
                MetricValue.id_metric == 2,
                MetricValue.id_region == region_id,
            )
            .all()
        )
        logger.debug(
            f"Получено {len(records)} записей туристического потока для региона {region_id}."
        )
        return records

    @manage_session
    def fill_weather(
        self, city_id: int, value: Dict[str, Dict[str, Union[int, float]]]
    ) -> None:
        """
        Загружает погодные данные в таблицу MetricValue.

        Args:
            city_id (int): Идентификатор города.
            value (Dict[str, Dict[str, Union[int, float]]]): Погодные данные.
        """
        ratio = {
            "day": 213,
            "night": 214,
            "rainfall": 215,
            "water": 216,
        }
        for month, temperatures in value.items():
            for d_n_r_w, number in temperatures.items():
                metric_id = ratio.get(d_n_r_w)
                if not metric_id:
                    logger.warning(f"Неизвестный тип метрики: {d_n_r_w}")
                    continue

                mv = MetricValue(
                    id_city=city_id,
                    id_metric=metric_id,
                    value=str(number),
                    month=month,
                    year=2023,
                )
                existing_mv = self.get_by_fields(
                    MetricValue,
                    id_city=city_id,
                    id_metric=metric_id,
                    value=str(number),
                    month=month,
                    year=2023,
                )
                if existing_mv:
                    mv.id_mv = existing_mv[0].id_mv
                    self.update(mv)
                    logger.info(
                        f"Обновлен параметр {metric_id} для города {city_id}."
                    )
                else:
                    self.add(mv)
                    logger.info(
                        f"Добавлен параметр {metric_id} для города {city_id}."
                    )
        logger.info(f"Обработка города {city_id} завершена.")


class LocationTypeRepository(Database):
    """
    Репозиторий для работы с моделью LocationType.
    """

    @manage_session
    def load_locations_yandex(self, locations_data: List[Dict[str, Any]]) -> None:
        """
        Загружает типы локаций для Яндекс Карт из предоставленных данных.

        Args:
            locations_data (List[Dict[str, Any]]): Список словарей с данными типов локаций.
        """
        logger.info(f"Начало загрузки типов локаций в базу данных. Количество записей: {len(locations_data)}")
        try:
            for row in locations_data:
                lt = LocationType(
                    location_type_value="yandex",
                    name=row["name_loc"],
                    general=row["type_loc"],
                )
                filters = {
                    "location_type_value": "yandex",
                    "name": row["name_loc"],
                    "general": row["type_loc"],
                }
                existing_lt = self.get_by_fields(LocationType, **filters)
                if existing_lt:
                    lt.id_location_type = existing_lt[0].id_location_type
                    self.update(lt)
                    logger.info(f"Обновлен тип локации: {row['name_loc']}")
                else:
                    self.add(lt)
                    logger.info(f"Добавлен тип локации: {row['name_loc']}")
            logger.info("Загрузка типов локаций завершена успешно.")
        except Exception as e:
            logger.exception(f"Ошибка при загрузке типов локаций: {e}")
            raise

class LocationsRepository(JSONRepository):
    """
    Репозиторий для работы с моделью Location.
    """

    def __init__(self):
        super().__init__()
        self.model = Location
        logger.info("Инициализирован LocationsRepository.")

    @manage_session
    def check_loc_yandex(
        self, location_name: str, coordinates: list
    ) -> Optional[Location]:
        """
        Проверяет наличие локации в базе данных для Яндекс.

        Args:
            location_name (str): Название локации.
            coordinates (list): координаты локации
        Returns:
            Optional[Location]: Найденная локация или None.
        """
        coordinates = f"SRID=4326;POINT({coordinates[0]} {coordinates[1]})" if all(coordinates) else "NULL"
        filters = {
            "location_name": location_name,
            "coordinates": coordinates
        }
        location = self.get_by_fields(Location, **filters)
        logger.debug(
            f"Проверка существования локации '{location_name}' по координатам {coordinates}: {bool(location)}"
        )
        return location[0] if location else None

    @manage_session
    def load_info_loc_yandex(
        self,
        location_name: str,
        coordinates: str,
        id_city: int,
        id_region: int,
        characters: Dict[str, Any],
    ) -> None:
        """
        Загружает информацию о локации Яндекс в базу данных.

        Args:
            location_name (str): Название локации.
            coordinates (str): Координаты локации.
            id_city (int): Идентификатор города.
            id_region (int): Идентификатор региона.
            characters (Dict[str, Any]): Характеристики локации.
        """
        coordinates_str = f"SRID=4326;POINT({coordinates[0]} {coordinates[1]})" if all(coordinates) else "NULL"
        location = Location(
            location_name=location_name,
            coordinates=coordinates_str,
            id_city=id_city,
            id_region=id_region,
            characters=characters,
        )
        self.add(location)
        existing_location = self.check_loc_yandex(
            location_name = location_name,
            coordinates = coordinates
        )
        if existing_location:
            self.id_loc_yandex = existing_location.id_location
            logger.info(
                f"Загружена локация Яндекс: {location_name}, id_location={self.id_loc_yandex}"
            )
        else:
            logger.error(f"Не удалось загрузить локацию Яндекс: {location_name}")


class ReviewRepository(Database):
    """
    Репозиторий для работы с моделью Review.
    """

    @manage_session
    def load_review_loc_yandex(
        self, id_loc: int, like: int, text: str, data: str
    ) -> None:
        """
        Загружает отзыв и оценку для локации Яндекс.

        Args:
            id_loc (int): Идентификатор локации.
            like (int): Количество лайков.
            text (str): Текст отзыва.
            data (str): Дата отзыва.
        """
        review = Review(
            id_location=id_loc,
            like=like,
            text=text,
            data=data,
        )
        self.add(review)
        logger.debug(f"Загружен отзыв для локации {id_loc}.")


class PhotoRepository(Database):
    """
    Репозиторий для работы с моделью Photo.
    """

    @manage_session
    def load_photo_loc_yandex(self, id_loc: int, url: str) -> None:
        """
        Загружает URL фотографии для локации Яндекс.

        Args:
            id_loc (int): Идентификатор локации.
            url (str): URL фотографии.
        """
        photo = Photo(
            id_location=id_loc,
            url=url,
        )
        self.add(photo)
        logger.debug(f"Загружена фотография для локации {id_loc}: {url}")


class CitiesRepository(JSONRepository):
    """
    Репозиторий для работы с моделью City.
    """

    @manage_session
    def check_type_loc(self, id_city: int, first_type: str) -> str:
        """
        Проверяет наличие 'last_type_loc' у города. Если отсутствует, добавляет его.

        Args:
            id_city (int): Идентификатор города.
            first_type (str): Начальный тип локации.

        Returns:
            str: Значение 'last_type_loc'.
        """
        while True:
            city_records = self.get_by_fields(City, id_city=id_city)
            if not city_records:
                logger.error(f"Город с id_city={id_city} не найден.")
                raise NoResultFound(f"Город с id_city={id_city} не найден.")

            city = city_records[0]
            characters = city.characters or {}
            if "last_type_loc" not in characters:
                characters["last_type_loc"] = first_type
                city.characters = characters
                self.update(city)
                logger.info(
                    f"Добавлено 'last_type_loc'='{first_type}' для города id={id_city}."
                )
                continue
            else:
                logger.debug(
                    f"'last_type_loc' для города id={id_city}: {characters['last_type_loc']}"
                )
                return characters["last_type_loc"]

    @manage_session
    def load_next_type_loc(self, id_city: int, type_loc: int) -> None:
        """
        Загружает новый тип локации для города.

        Args:
            id_city (int): Идентификатор города.
            type_loc (str): Новый тип локации.
        """
        city_records = self.get_by_fields(City, id_city=id_city)
        if not city_records:
            logger.error(f"Город с id_city={id_city} не найден.")
            raise NoResultFound(f"Город с id_city={id_city} не найден.")

        city = city_records[0]
        characters = city.characters or {}
        characters["last_type_loc"] = f'{type_loc}'
        city.characters = characters
        self.update(city)
        logger.info(
            f"Обновлен 'last_type_loc'='{type_loc}' для города id={id_city}."
        )
