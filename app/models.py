from sqlalchemy import create_engine, Column, Integer, String, Text, JSON,\
SmallInteger, ForeignKey, Sequence, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry  # For storing geometric data types
from .config import Config
from sqlalchemy.dialects.postgresql import JSONB


# from app.data.database import Base

Base = declarative_base()
metadata = Base.metadata

class Region(Base):
    '''Таблица регионов'''
    __tablename__ = 'regions'

    id_region = Column(Integer, Sequence('regions_id_region_seq'), primary_key=True)
    region_name = Column(String, nullable=False)
    capital = Column(Integer, ForeignKey('cities.id_city', ondelete='CASCADE'))
    coordinates = Column(Geometry('POINT', srid=4326))
    description = Column(Text)
    characters = Column(JSONB)

    cities = relationship('City', back_populates='region', foreign_keys='City.id_region')
    capital_city = relationship('City', foreign_keys=[capital])
    locations = relationship('Location', back_populates='region')
    metric_values = relationship('MetricValue', back_populates='region')


class City(Base):
    '''Таблица городов'''
    __tablename__ = 'cities'

    id_city = Column(Integer, Sequence('cities_id_city_seq'), primary_key=True)
    city_name = Column(String, nullable=False)
    id_region = Column(Integer, ForeignKey('regions.id_region', ondelete='CASCADE'))
    coordinates = Column(Geometry('POINT', srid=4326))
    description = Column(Text)
    characters = Column(JSONB)

    region = relationship('Region', back_populates='cities', foreign_keys=[id_region])
    locations = relationship('Location', back_populates='city')
    metric_values = relationship('MetricValue', back_populates='city')


class LocationType(Base):
    '''Таблица типов локаций'''
    __tablename__ = 'location_type'

    id_location_type = Column(Integer, Sequence('location_type_id_location_type_seq'), primary_key=True)
    location_type_value = Column(String, nullable=False)    
    description = Column(Text)
    location_type_key = Column(String)
    name = Column(String)
    general = Column(String)
    locations = relationship('Location', back_populates='location_type')


class Location(Base):
    '''Таблица локаций'''
    __tablename__ = 'locations'

    id_location = Column(Integer, Sequence('locations_id_location_seq'), primary_key=True)
    location_name = Column(String)
    description = Column(Text)
    coordinates = Column(Geometry('POINT', srid=4326))
    id_city = Column(Integer, ForeignKey('cities.id_city', ondelete='RESTRICT'))
    id_region = Column(Integer, ForeignKey('regions.id_region', ondelete='RESTRICT'))
    characters = Column(JSONB)
    id_location_type = Column(Integer, ForeignKey('location_type.id_location_type', ondelete='RESTRICT'))

    city = relationship('City', back_populates='locations')
    region = relationship('Region', back_populates='locations')
    location_type = relationship('LocationType', back_populates='locations')
    metric_values = relationship('MetricValue', back_populates='location')


class Metric(Base):
    '''Таблица метрик'''
    __tablename__ = 'metrics'

    id_metrics = Column(Integer, Sequence('metrics_id_metrics_seq'), primary_key=True)
    metric_name = Column(String)
    metric_description = Column(Text)

    metric_values = relationship('MetricValue', back_populates='metric')


class MetricValue(Base):
    '''Таблица значений метрик'''
    __tablename__ = 'metric_values'

    id_mv = Column(Integer, Sequence('metric_values_id_mv_seq'), primary_key=True)
    id_metric = Column(Integer, ForeignKey('metrics.id_metrics', ondelete='RESTRICT'), nullable=False)
    id_region = Column(Integer, ForeignKey('regions.id_region', ondelete='CASCADE'))
    id_city = Column(Integer, ForeignKey('cities.id_city', ondelete='CASCADE'))
    value = Column(String)
    month = Column(Integer)
    year = Column(Integer)
    id_location = Column(Integer, ForeignKey('locations.id_location', ondelete='CASCADE'))

    metric = relationship('Metric', back_populates='metric_values')
    region = relationship('Region', back_populates='metric_values')
    city = relationship('City', back_populates='metric_values')
    location = relationship('Location', back_populates='metric_values')

class Sync(Base):
    '''Таблица соответствия для синхронизации данных из разных источников'''
    __tablename__ = 'sync'

    id_sync = Column(Integer, primary_key=True)
    id_to = Column(Integer, nullable=False)
    object_type = Column(String, nullable=False)
    input_value = Column(String, nullable=False)
    input_from = Column(String, nullable=False)

class Photo(Base):
    '''Таблица для хранения url фотографий по конкретным локациям '''
    __tablename__ = 'photos'

    id_photo = Column(Integer, primary_key=True, server_default=text("nextval('photos_id_photo_seq'::regclass)"))
    id_location = Column(ForeignKey('locations.id_location', ondelete='CASCADE'))
    url = Column(String, nullable=False)

    location = relationship('Location')

class Rewiew(Base):
    __tablename__ = 'rewiews'

    id_rewiews = Column(Integer, primary_key=True, server_default=text("nextval('rewiews_id_rewiews_seq'::regclass)"))
    id_location = Column(ForeignKey('locations.id_location', ondelete='CASCADE'), nullable=False)
    like = Column(SmallInteger)
    text = Column(Text)
    data = Column(String)

    location = relationship('Location')


# Подключение к базе данных
DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI
engine = create_engine(DATABASE_URL)

# Создание таблиц
Base.metadata.create_all(engine)
