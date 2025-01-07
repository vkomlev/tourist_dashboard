from dash import Dash, html, dcc, Input, Output 
import plotly.express as px 
import pandas as pd 
from dash.dependencies import State 
from app.logging_config import logger 
from app.data.database.models_repository import RegionRepository 
from app.data.calc.base_calc import Region_calc 
from app.data.score.base_assessment import OverallTourismEvaluation 
from app.reports.plot import Region_page_plot 
 
 
# Интерпретации оценок 
interpretations = { 
    (1.0, 2.0): "Туристская инфраструктура слабо развита, требуется значительное улучшение.", 
    (2.1, 3.0): "Средний уровень, подходит для локальных туристов, но имеет ограничения для международного туризма.", 
    (3.1, 4.0): "Хорошая инфраструктура, пригодная для национальных и международных туристов.", 
    (4.1, 5.0): "Высокий уровень инфраструктуры, готовый к приему большого турпотока и международных мероприятий." 
} 
 
 
# Вспомогательная функция для интерпретации 
def get_interpretation(rating): 
    for (low, high), text in interpretations.items(): 
        if low <= rating <= high: 
            return text 
    return "Нет данных." 
 
 
def create_dashboard(flask_server): 
    """ 
    Создание Dash-дэшборда с поддержкой динамических URL. 
    """ 
    # Создаем приложение Dash 
    app_dash = Dash( 
        __name__, 
        server=flask_server, 
        url_base_pathname=f'/region/', 
        suppress_callback_exceptions=True  # Добавляем обработку динамических компонентов 
    ) 
 
    # Макет с поддержкой динамического URL 
    app_dash.layout = html.Div([ 
        dcc.Location(id='url', refresh=False),  # Добавляем поддержку URL 
        html.H1("Комплексная оценка туристской отрасли регионов"), 
 
        # Вывод динамического региона 
        html.Div(id='dynamic-region-header'), 
 
        # Блок оценки 
        html.Div(id='rating-display'), 
 
        # Детальный расчет 
        html.Div(id='detailed-calculation', style={'margin-top': '20px'}), 
 
    ]) 
 
 
    # Функция обратного вызова для обработки URL и извлечения параметра ID 
    @app_dash.callback( 
        [Output('dynamic-region-header', 'children'), 
         Output('rating-display', 'children'), 
         Output('detailed-calculation', 'children')], 
        Input('url', 'pathname')  # Получаем текущий URL 
    ) 
    def update_dashboard(pathname): 
        """ 
        Обработчик для динамических URL с поддержкой ID региона. 
        """ 
        # Извлекаем ID из URL 
        try: 
            # Разделяем URL, чтобы получить id 
            path_parts = pathname.split('/') 
            id_region = int(path_parts[-1]) if path_parts[-1].isdigit() else 0 
            logger.debug(f'region_id = {id_region}') 
 
            # Проверяем, существует ли такой регион 
            dp = RegionRepository() 
            region_info = dp.find_region_by_id(id_region=id_region) 
            if not region_info: 
                raise ValueError("Регион не найден") 
            region_name = region_info.region_name 
        except Exception: 
            return html.H2("Регион не найден"), "", ""
# получаем рассчитаные значения по туризму региона 
        dp = Region_calc(id_region=id_region) 
        result_overall = dp.get_overall_metrics() 
 
        result_segment = dp.get_segment_scores() 
        df = pd.DataFrame( 
            { 
            'Название сегмента':list(result_segment.keys()), 
            'Оценка':list(result_segment.values()) 
            } 
            ).sort_values('Оценка') 
        # Создаем график по топу сегментов туризма 
        fig = px.bar(df, x='Оценка', y='Название сегмента', title='Топ сегментов туризма') 
        dp = OverallTourismEvaluation(**result_overall) 
        rating = dp.calculate_overall_score() 
 
        # Генерация звезд 
        stars = '★' * int(rating) + '☆' * (5 - int(rating)) 
 
        # Описание и позиции 
        description = get_interpretation(rating) 
        country_rank = f"место по стране 50" 
        macro_rank = f"Место по хз 50" 
 
        # Пример расчета 
        detailed = html.Pre(f""" 
        Подробный расчет: 
        Ttotal = 0.4 * {dp.segment_scores} +  0.2 * {dp.general_infra} + 0.1 * {dp.safety} +  0.1 * {dp.flow} + 0.05 * {dp.nights} + 0.05 * {dp.climate} + 0.05 * {dp.prices} + 0.05 * {dp.distance} 
               = {rating:.2f} 
        """) 
 
        # Заголовок региона 
        header = html.H2(f"Регион: {region_name}") 
 
 
        return ( 
            header,  
            html.Div([ 
                html.H2(f"Рейтинг: {rating:.1f} {stars}"), 
                dcc.Graph(figure=fig), 
                html.P(description), 
                html.P(country_rank), 
                html.P(macro_rank), 
                html.Div(id='tabs-content') 
            ]), 
            detailed 
            ) 
 
    return app_dash
