import pandas
# from app.data.parsing import Parse_weather
from app.data.database import Database
from app.models import Region, City, LocationType, Location
import time

class Compare:

    def __init__(self):
        self.input_data = {}
        self.database = Database()

    def load_from_database(self, model):
        data = self.database.get_all(model)
        self.input_data = [Database.to_dict(i) for i in data]
        return self.input_data

class Compare_regions(Compare):

    def __init__(self):
        super().__init__()
        
    # !!!когда на маке работал - Делает словарь где ключи это названия регионов а значение их id из БД
    def load_regions_from_csv(self, path):
        self.input_data_regions = {}
        df = pandas.read_csv(path, delimiter=';')
        self.input_data_regions = {i['region_name']:i['id_region'] for index, i in df.iterrows()}
        return self.input_data_regions
    
    # Делает словарь где ключи это названия регионов а значение их id из БД
    def load_regions_from_database(self):
        self.input_data_regions = {}
        self.load_from_database(Region)
        self.input_data_regions = {i['region_name']:i['id_region'] for i in self.input_data}
        return self.input_data_regions
    
    # Заменяет ключи с названия в БД на названия с сайта который парсим чтобы в последствии соотносить их с id из БД
    def compare_regions_from_weather(self):
        from app.data.parsing import Parse_weather
        weather = Parse_weather()
        weather_regions = weather.parse_regions()
        self.load_regions_from_database()
        self.found_regions = {}
        self.not_found_regions = []
        for region in weather_regions.keys():
            check = self._check_names(region, self.input_data_regions)
            if check:
                self.found_regions[check[1]] = self.input_data_regions[check[0]]
            else:
                self.not_found_regions.append(region)
        return self.found_regions
        
    # Соотносит названия в базе данных с новыми (с сайтов)
    def _check_names(self, alt_name, input_data):
        sql_many = input_data.keys()
        for sql_one in sql_many:
            sql_one = sql_one.split(' ')
            if sql_one.count(alt_name) == 1:
                sql_one = ' '.join(sql_one)
                return [sql_one, alt_name, input_data[sql_one]]
        
        for sql_one in sql_many:
            if sql_one.count(alt_name[0:5]) == 1:
                return [sql_one, alt_name, input_data[sql_one]]
            

class Compare_cities(Compare_regions):

    def __init__(self):
        super().__init__()
        self.count = 0

    def load_cities_from_csv(self, path):
        self.input_data_cities = {}
        df = pandas.read_csv(path, delimiter=';')
        self.input_data_cities = {(i['city_name'],i['id_region']):i['id_city'] for index, i in df.iterrows()}
        return self.input_data_cities
    
    def load_cities_from_database(self):
        self.input_data_cities = {}
        self.load_from_database(City)
        self.input_data_cities = {(i['city_name'],i['id_region']):i['id_city'] for i in self.input_data}
        return self.input_data_cities
        
    # Получаем словарь городов где ключ это id из БД 
    # а значение кортеж из названия города и url по всем регионам с сайта погоды
    def union_cities(self):
        from app.data.parsing import Parse_weather
        self.count += 1
        i = -1
        self.all_found_cities = {}
        self.all_not_found_cities = {}
        self.load_cities_from_database()
        time.sleep(2)
        weather = Parse_weather()
        weather_regions = weather.parse_regions()
        for key, value in weather_regions.items():
            # i += 1
            # if i == 0 :
                i += 1
                self.compare_cities_from_weather(value,key)
                self.all_found_cities = self.all_found_cities|self.found_cities
                self.all_not_found_cities = self.all_not_found_cities|self.not_found_cities
                print('прошли регион', i+1, key, value)
                print(20*'-')
                # break
        print(f'прошли {i+1} регион/региона/регионов')
        print(self.count)

    
    # получает список городов в одном регионе и формирует 2 словаря
    # 1. совпавшие города
    # 2. не совпавшие
    def compare_cities_from_weather(self, region_url, region_name):
        from app.data.parsing import Parse_weather
        time.sleep(2)
        weather = Parse_weather()
        weather_cities = weather.parse_cities(region_url)
        self.load_regions_from_database()
        id_region = self._check_names(region_name, self.input_data_regions)[2]
        sql_cities_from_region = {key[0]: value for key, value in self.input_data_cities.items() if key[1] == id_region}
        # print('города из базы: ', len(sql_cities_from_region))
        # print('города с сайта: ', len(weather_cities))
        self.found_cities = {}
        self.not_found_cities= {}
        for city, url in weather_cities.items():
            check = self._check_names(city, sql_cities_from_region)
            if check:
                self.found_cities[sql_cities_from_region[check[0]]] = (check[1], url)
                print('взял', city)
            else:
                if region_name in self.not_found_cities:
                    self.not_found_cities[region_name].append(city)
                else:
                    self.not_found_cities[region_name] = [city]
        # return self.found_cities
    
class Compare_yandex(Compare):

    def __init__(self):
        super().__init__()

    # делает два словаря с городами по регионно и метриками для последующего использования при парсинге
    def load_regions_city_location_from_database(self):
        # получаем данные из таблицы регионов
        self.load_from_database(Region)
        input_data_regions = self.input_data
        # получаем данные из таблицы городов
        self.load_from_database(City)
        input_data_cities = self.input_data
        self.input_data = {}
        # объединение словарей регионы и города
        self.input_data_r_c = {}
        for region in input_data_regions:
            for city in input_data_cities:
                if city['id_region'] == region['id_region']:
                    self.input_data_r_c[region['region_name'], city['city_name']] = [region['id_region'], city['id_city']]
        # получаем данные из таблицы метрик, только те что из yandex 
        self.load_from_database(LocationType)
        self.input_data_yandex_locations_type = {i['name']: i['id_location_type'] for i in self.input_data if 'yandex' in i['location_type_value']}
