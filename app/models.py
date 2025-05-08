# app/models.py

import logging
from typing import Optional, List

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    JSON,
    SmallInteger,
    ForeignKey,
    Sequence,
    text,
    DateTime
)
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from geoalchemy2 import Geometry  # For storing geometric data types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped

from app.config import Config_SQL
from app.logging_config import logger


Base = declarative_base()
metadata = Base.metadata


class Region(Base):
    """Таблица регионов."""

    __tablename__ = 'regions'

    id_region: int = Column(
        Integer,
        Sequence('regions_id_region_seq'),
        primary_key=True,
        doc='Уникальный идентификатор региона',
    )
    region_name: str = Column(
        String,
        nullable=False,
        doc='Название региона',
    )
    capital: Optional[int] = Column(
        Integer,
        ForeignKey('cities.id_city', ondelete='CASCADE'),
        doc='Идентификатор столицы региона',
    )
    coordinates: Optional[str] = Column(
        Geometry('POINT', srid=4326),
        doc='Координаты региона',
    )
    description: Optional[str] = Column(
        Text,
        doc='Описание региона',
    )
    characters: Optional[dict] = Column(
        JSONB,
        doc='Характеристики региона в формате JSON',
    )

    cities: List['City'] = relationship(
        'City',
        back_populates='region',
        foreign_keys='City.id_region',
        doc='Связанные города региона',
    )
    capital_city: Optional['City'] = relationship(
        'City',
        foreign_keys=[capital],
        doc='Столица региона',
    )
    locations: List['Location'] = relationship(
        'Location',
        back_populates='region',
        doc='Локации региона',
    )
    metric_values: List['MetricValue'] = relationship(
        'MetricValue',
        back_populates='region',
        doc='Значения метрик региона',
    )

    def __repr__(self):
        return (f"<Region(id_region={self.id_region}, region_name='{self.region_name}', "
                f"capital={self.capital})>")

    def __str__(self):
        return f"Регион: {self.region_name} (ID: {self.id_region})"

class City(Base):
    """Таблица городов."""

    __tablename__ = 'cities'

    id_city: int = Column(
        Integer,
        Sequence('cities_id_city_seq'),
        primary_key=True,
        doc='Уникальный идентификатор города',
    )
    city_name: str = Column(
        String,
        nullable=False,
        doc='Название города',
    )
    id_region: int = Column(
        Integer,
        ForeignKey('regions.id_region', ondelete='CASCADE'),
        doc='Идентификатор региона, к которому принадлежит город',
    )
    coordinates: Optional[str] = Column(
        Geometry('POINT', srid=4326),
        doc='Координаты города',
    )
    description: Optional[str] = Column(
        Text,
        doc='Описание города',
    )
    characters: Optional[dict] = Column(
        JSONB,
        doc='Характеристики города в формате JSON',
    )

    region: 'Region' = relationship(
        'Region',
        back_populates='cities',
        foreign_keys=[id_region],
        doc='Регион, к которому принадлежит город',
    )
    locations: List['Location'] = relationship(
        'Location',
        back_populates='city',
        doc='Локации города',
    )
    metric_values: List['MetricValue'] = relationship(
        'MetricValue',
        back_populates='city',
        doc='Значения метрик города',
    )

    def __repr__(self):
        return (f"<City(id_city={self.id_city}, city_name='{self.city_name}', "
                f"id_region={self.id_region})>")

    def __str__(self):
        return f"Город: {self.city_name} (ID: {self.id_city})"

class LocationType(Base):
    """Таблица типов локаций."""

    __tablename__ = 'location_type'

    id_location_type: int = Column(
        Integer,
        Sequence('location_type_id_location_type_seq'),
        primary_key=True,
        doc='Уникальный идентификатор типа локации',
    )
    location_type_value: str = Column(
        String,
        nullable=False,
        doc='Значение типа локации',
    )
    description: Optional[str] = Column(
        Text,
        doc='Описание типа локации',
    )
    location_type_key: Optional[str] = Column(
        String,
        doc='Ключ типа локации',
    )
    name: Optional[str] = Column(
        String,
        doc='Название типа локации',
    )
    general: Optional[str] = Column(
        String,
        doc='Общее описание типа локации',
    )

    locations: List['Location'] = relationship(
        'Location',
        back_populates='location_type',
        doc='Локации данного типа',
    )

    def __repr__(self):
        return (f"<LocationType(id_location_type={self.id_location_type}, "
                f"location_type_value='{self.location_type_value}', name='{self.name}')>")

    def __str__(self):
        return f"Тип локации: {self.name} (ID: {self.id_location_type})"


class Location(Base):
    """Таблица локаций."""

    __tablename__ = 'locations'

    id_location: int = Column(
        Integer,
        Sequence('locations_id_location_seq'),
        primary_key=True,
        doc='Уникальный идентификатор локации',
    )
    location_name: Optional[str] = Column(
        String,
        doc='Название локации',
    )
    description: Optional[str] = Column(
        Text,
        doc='Описание локации',
    )
    coordinates: Optional[str] = Column(
        Geometry('POINT', srid=4326),
        doc='Координаты локации',
    )
    id_city: Optional[int] = Column(
        Integer,
        ForeignKey('cities.id_city', ondelete='RESTRICT'),
        doc='Идентификатор города, к которому принадлежит локация',
    )
    id_region: Optional[int] = Column(
        Integer,
        ForeignKey('regions.id_region', ondelete='RESTRICT'),
        doc='Идентификатор региона, к которому принадлежит локация',
    )
    characters: Optional[dict] = Column(
        JSONB,
        doc='Характеристики локации в формате JSON',
    )
    id_location_type: Optional[int] = Column(
        Integer,
        ForeignKey('location_type.id_location_type', ondelete='RESTRICT'),
        doc='Идентификатор типа локации',
    )

    city: Optional['City'] = relationship(
        'City',
        back_populates='locations',
        doc='Город, к которому принадлежит локация',
    )
    region: Optional['Region'] = relationship(
        'Region',
        back_populates='locations',
        doc='Регион, к которому принадлежит локация',
    )
    location_type: Optional['LocationType'] = relationship(
        'LocationType',
        back_populates='locations',
        doc='Тип локации',
    )
    metric_values: List['MetricValue'] = relationship(
        'MetricValue',
        back_populates='location',
        doc='Значения метрик локации',
    )
    def __repr__(self):
        return (f"<Location(id_location={self.id_location}, location_name='{self.location_name}', "
                f"id_city={self.id_city}, id_region={self.id_region})>")

    def __str__(self):
        return f"Локация: {self.location_name} (ID: {self.id_location})"

class Metric(Base):
    """Таблица метрик."""

    __tablename__ = 'metrics'

    id_metrics: int = Column(
        Integer,
        Sequence('metrics_id_metrics_seq'),
        primary_key=True,
        doc='Уникальный идентификатор метрики',
    )
    metric_name: Optional[str] = Column(
        String,
        doc='Название метрики',
    )
    metric_description: Optional[str] = Column(
        Text,
        doc='Описание метрики',
    )

    metric_values: List['MetricValue'] = relationship(
        'MetricValue',
        back_populates='metric',
        doc='Значения метрики',
    )
    def __repr__(self):
        return (f"<Metric(id_metrics={self.id_metrics}, metric_name='{self.metric_name}')>")

    def __str__(self):
        return f"Метрика: {self.metric_name} (ID: {self.id_metrics})"

class MetricValue(Base):
    """Таблица значений метрик."""

    __tablename__ = 'metric_values'

    id_mv: int = Column(
        Integer,
        Sequence('metric_values_id_mv_seq'),
        primary_key=True,
        doc='Уникальный идентификатор значения метрики',
    )
    id_metric: int = Column(
        Integer,
        ForeignKey('metrics.id_metrics', ondelete='RESTRICT'),
        nullable=False,
        doc='Идентификатор метрики',
    )
    id_region: Optional[int] = Column(
        Integer,
        ForeignKey('regions.id_region', ondelete='CASCADE'),
        doc='Идентификатор региона',
    )
    id_city: Optional[int] = Column(
        Integer,
        ForeignKey('cities.id_city', ondelete='CASCADE'),
        doc='Идентификатор города',
    )
    value: Optional[str] = Column(
        String,
        doc='Значение метрики',
    )
    month: Optional[int] = Column(
        Integer,
        doc='Месяц',
    )
    year: Optional[int] = Column(
        Integer,
        doc='Год',
    )
    id_location: Optional[int] = Column(
        Integer,
        ForeignKey('locations.id_location', ondelete='CASCADE'),
        doc='Идентификатор локации',
    )
    create_time: Mapped[Optional[datetime.datetime]] = Column(DateTime(True), server_default=text('now()'))
    modify_time: Mapped[Optional[datetime.datetime]] = Column(DateTime(True), server_default=text('now()'))
    type_location: Mapped[Optional[str]] = Column(String)

    metric: 'Metric' = relationship(
        'Metric',
        back_populates='metric_values',
        doc='Связанная метрика',
    )
    region: Optional['Region'] = relationship(
        'Region',
        back_populates='metric_values',
        doc='Связанный регион',
    )
    city: Optional['City'] = relationship(
        'City',
        back_populates='metric_values',
        doc='Связанный город',
    )
    location: Optional['Location'] = relationship(
        'Location',
        back_populates='metric_values',
        doc='Связанная локация',
    )

    def __repr__(self):
        return (f"<MetricValue(id_mv={self.id_mv}, id_metric={self.id_metric}, value='{self.value}', "
                f"month={self.month}, year={self.year})>")

    def __str__(self):
        return (f"Значение Метрики: {self.metric.metric_name if self.metric else 'N/A'} - "
                f"Value: {self.value} (ID: {self.id_mv})")

class Sync(Base):
    """Таблица соответствия для синхронизации данных из разных источников."""

    __tablename__ = 'sync'

    id_sync: int = Column(
        Integer,
        primary_key=True,
        doc='Уникальный идентификатор синхронизации',
    )
    id_to: int = Column(
        Integer,
        nullable=False,
        doc='Идентификатор целевого объекта',
    )
    object_type: str = Column(
        String,
        nullable=False,
        doc='Тип объекта',
    )
    input_value: str = Column(
        String,
        nullable=False,
        doc='Входное значение',
    )
    input_from: str = Column(
        String,
        nullable=False,
        doc='Источник входных данных',
    )

    def __repr__(self):
        return (f"<Sync(id_sync={self.id_sync}, id_to={self.id_to}, "
                f"object_type='{self.object_type}', input_value='{self.input_value}', "
                f"input_from='{self.input_from}')>")

    def __str__(self):
        return (f"Синхронизация: {self.object_type} (ID Sync: {self.id_sync}) "
                f"от {self.input_from} с значением '{self.input_value}'")


class Photo(Base):
    """Таблица для хранения URL фотографий по конкретным локациям."""

    __tablename__ = 'photos'

    id_photo: int = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('photos_id_photo_seq'::regclass)"),
        doc='Уникальный идентификатор фотографии',
    )
    id_location: Optional[int] = Column(
        ForeignKey('locations.id_location', ondelete='CASCADE'),
        doc='Идентификатор локации',
    )
    url: str = Column(
        String,
        nullable=False,
        doc='URL фотографии',
    )

    location: Optional['Location'] = relationship(
        'Location',
        doc='Связанная локация',
    )

    def __repr__(self):
        return (f"<Photo(id_photo={self.id_photo}, id_location={self.id_location}, "
                f"url='{self.url}')>")

    def __str__(self):
        return f"Фотография (ID: {self.id_photo}) для локации ID: {self.id_location}"


class Review(Base):
    """Таблица отзывов."""

    __tablename__ = 'reviews'

    id_reviews: int = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('reviews_id_reviews_seq'::regclass)"),
        doc='Уникальный идентификатор отзыва',
    )
    id_location: int = Column(
        ForeignKey('locations.id_location', ondelete='CASCADE'),
        nullable=False,
        doc='Идентификатор локации',
    )
    like: Optional[int] = Column(
        SmallInteger,
        doc='Лайки',
    )
    text: Optional[str] = Column(
        Text,
        doc='Текст отзыва',
    )
    data: Optional[str] = Column(
        String,
        doc='Дата отзыва',
    )

    location: 'Location' = relationship(
        'Location',
        doc='Связанная локация',
    )

    def __repr__(self):
        return (f"<Review(id_reviews={self.id_reviews}, id_location={self.id_location}, "
                f"like={self.like}, data='{self.data}')>")

    def __str__(self):
        return (f"Отзыв (ID: {self.id_reviews}) для локации ID: {self.id_location} - "
                f"Лайков: {self.like}, Дата: {self.data}")


def initialize_database() -> None:
    """Подключение к базе данных и создание таблиц."""
    try:
        database_url = Config_SQL.SQLALCHEMY_DATABASE_URI
        logger.debug(f"Строка подключения: {database_url}")
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        logger.info("Таблицы успешно созданы или уже существуют.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise


# Инициализация базы данных при запуске модуля
initialize_database()
