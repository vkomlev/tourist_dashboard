import os
import geopandas as gpd
from flask import current_app, url_for
from app.data.database import SyncRepository, RegionRepository
import folium
import random
from app.data.transform.prepare_data import Main_page_dashboard
from app.reports.plot import Main_page_plot, Region_page_plot

# Кэш для хранения GeoDataFrame
cached_gdf, map = None, None

def load_geojson():
    '''Загрузка json файла с границами с учетом кэширования'''
    global cached_gdf
    if cached_gdf is None:
        geojson_path = os.path.join(current_app.root_path, 'files', 'regions.geojson')
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
        sync_repo = SyncRepository()

        # Добавление Popup с информацией о регионе
        for _, row in gdf.iterrows():
            region_name = row['name:ru']
            region_id = sync_repo.find_id(region_name, 'region', 'OSM')
            if region_id is not None:
                image_path = os.path.join(current_app.root_path, 'static', 'images', f'{region_id}.jpg')
                if os.path.exists(image_path):
                    image_url = url_for('static', filename=f'images/{region_id}.jpg')
                    image_html = f'<br><img src="{image_url}" alt="Достопримечательность" width="150" height="100">'
                else:
                    image_html = ''
                
                popup_content = (
                    f"<b>{region_name}</b><br>"
                    f"<a href='/dashboard/region/{region_id}' target='_blank'>Подробнее</a>"
                    f"{image_html}"
                    )

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
                map = m
    else:
        m = map

    return m._repr_html_()


def generate_top_popular_data():
    '''Генерация таблицы с топ 10 самых популярных регионов'''
    tourism_data = Main_page_dashboard.process_tourist_count_data(n=10, top=True)
    tourism_table = generate_top_popular_html(tourism_data)
    return tourism_table

def generate_top_popular_html(df):
    table_html = '<table class="table">'
    table_html += '<thead><tr><th>Место</th><th>Название региона</th><th>Турпоток</th><th>Доля в %</th></tr></thead>'
    table_html += '<tbody>'
    for _, row in df.iterrows():
        table_html += f'<tr><td>{row["rank"]}</td><td>{row["region_name"]}</td><td>{row["value"]}</td><td>{row["percentage"]:.2f}</td></tr>'
    table_html += '</tbody></table>'
    return table_html

def get_region_details(region_id):
    '''Получение детальной информации о регионе и генерация гистограммы'''
    db = RegionRepository()
    region = db.find_region_by_id(region_id)
    if region:
        rpp = Region_page_plot()
        population = region.characters.get('population') if region.characters else 'Unknown'
        rpp.plot_region_flow_histogram(region_id, region.region_name)  # Генерация гистограммы
        return {
            'region_name': region.region_name,
            'description': region.description,
            'population': population,
            'histogram_path': f'images/histogram_flow_{region_id}.png'
        }
    return None

