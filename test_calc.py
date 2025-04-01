from app.data.calc.base_calc import Region_calc
from app.data.imports.import_json import import_json_file
from app.data.database.models_repository import LocationsRepository
import time

# dp = Region_calc(154)
# dp.get_like_type_location(name='Пляж', id_city='')

# print(import_json_file(file_path=r'app\files\segments.json')['beach'])
start_time = time.time()
l = LocationsRepository()
type_location = 'Памятник, мемориал'
print(type_location)
x = l.get_locations_by_type(type_location=type_location)
print(len(x))
end_time = time.time()
execution_time = end_time - start_time
print(f"Время выполнения: {execution_time:.2f} секунд")