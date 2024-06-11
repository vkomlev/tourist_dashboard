import os
import geopandas as gpd
from flask import current_app
from app.data.database import Sync_repo, Region_repo
import folium
import random
from app.data.processing import process_tourism_data

# Кэш для хранения GeoDataFrame
cached_gdf, map = None, None

def load_geojson():
    '''Загрузка json файла с границами с учетом кэширования'''
    global cached_gdf
    if cached_gdf is None:
        geojson_path = os.path.join(current_app.root_path, 'data', 'regions.geojson')
        cached_gdf = gpd.read_file(geojson_path)
        # Фильтрация, чтобы загружать только полигоны
        cached_gdf = cached_gdf[cached_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    return cached_gdf


def generate_map():
    '''Генерация карты с границами регионов'''
    global map
    if map is None:
        gdf = load_geojson()
        m = folium.Map(location=[61.5240, 105.3188], zoom_start=3)
        sync_repo = Sync_repo()

        # Добавление Popup с информацией о регионе
        for _, row in gdf.iterrows():
            region_name = row['name:ru']
            region_id = sync_repo.find_id(region_name, 'region', 'OSM')
            if region_id is not None:
                popup_content = f"<b>{region_name}</b><br><a href='/region/{region_id}' target='_blank'>Подробнее</a>"
                popup = folium.Popup(popup_content, max_width=300)
                color = "#{:06x}".format(random.randint(0, 0xFFFFFF))  # Генерация случайного цвета
                folium.GeoJson(
                    row['geometry'],
                    style_function=lambda feature, color=color: {
                        'fillColor': "#{:06x}".format(random.randint(0, 0xFFFFFF)),
                        'color': "#{:06x}".format(random.randint(0, 0xFFFFFF)),
                        'weight': 2,
                        'fillOpacity': 0.5,
                    },
                    highlight_function=lambda feature: {
                        'weight': 3,
                        'color': 'black',
                        'fillOpacity': 0.7
                    },
                    tooltip=row['name:ru'],
                    popup=popup
                ).add_to(m)
                map  = m
    else:
        m = map

    return m._repr_html_()

def generate_top_popular_table():
    '''Генерация таблицы с топ 10 самых популярных регионов'''
    tourism_data = process_tourism_data(n=10)
    tourism_table = generate_tourism_table(tourism_data)
    return tourism_table

def generate_tourism_table(df):
    table_html = '<table class="table">'
    table_html += '<thead><tr><th>Место</th><th>Название региона</th><th>Турпоток</th><th>Доля в %</th></tr></thead>'
    table_html += '<tbody>'
    for _, row in df.iterrows():
        table_html += f'<tr><td>{row["rank"]}</td><td>{row["region_name"]}</td><td>{row["value"]}</td><td>{row["percentage"]:.2f}</td></tr>'
    table_html += '</tbody></table>'
    return table_html

def get_region_details(region_id):
    '''Получение детальной информации о регионе'''
    db = Region_repo()
    region = db.find_region_by_id(region_id)
    if region:
        population = region.characters.get('population') if region.characters else 'Unknown'
        return {
            'region_name': region.region_name,
            'description': region.description,
            'population': population
        }
    return None
