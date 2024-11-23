#app\data\database\base_repository.py

import time
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, Column
from sqlalchemy.exc import  OperationalError, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import inspect

from app.config import Config_SQL
from app.logging_config import logger

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
        self.engine = create_engine(Config_SQL.SQLALCHEMY_DATABASE_URI)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()
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
    def get_all(self, model: Type[T]) -> List[T]:
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
        try:
            self.session.delete(obj)
            self.session.commit()
            logger.info(f"Удален объект: {obj}")
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении объекта {obj}: {e}")
            raise      
        

    def get_engine(self) -> Any:
        """
        Возвращает SQLAlchemy Engine.

        Returns:
            Engine: Экземпляр SQLAlchemy Engine.
        """
        return self.engine
    
    def _get_pk_fields(self, model: Type[T]) -> List[Column]:
        """
        Возвращает список столбцов, являющихся первичными ключами модели.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.

        Returns:
            List[Column]: Список столбцов первичных ключей.
        """
        return [column for column in inspect(model).mapper.columns if column.primary_key]

    @manage_session
    def find_by_primary_key(
        self, model: Type[T], pk_values: Dict[str, Any]
    ) -> Optional[T]:
        """
        Находит запись по первичным ключам.

        Args:
            model (Type[T]): Класс модели SQLAlchemy.
            pk_values (Dict[str, Any]): Словарь с названиями столбцов первичных ключей и их значениями.

        Returns:
            Optional[T]: Найденная запись или None.
        """
        pk_columns = self._get_pk_fields(model)

        if not pk_columns:
            raise ValueError(f"Модель {model.__name__} не имеет первичных ключей.")

        if len(pk_columns) != len(pk_values):
            raise ValueError(
                f"Модель {model.__name__} ожидает {len(pk_columns)} первичных ключей, "
                f"получено {len(pk_values)}."
            )

        # Создаем фильтры для запроса
        filters = []
        for column in pk_columns:
            column_name = column.name
            if column_name not in pk_values:
                raise ValueError(f"Отсутствует значение для первичного ключа '{column_name}'.")
            filters.append(getattr(model, column_name) == pk_values[column_name])

        # Выполняем запрос
        record = self.session.query(model).filter(*filters).first()
        logger.debug(
            f"Поиск по PK - модель: {model.__tablename__}, PK Values: {pk_values}. Найдено: {record is not None}"
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

    @staticmethod
    def to_dict(obj: Type[T]) -> Dict[str, Any]:
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
                logger.debug(f"Объект добавлен в сессию: {obj}")
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