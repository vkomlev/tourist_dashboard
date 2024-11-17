# app/data/database.py

import time
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import NoResultFound, OperationalError, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from sqlalchemy import inspect

from app.config import Config, YANDEX_LOCATION
from app.logging_config import logger
from app.models import (
    Sync,
    Region,
    MetricValue,
    LocationType,
    Location,
    Photo,
    Rewiew,
    City,
)
from app.data.imports.import_xls import load_yandex_locations  # Импортируем функцию загрузки

Base = declarative_base()
T = TypeVar("T", bound=DeclarativeMeta)


def retry_on_failure(retries: int = 5, delay: int = 2):
    """
    Декоратор для повторных попыток при сбоях подключения.

    Args:
        retries (int): Количество повторных попыток. По умолчанию 5.
        delay (int): Задержка между попытками в секундах. По умолчанию 2.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    attempts += 1
                    logger.warning(f"Попытка {attempts} из {retries} не удалась: {e}")
                    if attempts < retries:
                        logger.info(f"Повтор через {delay} секунд...")
                        time.sleep(delay)
                    else:
                        logger.error("Все попытки исчерпаны.")
                        raise

        return wrapper

    return decorator


def manage_session(func):
    """
    Декоратор для автоматического управления сессией SQLAlchemy.

    Открывает сессию перед вызовом функции и закрывает после завершения.
    В случае ошибки откатывает транзакцию.

    Args:
        func (Callable): Функция, для которой применяется декоратор.
    """

    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            return result
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка в методе {func.__name__}: {e}")
            raise
        finally:
            self.session.close()
            logger.debug("Сессия закрыта.")

    return wrapper


class Database:
    """
    Класс для управления подключением к базе данных и выполнением операций.

    Атрибуты:
        engine (Engine): Экземпляр SQLAlchemy Engine.
        SessionLocal (sessionmaker): Конфигурированный sessionmaker.
    """

    def __init__(self):
        self.engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Создан SQLAlchemy Engine и sessionmaker.")

    def create_tables(self) -> None:
        """
        Создает все таблицы, определенные в моделях.
        """
        Base.metadata.create_all(self.engine)
        logger.info("Таблицы успешно созданы.")

    def drop_tables(self) -> None:
        """
        Удаляет все таблицы, определенные в моделях.
        """
        Base.metadata.drop_all(self.engine)
        logger.info("Таблицы успешно удалены.")

    def get_session(self) -> Session:
        """
        Возвращает новую сессию базы данных.

        Returns:
            Session: Экземпляр сессии SQLAlchemy.
        """
        return self.SessionLocal()

    @manage_session
    def add(self, obj: Type[T]) -> T:
        """
        Добавляет объект в базу данных и сохраняет изменения.

        Args:
            obj (Base): Объект модели SQLAlchemy.

        Returns:
            Base: Добавленный объект.
        """
        self.session.add(obj)
        self.session.commit()
        logger.info(f"Добавлен объект: {obj}")
        return obj

    @manage_session
    def add_all(self, objs: List[T]) -> None:
        """
        Добавляет несколько объектов в базу данных и сохраняет изменения.

        Args:
            objs (List[Base]): Список объектов моделей SQLAlchemy.
        """
        self.session.add_all(objs)
        self.session.commit()
        logger.info(f"Добавлено {len(objs)} объектов.")

    @manage_session
    def query_all(self, model: Type[T]) -> List[T]:
        """
        Возвращает все записи из указанной модели.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.

        Returns:
            List[T]: Список записей модели.
        """
        results = self.session.query(model).all()
        logger.debug(f"Запрошено {len(results)} записей из {model.__tablename__}.")
        return results

    @manage_session
    def delete(self, obj: Type[T]) -> None:
        """
        Удаляет объект из базы данных и сохраняет изменения.

        Args:
            obj (Base): Объект модели SQLAlchemy.
        """
        self.session.delete(obj)
        self.session.commit()
        logger.info(f"Удален объект: {obj}")

    def get_engine(self) -> Any:
        """
        Возвращает SQLAlchemy Engine.

        Returns:
            Engine: Экземпляр SQLAlchemy Engine.
        """
        return self.engine

    @manage_session
    def find_by_primary_key(
        self, model: Type[T], pk_column: str, pk_value: Any
    ) -> Optional[T]:
        """
        Находит запись по первичному ключу.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.
            pk_column (str): Название столбца первичного ключа.
            pk_value (Any): Значение первичного ключа.

        Returns:
            Optional[T]: Найденная запись или None.
        """
        record = (
            self.session.query(model)
            .filter(getattr(model, pk_column) == pk_value)
            .first()
        )
        logger.debug(
            f"Поиск по PK - модель: {model.__tablename__}, {pk_column}: {pk_value}. Найдено: {record is not None}"
        )
        return record

    @manage_session
    def find_by_name(
        self, model: Type[T], name_column: str, name_value: Any
    ) -> List[T]:
        """
        Находит записи по значению указанного столбца.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.
            name_column (str): Название столбца.
            name_value (Any): Значение для фильтрации.

        Returns:
            List[T]: Список найденных записей.
        """
        records = (
            self.session.query(model)
            .filter(getattr(model, name_column) == name_value)
            .all()
        )
        logger.debug(
            f"Поиск по имени - модель: {model.__tablename__}, {name_column}: {name_value}. Найдено: {len(records)}"
        )
        return records

    @manage_session
    def get_all(self, model: Type[T]) -> List[T]:
        """
        Возвращает все записи из указанной модели.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.

        Returns:
            List[T]: Список записей модели.
        """
        records = self.session.query(model).all()
        logger.debug(f"Получено {len(records)} записей из {model.__tablename__}.")
        return records

    @classmethod
    def to_dict(cls, obj: Type[T]) -> Dict[str, Any]:
        """
        Преобразует объект модели в словарь.

        Args:
            obj (Base): Объект модели SQLAlchemy.

        Returns:
            Dict[str, Any]: Словарь с данными объекта.
        """
        record = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
        logger.debug(f"Преобразование объекта в словарь: {record}")
        return record

    @manage_session
    def get_by_fields(self, model: Type[T], **kwargs) -> List[T]:
        """
        Получает записи по значениям полей, переданным через kwargs.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.
            **kwargs: Пары ключ-значение для фильтрации.

        Returns:
            List[T]: Список найденных записей.
        """
        query = self.session.query(model)
        for key, value in kwargs.items():
            query = query.filter(getattr(model, key) == value)
        results = query.all()
        logger.debug(
            f"Получено {len(results)} записей из {model.__tablename__} по фильтрам {kwargs}."
        )
        return results

    @manage_session
    def update(self, obj: Type[T]) -> None:
        """
        Обновляет запись в базе данных.

        Args:
            obj (Base): Объект модели SQLAlchemy.
        """
        try:
            if not self.session.object_session(obj):
                self.session.merge(obj)
                logger.debug(f"Объект объединен в сессию: {obj}")
            self.session.commit()
            logger.info(f"Обновлен объект: {obj}")
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении объекта {obj}: {e}")
            raise

    @staticmethod
    def get_model_by_tablename(tablename: str) -> Optional[Type[T]]:
        """
        Возвращает класс модели по названию таблицы.

        Args:
            tablename (str): Название таблицы.

        Returns:
            Optional[Type[Base]]: Класс модели или None.
        """
        for class_obj in Base.registry._class_registry.values():
            if hasattr(class_obj, '__tablename__') and class_obj.__tablename__ == tablename:
                logger.debug(f"Найден класс модели для таблицы {tablename}: {class_obj.__name__}")
                return class_obj
        logger.warning(f"Модель для таблицы {tablename} не найдена.")
        return None



class JSONRepository(Database):
    """
    Базовый класс для манипуляций с объектами БД, содержащими JSONB поля.
    """

    @manage_session
    def update_json_fields(
        self,
        model_instance: Type[T],
        field_name: str = "characteristics",
        json_field: Dict[str, Any] = {},
    ) -> None:
        """
        Обновляет пары JSON в указанном поле модели.

        Args:
            model_instance (Base): Экземпляр модели SQLAlchemy.
            field_name (str, optional): Название JSON поля. По умолчанию 'characteristics'.
            json_field (Dict[str, Any], optional): Пары ключ-значение для обновления.
        """
        if not json_field:
            logger.debug("Нет данных для обновления JSON полей.")
            return

        for key, value in json_field.items():
            wrapped_value = self._wrap_json_value(value)
            self._update_json_value(
                model_instance.__class__,
                model_instance.id,
                field_name,
                f"{{{key}}}",
                wrapped_value,
            )
            logger.debug(
                f"Обновлено JSON поле {field_name} для записи {model_instance.id}: {key} = {wrapped_value}"
            )

    def _update_json_value(
        self,
        model_class: Type[T],
        name_id: Any,
        json_field: str,
        key_path: str,
        new_value: str,
        operation: str = "replace",
    ) -> None:
        """
        Обновляет значение JSONB поля в базе данных.

        Args:
            model_class (Type[Base]): Класс модели SQLAlchemy.
            name_id (Any): Значение идентификатора записи.
            json_field (str): Название JSON поля.
            key_path (str): Путь к ключу JSON.
            new_value (str): Новое значение для ключа.
            operation (str, optional): Тип операции ('replace', 'append', 'remove'). По умолчанию 'replace'.

        Raises:
            ValueError: Если операция не поддерживается.
        """
        operations = {
            "replace": f"jsonb_set({json_field}, :key_path, :new_value)",
            "append": f"jsonb_set({json_field}, :key_path, ({json_field} #> :key_path) || :new_value)",
            "remove": f"jsonb_set({json_field}, :key_path, ({json_field} #> :key_path) - :new_value)",
        }

        if operation not in operations:
            logger.error(f"Unsupported operation: {operation}")
            raise ValueError("Unsupported operation. Use 'replace', 'append', or 'remove'.")

        sql_expression = text(
            f"UPDATE {model_class.__tablename__} SET {json_field} = {operations[operation]} WHERE id = :item_id"
        )

        try:
            session = self.get_session()
            session.execute(
                sql_expression,
                {"item_id": name_id, "key_path": key_path, "new_value": new_value},
            )
            session.commit()
            logger.debug(
                f"Выполнена операция '{operation}' на {json_field} для id={name_id}."
            )
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при обновлении JSON поля: {e}")
            raise

    @manage_session
    def delete_json_pair(
        self,
        model_class: Type[T],
        item_id: Any,
        json_field: str = "characteristics",
        key: str = "",
    ) -> None:
        """
        Удаляет пару ключ-значение из JSONB поля в базе данных.

        Args:
            model_class (Type[Base]): Класс модели SQLAlchemy.
            item_id (Any): Идентификатор записи.
            json_field (str, optional): Название JSON поля. По умолчанию 'characteristics'.
            key (str, optional): Ключ для удаления. По умолчанию ''.
        """
        if not key:
            logger.warning("Ключ для удаления JSON пары не указан.")
            return

        sql_expression = text(
            f"UPDATE {model_class.__tablename__} SET {json_field} = {json_field} - :key_path WHERE id = :item_id"
        )

        try:
            self.session.execute(
                sql_expression, {"item_id": item_id, "key_path": f"{{{key}}}"}
            )
            self.session.commit()
            logger.info(f"Удалена JSON пара '{key}' из {json_field} для id={item_id}.")
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Ошибка при удалении JSON пары: {e}")
            raise

    def _wrap_json_value(self, value: Any) -> str:
        """
        Оборачивает значение в зависимости от типа данных для JSON.

        Args:
            value (Any): Значение для оборачивания.

        Returns:
            str: Обработанное значение.
        """
        if isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, list):
            wrapped_values = [self._wrap_json_value(v) for v in value]
            return f"[{', '.join(wrapped_values)}]"
        elif value is None:
            return "null"
        else:
            logger.warning(f"Неизвестный тип данных для JSON: {type(value)}")
            return f'"{str(value)}"'

    @manage_session
    def get_json_value(
        self,
        model_class: Type[T],
        serial_id: str,
        item_id: Any,
        json_field: str,
        key: str,
    ) -> Optional[str]:
        """
        Получает значение из JSON поля по ключу.

        Args:
            model_class (Type[Base]): Класс модели SQLAlchemy.
            serial_id (str): Название столбца идентификатора.
            item_id (Any): Идентификатор записи.
            json_field (str): Название JSON поля.
            key (str): Ключ для получения значения.

        Returns:
            Optional[str]: Значение по ключу или None.
        """
        sql_expression = text(
            f"SELECT {json_field}->> :key_path FROM {model_class.__tablename__} WHERE {serial_id} = :item_id"
        )
        try:
            session = self.get_session()
            result = session.execute(
                sql_expression, {"item_id": item_id, "key_path": f"{{{key}}}"}
            ).scalar()
            logger.debug(
                f"Получено значение '{result}' для ключа '{key}' из {json_field}."
            )
            return result
        except NoResultFound:
            logger.warning(
                f"Запись с {serial_id}={item_id} не найдена для получения JSON значения."
            )
            return None

    @manage_session
    def _update_existing_record(
        self, existing_record: Type[T], data: Dict[str, Any], keep_existing: bool = False
    ) -> None:
        """
        Обновляет существующую запись новыми данными.

        Args:
            existing_record (Base): Существующая запись.
            data (Dict[str, Any]): Новые данные для обновления.
            keep_existing (bool, optional): Флаг сохранения существующих данных. По умолчанию False.
        """
        table_columns = inspect(existing_record.__class__).columns
        for column in table_columns:
            column_name = column.name
            if column_name in data and isinstance(column.type, JSONB):
                column_data = getattr(existing_record, column_name, {})
                new_data = data.get(column_name, {})
                if not keep_existing:
                    column_data.update(new_data)
                else:
                    column_data = {**new_data, **column_data}
                setattr(existing_record, column_name, column_data)
                logger.debug(
                    f"Обновлено JSON поле '{column_name}' для записи id={existing_record.id}."
                )
            elif column_name in data:
                if not (keep_existing and getattr(existing_record, column_name)):
                    setattr(existing_record, column_name, data[column_name])
                    logger.debug(
                        f"Обновлено поле '{column_name}' для записи id={existing_record.id}."
                    )
        self.update(existing_record)

    @manage_session
    def _add_new_record(
        self, data: Dict[str, Any], table_name: str
    ) -> None:
        """
        Добавляет новую запись в базу данных, если она не существует.

        Args:
            data (Dict[str, Any]): Данные для создания новой записи.
            table_name (str): Название таблицы.
        """
        record = data.copy()
        record.pop("table_to_load", None)
        record.pop("source_id", None)

        model_class = self.get_model_by_tablename(table_name)
        if not model_class:
            logger.error(f"Модель для таблицы '{table_name}' не найдена.")
            return

        valid_keys = [
            key for key in record.keys() if key in model_class.__table__.columns
        ]
        new_record = model_class(**{key: record[key] for key in valid_keys})
        self.add(new_record)
        logger.info(f"Добавлена новая запись в таблицу '{table_name}': {new_record}")

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
        self, id_region: int, id_city: int, location_name: str
    ) -> Optional[Location]:
        """
        Проверяет наличие локации в базе данных для Яндекс.

        Args:
            id_region (int): Идентификатор региона.
            id_city (int): Идентификатор города.
            location_name (str): Название локации.

        Returns:
            Optional[Location]: Найденная локация или None.
        """
        filters = {
            "id_region": id_region,
            "id_city": id_city,
            "location_name": location_name,
        }
        location = self.get_by_fields(Location, **filters)
        logger.debug(
            f"Проверка существования локации '{location_name}' в регионе {id_region}, городе {id_city}: {bool(location)}"
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
        location = Location(
            location_name=location_name,
            coordinates=coordinates,
            id_city=id_city,
            id_region=id_region,
            characters=characters,
        )
        self.add(location)
        existing_location = self.check_loc_yandex(
            id_region, id_city, location_name
        )
        if existing_location:
            self.id_loc_yandex = existing_location.id_location
            logger.info(
                f"Загружена локация Яндекс: {location_name}, id_location={self.id_loc_yandex}"
            )
        else:
            logger.error(f"Не удалось загрузить локацию Яндекс: {location_name}")


class RewiewRepository(Database):
    """
    Репозиторий для работы с моделью Rewiew.
    """

    @manage_session
    def load_rewiew_loc_yandex(
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
        rewiew = Rewiew(
            id_location=id_loc,
            like=like,
            text=text,
            data=data,
        )
        self.add(rewiew)
        logger.info(f"Загружен отзыв для локации {id_loc}.")


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
        logger.info(f"Загружена фотография для локации {id_loc}: {url}")


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
    def load_next_type_loc(self, id_city: int, type_loc: str) -> None:
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
        characters["last_type_loc"] = type_loc
        city.characters = characters
        self.update(city)
        logger.info(
            f"Обновлен 'last_type_loc'='{type_loc}' для города id={id_city}."
        )
