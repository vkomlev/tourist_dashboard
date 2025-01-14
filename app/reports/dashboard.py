from dash import Dash, html, dcc, Input, Output, State 
import plotly.express as px 
import pandas as pd 

from app.logging_config import logger 
from app.data.database.models_repository import RegionRepository 
from app.data.calc.base_calc import Region_calc 

from app.reports.plot import Region_page_plot
 
 
def extract_region_id(pathname: str) -> int:
    """
    Извлекает идентификатор региона из URL.

    Args:
        pathname (str): Путь URL.

    Returns:
        int: Идентификатор региона.
    """
    try:
        path_parts = pathname.split('/')
        return int(path_parts[-1]) if path_parts[-1].isdigit() else 0
    except Exception as e:
        logger.error(f"Ошибка извлечения ID региона: {e}")
        return 0
     
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
        dcc.Location(id='url', refresh=False),
        html.H1("Комплексная оценка туристской отрасли регионов"),

        # Вывод динамического региона
        html.Div(id='dynamic-region-header'),

        # Блок оценки
        html.Div(id='rating-display'),

        # Детальный расчет
        html.Div(id='score-calculation', style={'margin-top': '20px'}),

        # Детальный расчет
        html.Div(id='detailed-calculation', style={'margin-top': '20px'}),

        # Добавляем новый блок для динамики турпотока
        html.Div(id='tourist-flow-section', style={'margin-top': '20px'}),

        # Добавляем блок количества ночевок
        html.Div(id='tourist-nights-section', style={'margin-top': '20px'})
    ])

    @app_dash.callback(
        Output('score-calculation', 'children'),
        Input('url', 'pathname')
    )
    def load_score_calc_section(pathname):
        """
        Загружает секцию с посегментным графиком оценок.
        """
        try:
            region_id = extract_region_id(pathname)
            rplot = Region_page_plot()
            return rplot.create_rating_section(region_id)
        except Exception as e:
            logger.error(f"Ошибка загрузки секции рейтинга: {e}")
            return html.Div("Ошибка загрузки данных")
    
    @app_dash.callback(
        Output('detailed-calculation', 'children'),
        Input('url', 'pathname')
    )
    def load_detailed_calc_section(pathname):
        """
        Загружает секцию с рассчетами туризма.
        """
        try:
            region_id = extract_region_id(pathname)
            rplot = Region_page_plot()
            return rplot.create_details_section(region_id)
        except Exception as e:
            logger.error(f"Ошибка загрузки секции рейтинга: {e}")
            return html.Div("Ошибка загрузки данных")
 
    @app_dash.callback(
        Output('tourist-flow-section', 'children'),
        Input('url', 'pathname')
    )
    def load_tourist_flow_section(pathname):
        """
        Загружает секцию с вкладками для графиков турпотока.
        """
        try:
            region_id = extract_region_id(pathname)
            rplot = Region_page_plot()
            return rplot.create_tabs_layout(region_id)
        except Exception as e:
            logger.error(f"Ошибка загрузки секции турпотока: {e}")
            return html.Div("Ошибка загрузки данных")
    
    @app_dash.callback(
        Output('tourist-nights-section', 'children'),
        Input('url', 'pathname')
    )
    def load_tourist_nights_section(pathname):
        """
        Загружает секцию с вкладками для графиков количества ночевок.
        """
        try:
            region_id = extract_region_id(pathname)
            year = 2023
            rplot = Region_page_plot()
            return rplot.create_night_count_section(region_id, year)
        except Exception as e:
            logger.error(f"Ошибка загрузки секции ночевок: {e}")
            return html.Div("Ошибка загрузки данных")

    @app_dash.callback(
        Output('tourist-flow-chart', 'figure'),
        Input('year-tabs', 'value'),
        State('url', 'pathname')
    )
    def update_tourist_flow_chart(selected_year, pathname):
        """
        Ленивая загрузка графиков по выбранному году.
        """
        try:
            # Получаем ID региона
            path_parts = pathname.split('/')
            id_region = int(path_parts[-1]) if path_parts[-1].isdigit() else 0

            # Загружаем график
            rplot = Region_page_plot()
            return rplot.create_tourist_flow_chart(id_region, int(selected_year))
        except Exception as e:
            logger.error(f"Ошибка обновления графика турпотока: {e}")
            return {}


    # Функция обратного вызова для обработки URL и извлечения параметра ID 
    @app_dash.callback( 
        Output('dynamic-region-header', 'children'), 
        Input('url', 'pathname')  # Получаем текущий URL 
    ) 
    def update_dashboard_header(pathname):
        """
        Обработчик для динамических URL с поддержкой ID региона.
        """
        try:
            # Извлекаем ID региона
            region_id = extract_region_id(pathname)
            logger.debug(f'region_id = {region_id}')

            # Получаем данные региона
            region_repo = RegionRepository()
            region_info = region_repo.find_region_by_id(region_id)

            if not region_info:
                raise ValueError("Регион не найден")
            region_name = region_info.region_name


            # Формируем контент
            rplot = Region_page_plot()
            header = rplot.create_region_header(region_name)

            return header

        except Exception as e:
            logger.error(f"Ошибка обновления дашборда: {e}")
            return html.H2("Регион не найден"), "", ""
 
    return app_dash
