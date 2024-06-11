from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import Config
from app.models import Sync, Region, MetricValue

Base = declarative_base()

class Database:
    def __init__(self):
        self.engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        Base.metadata.drop_all(self.engine)

    def get_session(self):
        return self.Session()

    def add(self, obj):
        session = self.get_session()
        try:
            session.add(obj)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def add_all(self, objs):
        session = self.get_session()
        try:
            session.add_all(objs)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def query(self, model):
        session = self.get_session()
        try:
            return session.query(model).all()
        finally:
            session.close()

    def delete(self, obj):
        session = self.get_session()
        try:
            session.delete(obj)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    def get_engine(self):
        return self.engine
    
    def find_by_primary_key(self, model, pk_column, pk_value):
        session = self.get_session()
        try:
            return session.query(model).filter(getattr(model, pk_column) == pk_value).first()
        finally:
            session.close()

    def find_by_name(self, model, name_column, name_value):
        session = self.get_session()
        try:
            return session.query(model).filter(getattr(model, name_column) == name_value).all()
        finally:
            session.close()

class Sync_repo(Database):
    def find_id(self, input_value, object_type, input_from):
        session = self.get_session()
        try:
            sync_entry = session.query(Sync).filter(
                Sync.input_value == input_value,
                Sync.object_type == object_type,
                Sync.input_from == input_from
            ).first()
            return sync_entry.id_to if sync_entry else None
        finally:
            session.close()

class Region_repo(Database):
    def find_region_by_id(self, id_region):
        session = self.get_session()
        try:
            return session.query(Region).filter(Region.id_region == id_region).first()
        finally:
            session.close()

class MV_repo(Database):
    def get_tourist_count_data(self):
        '''Турпоток по регионам'''
        session = self.get_session()
        try:
            query = session.query(
                MetricValue.id_region,
                MetricValue.value,
                MetricValue.month,
                MetricValue.year,
            ).filter(
                MetricValue.id_metric == 2
            )
            return query.all()
        finally:
            session.close()
    
    def get_tourist_count_data_by_region(self, region_id):
        '''Турпоток по конкретному региону в разресе периодов'''
        session = self.get_session()
        try:
            query = session.query(
                MetricValue.id_region,
                MetricValue.value,
                MetricValue.month,
                MetricValue.year,
            ).filter(
                MetricValue.id_metric == 2,
                MetricValue.id_region == region_id
            )
            return query.all()
        finally:
            session.close()