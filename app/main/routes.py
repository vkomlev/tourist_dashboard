from flask import Flask, render_template, Blueprint, url_for, send_from_directory
from app.additional.textutil import transliterate
from app.main.views import load_geojson, generate_map, get_region_details, generate_top_popular_data  # Импорт функций из views.py
from app.reports.plot import Main_page_plot
import os

app = Flask(__name__)

# Флаг для проверки, был ли уже выполнен первый запрос
has_first_request = False

@app.before_request
def before_each_request():
    '''Проверка первого запуска приложения'''
    global has_first_request
    if not has_first_request:
        # Выполнить действия, которые должны быть выполнены перед первым запросом
        load_geojson()
        has_first_request = True

main = Blueprint('main', __name__)

@main.route('/')
def index():
    map_html = generate_map()
    tourism_table  = generate_top_popular_data()
    Main_page_plot.plot_heatmap_tourist_count_data()
    return render_template('index.html', map_html=map_html, tourism_table=tourism_table)

#@main.route('/region/<int:id>')
#def region(id):
#    region_details = get_region_details(id)
#    if region_details:
#        return render_template('region.html', **region_details)
#    else:
#        return render_template('404.html'), 404
