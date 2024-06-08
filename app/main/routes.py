import os
import folium
import geopandas as gpd
import random
from flask import Flask, render_template, request, url_for, Blueprint
import urllib.parse
from app.additional.textutil import transliterate

app = Flask(__name__)

# Кэш для хранения GeoDataFrame
cached_gdf = None

def load_geojson():
    global cached_gdf
    if cached_gdf is None:
        geojson_path = os.path.join(app.root_path, 'data', 'regions.geojson')
        cached_gdf = gpd.read_file(geojson_path)
        # Фильтрация, чтобы загружать только полигоны
        cached_gdf = cached_gdf[cached_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    return cached_gdf

# Флаг для проверки, был ли уже выполнен первый запрос
has_first_request = False

@app.before_request
def before_each_request():
    global has_first_request
    if not has_first_request:
        # Выполнить действия, которые должны быть выполнены перед первым запросом
        load_geojson()
        has_first_request = True

main = Blueprint('main', __name__)

@main.route('/')
def index():
    gdf = load_geojson()
    m = folium.Map(location=[61.5240, 105.3188], zoom_start=3)

    # Стиль для GeoJson
    def style_function(feature):
        region_name = feature['properties']['name:ru']
        region_name_translit = transliterate(region_name)
        return {
            'fillColor': "#{:06x}".format(random.randint(0, 0xFFFFFF)),
            'color': "#{:06x}".format(random.randint(0, 0xFFFFFF)),
            'weight': 2,
            'fillOpacity': 0.5,
            'className': f"region-{region_name_translit}"  # Используем транслитерированное имя для класса
        }

    # Создание GeoJson объекта
    geojson = folium.GeoJson(
        gdf,
        style_function=style_function,
        highlight_function=lambda feature: {
            'weight': 3,
            'color': 'black',
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['name:ru'],
            aliases=['Регион: '],
            labels=True,
            sticky=False
        ),       
    ).add_to(m)

    # JavaScript для обработки клика по региону
    m.get_root().html.add_child(folium.Element("""
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            var regionElements = document.querySelectorAll('[class^="region-"]');
            for (var i = 0; i < regionElements.length; i++) {
                regionElements[i].addEventListener('click', function() {
                    var regionClass = this.getAttribute('class');
                    var regionName = regionClass.split('region-')[1];
                    if (regionName) {
                        window.location.href = `/region/${regionName}`;
                    }
                });
            }
        });
        </script>
    """))

    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html)

@main.route('/region/<name>')
def region(name):
    name = transliterate(name)  # Если нужно обратное преобразование
    #return f"<h1>{region_name}</h1><a href='/'>Вернуться на главную</a>"
    return render_template('region.html', region_name=name)


