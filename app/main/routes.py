from flask import Flask, render_template, Blueprint
from app.additional.textutil import transliterate
from app.main.views import load_geojson, generate_map, get_region_details  # Импортируйте функции из views.py

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
    '''Главная страница'''
    map_html = generate_map()
    return render_template('index.html', map_html=map_html)

@main.route('/region/<int:id>')
def region(id):
    '''Страница региона'''
    region_details = get_region_details(id)
    if region_details:
        return render_template('region.html', **region_details)
    else:
        return render_template('404.html'), 404  # Отображение страницы 404, если регион не найден
