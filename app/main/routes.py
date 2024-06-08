from flask import Flask, render_template, Blueprint
from app.additional.textutil import transliterate
from app.main.views import load_geojson, generate_map  # Импортируйте функции из views.py

app = Flask(__name__)

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
    map_html = generate_map()
    return render_template('index.html', map_html=map_html)

@main.route('/region/<int:id>')
def region(id):
    # Логика для получения данных региона по ID
    return render_template('region.html', region_id=id)
