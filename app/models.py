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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from geoalchemy2 import Geometry  # For storing geometric data types
from sqlalchemy.dialects.postgresql import JSONB

from .config import Config

# Настройка логирования
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'app.log',
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5  # Количество резервных файлов
)

logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)


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


class Rewiew(Base):
    """Таблица отзывов."""

    __tablename__ = 'rewiews'

    id_rewiews: int = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('rewiews_id_rewiews_seq'::regclass)"),
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


def initialize_database() -> None:
    """Подключение к базе данных и создание таблиц."""
    try:
        database_url = Config.SQLALCHEMY_DATABASE_URI
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        logger.info("Таблицы успешно созданы или уже существуют.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise


# Инициализация базы данных при запуске модуля
initialize_database()
