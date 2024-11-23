# app\data\database\json_repository.py

from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import text
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect

from app.data.database import Database, manage_session
from app.logging_config import logger



Base = declarative_base()
T = TypeVar("T", bound=DeclarativeMeta)

class JSONRepository(Database):
    """
    Базовый класс для манипуляций с объектами БД, содержащими JSONB поля.
    """

    @manage_session
    def update_json_fields(
        self,
        model_instance: Type[T],
        key_value: Any,
        field_name: str = "characters",
        json_field: Dict[str, Any] | List = {},
        operation: str = "replace",
    ) -> None:
        """
        Обновляет пары JSON в указанном поле модели.

        Args:
            model_instance (Base): Экземпляр модели SQLAlchemy.
            key_value (Any): Значение первичного ключа записи.
            field_name (str, optional): Название JSON поля. По умолчанию 'characters'.
            json_field (Dict[str, Any], optional): Пары ключ-значение для обновления.
            operation (str, optional): Тип операции ('replace', 'append', 'remove'). По умолчанию 'replace'.
        """
        if not json_field:
            logger.debug("Нет данных для обновления JSON полей.")
            return
        pk_column = self._get_pk_fields(model_instance.__class__)[0].name
        existing_record = self.find_by_primary_key(model_instance.__class__, {pk_column: key_value})
        old_value = getattr(existing_record, field_name, {})
        if not old_value:
            old_value = {}
        if operation not in ['replace', 'append', 'remove']:
            logger.error(f"Unsupported operation: {operation}")
            raise ValueError("Unsupported operation. Use 'replace', 'append', or 'remove'.")
        
        if operation == "replace":
            new_value = old_value | json_field
        elif operation == "append":
            new_value = json_field | old_value
        
        if operation == "remove":
            try:
                for key in json_field:
                    self.delete_json_pair(model_instance.__class__, key_value, field_name, key)
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при удалении пары JSON: {e}")
                raise
            return
        else:
            try:
                table_columns = inspect(existing_record.__class__).columns
                for column in table_columns:
                    column_name = column.name
                    if column_name == field_name and isinstance(column.type, JSONB):
                        setattr(existing_record, column_name, new_value)
                        self.update(existing_record)
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при обновлении JSON поля: {e}")
                raise
            return


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
        pk_column = self._get_pk_fields(model_class)[0].name
        sql_expression = text(
            f"UPDATE {model_class.__tablename__} SET {json_field} = {json_field} - :key_path WHERE {pk_column} = :item_id"
        )
        params = {"item_id": item_id, "key_path": f'{key}'}
        logger.debug(f'SQL удаления: {sql_expression}')
        logger.debug(f"Параметры: {params}")
        try:
            self.session.execute(
                sql_expression, params
            )
            self.session.commit()
            logger.info(f"Удалена JSON пара '{key}' из {json_field} для {pk_column}={item_id}.")
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Ошибка при удалении JSON пары: {e}")
            raise

    @manage_session
    def get_json_value(
        self,
        model_class: Type[T],
        loc_serial: Any,
        json_field: str,
        key: str,
    ) -> Optional[str]:
        """
        Получает значение из JSON поля по ключу.

        Args:
            model_class (Type[Base]): Класс модели SQLAlchemy.
            item_id (Any): Идентификатор записи.
            json_field (str): Название JSON поля.
            key (str): Ключ для получения значения.

        Returns:
            Optional[str]: Значение по ключу или None.
        """
        pk_column = self._get_pk_fields(model_class)[0].name
        sql_expression = text(
            f"SELECT {json_field}->> :key_path FROM {model_class.__tablename__} WHERE {pk_column} = :loc_serial"
        )
        try:
            session = self.get_session()
            params = {"loc_serial": loc_serial, "key_path": f"{key}"}
            logger.debug(f'SQL получения: {sql_expression}')
            logger.debug(f"Параметры: {params}")
            result = session.execute(sql_expression, params).scalar()
            logger.debug(
                f"Получено значение '{result}' для ключа '{key}' из {json_field}."
            )
            return result
        except NoResultFound:
            logger.warning(
                f"Запись с {pk_column}={loc_serial} не найдена для получения JSON значения."
            )
            return None