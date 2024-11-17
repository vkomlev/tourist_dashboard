from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError, SQLAlchemyError, NoResultFound
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.config import Config
import inspect
from app.models import Sync, Region, MetricValue, LocationType, Location, Photo, Rewiew, City
import time, json
import pandas


# from app.models import *
# from sqlalchemy.orm import class_mapper
# from app.models import Base
# import json
# import csv
# import importlib


Base = declarative_base()

def retry_on_failure(retries=5, delay=2):
    """Декоратор для повторных попыток при сбоях подключения"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    attempts += 1
                    print(f"Попытка {attempts} из {retries} не удалась: {e}")
                    if attempts < retries:
                        print(f"Повтор через {delay} секунд...")
                        time.sleep(delay)
                    else:
                        print("Все попытки исчерпаны.")
                        raise
        return wrapper
    return decorator

def manage_session(func):
    """Декоратор для автоматического закрытия сессии SQLAlchemy"""
    def wrapper(self, *args, **kwargs):
        try:
            # Выполняем основную функцию
            result = func(self, *args, **kwargs)
            # Возвращаем результат
            return result
        except Exception as e:
            # В случае ошибки откатываем транзакцию
            self.session.rollback()
            raise e
        finally:
            # Закрываем сессию после использования
            self.session.close()
    return wrapper


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
        except Exception as e:
            print(e)
            session.rollback()
            raise
        finally:
            session.close()
            return obj

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
    
    def get_all(self, model):
        try:
            session = self.get_session()
            return session.query(model).all()
        finally:
            session.close()

    @classmethod
    def to_dict(self, obj):
        """Преобразует объект модели в словарь"""
        return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    
    def get_by_fields(self, model, **kwargs):
        """Получить записи по значениям полей, переданным через kwargs"""
        try:
            session = self.get_session()
            query = session.query(model)
            for key, value in kwargs.items():
                query = query.filter(getattr(model, key) == value)
            return query.all()
        finally:
            session.close()
    
    def update(self, obj):
        """Обновить запись"""
        session = self.get_session()
        try:
            # Привязываем объект к текущей сессии, если он не в сессии
            if not session.object_session(obj):
                session.merge(obj)  # Используем merge для включения объекта в сессию
            session.commit()  # Фиксируем изменения
        except Exception as e:
            session.rollback()  # Откатываем изменения при ошибке
            raise
        finally:
            session.close()  # Закрываем сессию
    
    def get_model_by_tablename(tablename):
        '''Returns a model class by tablename'''
        base = Base                        
        for class_obj in base.registry._class_registry.values():
            if hasattr(class_obj, '__tablename__') and class_obj.__tablename__ == tablename:
                return class_obj
        return None

# Сопоставление названий из сайтов с названиями из БД
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
    
    def fill(self, model, input_from, df):
        db = Database()
        rows = db.get_all(model)
        # exists = db.get_by_fields(model=model, input_from = input_from)
        for row in rows:
            id_name = model.__table__.primary_key.columns.keys()[0]
            if not db.get_by_fields(model=Sync, input_from = input_from, id_to = getattr(row, id_name)):
                sync = Sync()
                sync.id_to = getattr(row, id_name)
                sync.object_type = model.__table__.name
                sync.input_from = input_from 
                self.add(sync)
                
        
        for key, value in df.items():
            sync = Sync()
            if isinstance(key, tuple):
                sync.input_value = key[0]
            elif isinstance(key, str):
                sync.input_value = key
            
            sync.id_to = value
            sync.input_from = input_from
            params = {'id_to':value, 'input_from': input_from}
            id = db.get_by_fields(model=Sync, **params)[0]
            sync.id_sync = id.id_sync
            db.update(sync)


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
            
    # загрузка погоды в таблицу MetricValue
    def fill_weather(self, city_id, value):
        ratio = {'day': 213, 'night':214, 'rainfall':215,  'water':216}
        for month, temperatures in value.items():
            for d_n_r_w, number in temperatures.items():  
                mv = MetricValue()
                mv.id_city = city_id
                mv.id_metric = ratio[d_n_r_w]
                mv.value = number
                mv.month = month
                mv.year = 2023
                filters = {'id_city': city_id, 'id_metric':ratio[d_n_r_w],
                               'value': number,  'month': month, 'year': 2023}
                    # есть или нет элемент в базе
                yes = self.get_by_fields(MetricValue, **filters)
                if yes:
                    mv.id_mv = yes[0].id_mv
                    self.update(mv)
                    print(f'Обновили параметр {ratio[d_n_r_w]} о городе {city_id}')
                else:
                    self.add(mv)
                    print(f'Добавили параметр {ratio[d_n_r_w]} о городе {city_id}')
        print('Прошли город', city_id)

class Location_Type_Repo(Database):

    # загружает типы локаций для яндекс карт из выбраного файла
    def loading_locations_yandex(self):
        # Указываем файл их которого брать данные
        locations =  pandas.read_excel(r'C:\Users\Cmaul\Desktop\programs\file\type_loc_yandex.xlsx')
        for index, row in locations.iterrows():
            lt = LocationType()
            lt.location_type_value = 'yandex'
            lt.name = row['name_loc']
            lt.general = row['type_loc']
            filters = {'location_type_value':'yandex',
                       'name':row['name_loc'],'general':row['type_loc']}
            yes = self.get_by_fields(LocationType, **filters)
            if yes:
                lt.id_location_type = yes[0].id_location_type
                self.update(lt)
                print(f'Обновили тип локации {row["name_loc"]}')
            else:
                self.add(lt)
                print(f'Добавили тип локации {row["name_loc"]}')

class JSONRepository(Database):
    '''Базовый класс для манипуляций с объектами БД, где есть JSONB поля'''
    def update_json_fields(self, model_instance, field_name = 'characteristics', json_field = {}):
        '''Метод получает пары JSON и обновляет их в БД'''
        if json_field:
            for key, value in json_field.items():
                wrapped_value = self._wrap_json_value(value)
                self._update_json_value (model_instance.__class__, model_instance.id, field_name,'{'+ key+'}', wrapped_value)
    
    def _update_json_value(self, model_class, name_id, item_id, json_field, key, new_value, operation='replace'):
        '''Метод обновляет значение JSONB поля в БД'''                
        
        # Обернуть ключ в фигурные скобки, если значение — массив
        if isinstance(new_value, list):
            key_path = f"{{{key}}}"
        else:
            key_path = key

        # Определение SQL-выражения в зависимости от типа операции
        if operation == 'replace':
            sql_expression = text(f"UPDATE {model_class.__tablename__} "
                                f"SET {json_field} = jsonb_set({json_field}, :key_path, :new_value) "
                                f"WHERE {name_id} = :item_id")
        elif operation == 'append':
            sql_expression = text(f"UPDATE {model_class.__tablename__} "
                                f"SET {json_field} = jsonb_set({json_field}, :key_path, ({json_field} #> :key_path) || :new_value) "
                                f"WHERE {name_id} = :item_id")
        elif operation == 'remove':
            sql_expression = text(f"UPDATE {model_class.__tablename__} "
                                f"SET {json_field} = jsonb_set({json_field}, :key_path, ({json_field} #> :key_path) - :new_value) "
                                f"WHERE {name_id} = :item_id")
        else:
            raise ValueError("Unsupported operation. Use 'replace', 'append', or 'remove'.")

        # Выполнение запроса
        try:
            new_value = self._wrap_json_value(value=new_value)
            session = self.get_session()
            session.execute(sql_expression, {"item_id": item_id, "key_path": key_path, "new_value": new_value})
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    def delete_json_pair(self, model_class, item_id, json_field = 'characteristics', key = {}):
        '''Метод удаляет пару JSON и обновляет их в БД'''
        # SQL-выражение для удаления пары по ключу из JSONB
        if key:
            sql_expression = text(f"UPDATE {model_class.__tablename__} "
                              f"SET {json_field} = {json_field} - :key_path "
                              f"WHERE id = :item_id")

        # Выполнение запроса
            try:
                self.session.execute(sql_expression, {"item_id": item_id, "key_path": [key]})
                self.session.commit()
            except SQLAlchemyError as e:
                self.session.rollback()
                raise e
    
    
    def _wrap_json_value(self, value):
        '''Оборачиваем JSON значение в зависимости от типа данных.'''
        if isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, list):
            wrapped_values = [self._wrap_json_value(v) for v in value]
            return f"[{', '.join(wrapped_values)}]"
        elif value is None:
            return 'null'
        else:
            # Обработка других типов по необходимости
            return f'"{str(value)}"'

    def get_json_value(self, model_class, serial_id, item_id, json_field, key):
        '''Получаем значение JSON пары по ключу JSON'''
        # SQL-выражение для извлечения значения по ключу из JSONB
        sql_expression = text(f"SELECT {json_field}->> :key_path FROM {model_class.__tablename__} WHERE {serial_id} = :item_id")
        # Выполнение запроса и извлечение значения
        try:
            session = self.get_session()
            result = session.execute(sql_expression, {"item_id": item_id, "key_path": key}).scalar()
            return result
        except NoResultFound:
            return None
       
    def _update_existing_record(self, existing_record, data, keep_existing = False) -> None:
        '''Если запись в БД уже существует, обновляем ее новыми обработанными данными из источника'''
        table_columns = inspect(existing_record.__class__).columns
        for column in table_columns :
            column_name = column.name
            if column_name in data and isinstance (column.type, JSONB):

                column_data = getattr(existing_record, column_name, b'{}')
                new_data = data.get(column_name, {})
                if not keep_existing:
                    column_data = column_data | new_data
                else:
                    column_data = new_data | column_data
                                                
                setattr(existing_record, column_name, column_data)
            elif column_name in data:
                if not (keep_existing and getattr(existing_record, column_name)):   
                    setattr(existing_record, column_name, data[column_name])

        # Вызываем общий метод для обновления
        self.update(existing_record)

    def _add_new_record(self, data, table_name):
        '''Если записи в БД не существует, добавляем новый объект с обработанными данными из источника'''
        record = data.copy()
        if 'table_to_load' in record:
            del record['table_to_load']
        if 'source_id' in record:
            del record['source_id']
                        
        model_class = self.get_model_by_table_name(table_name)
        valid_keys = [key for key in record.keys() if key in model_class.__table__.columns]
        new_record = model_class(**{key: record[key] for key in valid_keys})
        self.add(new_record)
    
    def _get_exists_by_field_and_json(self, model_class, record_data, record):
        '''Получаем существующую запись по полю name или JSON значению code
        Проверяет существование записи в БД, с учетом регистра в полях 
        и значениях JSON параметров.
        :param model_class: Класс модели SQLAlchemy.
        :param record_data: Данные новой записи.
        '''
        existing_record = None
        for data in record_data:
            filters = []
            if 'fields' in data:
                for value in data['fields']:
                    if record.get(value):
                        if isinstance(record.get(value), str):
                            filters.append(func.lower(getattr(model_class, value)) == record.get(value).lower())
                        elif isinstance(record.get(value), int) or isinstance(record.get(value), float):
                            filters.append(getattr(model_class, value) == record.get(value))
                    else:
                        return None
            if 'json_fields' in data:
                for index, value in enumerate(data['json_keys']):
                    if record.get(data['json_fields'][index]):
                        characteristic = record[data['json_fields'][index]]
                        if characteristic.get(value):                            
                            filters.append(getattr(model_class, data['json_fields'][index])[value].astext == characteristic[value])
                        else:
                            return None
                                                                                                
            # Поиск по имени без учета регистра
            existing_record = self.session.query(model_class).filter(*filters).first()
            if existing_record:
                return existing_record
        else:
            return None                                

    def get_model_by_table_name(self, table_name):
        '''Возвращает класс модели по имени таблицы'''
        # return Database.get_model_by_tablename(table_name)
        return self.model

class Locations_Repo(JSONRepository):
    def __init__(self):
        super().__init__()
        self.model = Location

    # Для яндекс локаций
    # Проверяет если данная локация в базе 
    def check_loc_yandex(self, id_region, id_city, location_name):
        filters = {'id_region':id_region, 'id_city':id_city, 'location_name':location_name}
        yes = self.get_by_fields(Location, **filters)
        if yes:
            return yes
        else:
            return yes
        
    # Для яндекс локаций
    # загружает локацию в БД
    def loading_info_loc_yandex(self, location_name, coordinates, id_city, id_region, characters):
        l = Location()
        l.location_name = location_name
        l.coordinates = coordinates
        l.id_city = id_city
        l.id_region = id_region
        l.characters = characters
        self.add(l)
        filters = {'id_region':id_region, 'id_city':id_city, 'location_name':location_name}
        yes = self.get_by_fields(Location, **filters)
        self.id_loc_yandex = yes[0].id_location

class Rewiew_Repo(Database):

    # Для яндекс локаций
    # загружает отзыв и оценку у локации
    def loading_rewiew_loc_yandex(self, id_loc, like, text, data):
        r = Rewiew()
        r.id_location = id_loc
        r.like = like
        r.text = text
        r.data = data
        self.add(r)

class Photo_Repo(Database):

    # Для яндекс локаций
    # загружает url фото у локации
    def loading_photo_loc_yandex(self, id_loc, url):
        p = Photo()
        p.id_location = id_loc
        p.url = url
        self.add(p)

class Cities_Repo(JSONRepository):
    # проверяет есть ли у города 'last_type_loc' если да то возвращает его значение, иначе добавляет его и возвращает
    def check_type_loc(self, id_city, first_type):
        while True:
            filters = {'id_city':id_city}
            city = self.get_by_fields(City, **filters)
            characters = city[0].characters
            if not characters or not 'last_type_loc' in characters:
                characters['last_type_loc'] = f'{first_type}'
                c = City()
                c.id_city = id_city
                c.characters = characters
                self.update(c)                       
                continue
            else:
                return characters['last_type_loc']
    
    # загружает новый тип локации
    def loading_next_type(self, id_city, type_loc):
        filters = {'id_city':id_city}
        city = self.get_by_fields(City, **filters)
        characters = city[0].characters
        characters['last_type_loc'] = f'{type_loc}'
        c = City()
        c.id_city = id_city
        c.characters = characters
        self.update(c) 




           

        
        




            



# class Da(Database):

#     def open_json (self, door = r'C:\programs\file\DBS_delivery.json', coding = 'utf-8'):
#             with open(door, 'r', encoding=coding) as file_json:
#                 self.text_json = json.load(file_json)

#     def open_csv (self, door, separator = ',', coding = 'utf-8'):
#             with open(door, 'r', encoding=coding) as file_csv:
#                 self.text_csv = list(csv.DictReader(file_csv, delimiter=separator))

#     def rename (self, product):
#             return f'работает rename виии {product}'

#     def get_model_by_table_name(self, table_name):
#         '''выдает нужную модель'''
#         mass_tablename = {'Notable': Notable()}                      
#         if table_name in mass_tablename:
#             return mass_tablename[table_name]
#         return None
    
#     def get_column_by_column_name(self, column_name):
#         '''выбирает нужную колонку'''
#         columns = {'id_dbs': Notable.id_dbs, 'marketplace': Notable.marketplace, 'product': Notable.product}
#         return columns[column_name]
 
#     def processing(self, door, table_name, separator = ',', coding = 'utf-8'):
#         self.open_json()
#         self.open_csv(door = door, separator = separator, coding = coding)
#         columns_json = self.text_json[table_name]
#         settings = {}
        
#         # цикл делает словарь где ключ название столбца в загружаемом файле а значение массив с названием в БД и действием
#         for column_json in columns_json:
#             settings[column_json['mappings']['DBSDelivery']] = [column_json['name'], column_json['mappings']['transformation']]

#         for row in self.text_csv:
#             table = self.get_model_by_table_name(table_name)
#             for key, value in row.items():
#                 cell = settings[key]
#                 column = self.get_column_by_column_name(cell[0])
#                 if 'skip' in cell:
#                     pass

#                 elif 'direct' in cell:
#                     column = value 
#                     pass
        
#                 else:
#                     x = getattr(Da(),cell[1])(value)
#                     column = x
                    
#             self.add(table)
                    
                        
