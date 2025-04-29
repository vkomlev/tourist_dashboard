from app.data.calc.base_calc import Region_calc
from app.data.imports.import_json import import_json_file
from app.data.database.models_repository import LocationsRepository
import time


r = Region_calc(id_region='')
r.get_weather_calc(id_city=5845, segment='beach')


# # не рабочая, нужно цикл с сегментами добавить
# start_time = time.time()
# dp = Region_calc(154)
# x = dp.get_like_locations(id_region=150)
# for i in x:
#     print(i)
#     print(x[i])
# end_time = time.time()
# execution_time = end_time - start_time
# print(f"Время выполнения: {execution_time:.2f} секунд")


# c = CitiesRepository()
# cities = c.get_cities_full()
# mass = [city.__dict__ for city in cities]
# df = pd.DataFrame(mass)
# df_city = df[['id_region', 'id_city', 'city_name']]


# Тест поиска нужного типа локации в таблице локации
# start_time = time.time()
# l = LocationsRepository()
# type_location = 'Памятник, мемориал'
# print(type_location)
# x = l.get_locations_by_type(type_location=type_location)
# print(len(x))
# end_time = time.time()
# execution_time = end_time - start_time
# print(f"Время выполнения: {execution_time:.2f} секунд")