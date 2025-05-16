#app\data\transform\divide_municipal.py
import geopandas as gpd
from app.data.database.models_repository import CitiesRepository
from app.models import City
import os
from app.logging_config import logger

# Загрузка исходного GeoJSON с границами городов/муниципалитетов
input_path = os.path.join(os.getcwd(), 'app', 'files','municipalities_ru.geojson') 
gdf = gpd.read_file(input_path)

# Инициализация репозитория городов
cities_repo = CitiesRepository()

# Предполагаем, что в свойствах каждого feature есть ключ 'id_city'
# или 'OSM' для mаппинга. Сначала получим маппинг OSM id -> region id из БД:
# Например, для всех городов:
city_to_region = {}
cities = cities_repo.get_all(City)  # возвращает список City
logger.info(f'Получили список городов. Общее количество = {len(cities)}')
for city in cities:
    # characters JSONB, в нём есть 'OSM'
    if city.characters:
        osm_id = city.characters.get('OSM')
    else:
        osm_id = None
    if osm_id:
        logger.info(f'Для города {city.city_name} найден OSM_ID ={osm_id}')
        city_to_region[int(osm_id)] = city.id_region
    else:
        logger.warning(f'Для города {city.city_name} не найден OSM_ID')

# Добавляем колонку region_id в GeoDataFrame
def lookup_region(feature):
    # В GeoJSON поле может называться 'OSM' или 'id_city'; пробуем оба
    osm = feature.get('OSM') or feature.get('properties', {}).get('OSM') or feature.get('properties', {}).get('id') or feature.get('id')
    city_name = feature.get('name') or feature.get('properties', {}).get('name')
    if osm:        
        logger.info(f'Для города {city_name} найден регион {city_to_region.get(int(osm))}')
        return city_to_region.get(int(osm))
    else:
        logger.warning(f'Для города {city_name} не найден элемент osm')
        return None

# Применяем lookup_region ко всем строкам
gdf['region_id'] = gdf.apply(lambda row: lookup_region(row), axis=1)

# Создаём выходной каталог
out_dir = os.path.join(os.getcwd(), 'app', 'files', 'municipalities')
os.makedirs(out_dir, exist_ok=True)

# Разбиваем по region_id и сохраняем отдельные GeoJSON
for region_id, group in gdf.groupby('region_id'):
    if region_id is None:
        continue
    out_path = os.path.join(out_dir, f'{int(region_id)}.geojson')
    group.drop(columns=['region_id']) \
         .to_file(out_path, driver='GeoJSON')
    logger.info(f'Сохранен geojson {out_path}')

