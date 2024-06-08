import os
import geopandas as gpd
from flask import current_app
from app.data.database import Sync_repo
import folium
import random

# Кэш для хранения GeoDataFrame
cached_gdf = None

def load_geojson():
    global cached_gdf
    if cached_gdf is None:
        geojson_path = os.path.join(current_app.root_path, 'data', 'regions.geojson')
        cached_gdf = gpd.read_file(geojson_path)
        # Фильтрация, чтобы загружать только полигоны
        cached_gdf = cached_gdf[cached_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    return cached_gdf

def generate_map():
    gdf = load_geojson()
    m = folium.Map(location=[61.5240, 105.3188], zoom_start=3)
    sync_repo = Sync_repo()

    # Добавление Popup с информацией о регионе
    for _, row in gdf.iterrows():
        region_name = row['name:ru']
        region_id = sync_repo.find_id(region_name, 'region', 'OSM')
        if region_id is not None:
            popup_content = f"<b>{region_name}</b><br><a href='/region/{region_id}'>Подробнее</a>"
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

    return m._repr_html_()
