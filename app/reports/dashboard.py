# app/reports/dashboard.py

import io
import logging
from typing import Dict, Optional

import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from flask import Flask

from app.data.database.models_repository import (
    MetricValueRepository, 
    RegionRepository
)
from app.reports.plot import (
    RegionPagePlot,
    BaseDashboardPlot,
    SegmentDashboardPlot
)
from app.data.transform.prepare_data import (
    RegionDashboardData,
    CityDashboardData,
    BaseDashboardData
)
logger = logging.getLogger(__name__)


def create_dashboard(server: Flask) -> Dash:
    """Создает единый Dash-приложение с маршрутизацией страниц."""
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    app_dash = Dash(
        __name__,
        server=server,
        url_base_pathname="/dashboard/",
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )
    app_dash.layout = dbc.Container([
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content")
    ], fluid=True)
    register_callbacks(app_dash)
    return app_dash


def register_callbacks(app_dash: Dash) -> None:
    """Регистрирует коллбеки для роутинга и экспорта."""

    @app_dash.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    )
    def display_page(pathname: str):
        parts = pathname.rstrip("/").split("/")
        # /dashboard/segment/region/beach/5
        if len(parts) == 6 and parts[2] == "segment":
            entity_type = parts[3]
            segment_prefix = parts[4]
            entity_id = int(parts[5])
            for key, prefix in BaseDashboardData.get_segment_patterns():
                if prefix == segment_prefix:
                    return create_segment_dashboard(entity_type, entity_id, key)
            return dbc.Alert("Сегмент не найден", color="warning")
        # /dashboard/region/5
        if len(parts) >= 4 and parts[2] == "region":
            try:
                region_id = int(parts[3])
                return create_region_layout(region_id)
            except ValueError as e:
                logger.error(f"Ошибка значения при формировании страницы региона: {e}")
                return page_not_found()
        # /dashboard/city/123
        if len(parts) >= 4 and parts[2] == "city":
            try:
                city_id = int(parts[3])
                return create_city_layout(city_id)
            except ValueError as e:
                logger.error(f"Ошибка значения при формировании страницы города: {e}")
                return page_not_found()
        return page_not_found()



    @app_dash.callback(
    Output("download-dataframe-xlsx", "data"),
    Input("btn-download", "n_clicks"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
    def download_metrics(n_clicks: int, pathname: str):
        buffer = io.BytesIO()
        parts = pathname.rstrip("/").split("/")
        entity_type = parts[2]
        entity_id = int(parts[3])

        # Универсальный сборщик
        if entity_type == "region":
            data_prep = RegionDashboardData()
            metrics = data_prep.get_kpi_metrics(id_region=entity_id)
        elif entity_type == "city":
            data_prep = CityDashboardData()
            metrics = data_prep.get_kpi_metrics(id_city=entity_id)
        else:
            return None

        df = pd.DataFrame([metrics])
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Metrics")
        buffer.seek(0)
        filename = f"{entity_type}_{entity_id}_metrics.xlsx"
        return dcc.send_bytes(buffer.read(), filename)
    
    region_data = RegionDashboardData()
    rpp = RegionPagePlot(region_data)
    rpp.register_graph_callbacks(app_dash)
    SegmentDashboardPlot.register_callbacks(app_dash)
def page_not_found():
    """Заглушка для нераспознанных URL."""
    return dbc.Alert("Страница не найдена", color="danger")


def create_region_layout(region_id: int):
    """
    Компоновка дашборда региона.
    Собирает KPI, графики абсолютных значений и кнопку экспорта.
    """
    region_repo = RegionRepository()
    region_data = RegionDashboardData()
    rpp = RegionPagePlot(region_data)
    # Пытаемся получить экземпляр региона
    region = region_repo.find_region_by_id(region_id)
    region_name = region.region_name if region else f"#{region_id}"
    # KPI
    cards = rpp.make_kpi_cards(id_region = region_id)

    # Графики
    flow_block = rpp.flow_graph_with_year_selector(region_id)
    nights_block = rpp.nights_graph_with_year_selector(region_id)
    # муниципалитеты
    muni = rpp.make_municipalities_map(region_id)

    # Таблица сегментов
    seg_table = rpp.make_segments_table(id_region = region_id)
    weather_block = rpp.make_weather_block(id_region = region_id)  # <- добавили сюда

    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H2(f"Дашборд региона: {region_name}"), width=12),
            className="my-3"
        ),
        # Карточки показателей
        dbc.Row(cards, className="mb-4"),
        # Графики турпотока и ночевок
        dbc.Row([
            dbc.Col(flow_block, md=6),
            dbc.Col(nights_block, md=6),
        ], className="mb-4"),
         # Карта городов
        dbc.Row(dbc.Col(html.H4("Муниципалитеты и города"), width=12)),
        dbc.Row(dbc.Col(muni, width=12), className="mb-4"),
        dbc.Row(dbc.Col(html.H4("Оценки сегментов туризма", id="segment-table"), width=12), className="mt-4"),
        dbc.Row(dbc.Col(seg_table, width=12), className="mb-4"),
        dbc.Row(dbc.Col(html.H4("Климат и погода региона"), width=12), className="mt-4"),
        dbc.Row(dbc.Col(weather_block, width=12), className="mb-4"),

        dbc.Row([
            dbc.Col(dbc.Button("Скачать метрики в Excel", id="btn-download", color="primary"),
                    width="auto"),
            dcc.Download(id="download-dataframe-xlsx")
        ], justify="start"),
    ], fluid=True)

def create_city_layout(city_id: int):
    """
    Компоновка дашборда города.
    """
    from app.data.database.models_repository import CitiesRepository
    from app.models import City

    # Получаем данные о городе
    city_repo = CitiesRepository()
    cities = city_repo.get_by_fields(model=City, id_city=city_id)
    city = cities[0] if cities else None
    city_name = city.city_name if city else f"#{city_id}"

    # Подготавливаем универсальные классы данных и визуализации
    city_data = CityDashboardData()
    plot = BaseDashboardPlot(city_data)

    # KPI карточки
    cards = plot.make_kpi_cards(id_city=city_id)
    # Таблица сегментов
    seg_table = plot.make_segments_table(id_city=city_id)
    # Погода
    weather_block = plot.make_weather_block(id_city=city_id)

    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H2(f"Дашборд города: {city_name}"), width=12),
            className="my-3"
        ),
        dbc.Row(cards, className="mb-4"),
        dbc.Row(dbc.Col(html.H4("Оценки сегментов туризма"), width=12), className="mt-4"),
        dbc.Row(dbc.Col(seg_table, width=12), className="mb-4"),
        dbc.Row(dbc.Col(html.H4("Климат и погода города"), width=12), className="mt-4"),
        dbc.Row(dbc.Col(weather_block, width=12), className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("Скачать метрики в Excel", id="btn-download", color="primary"),
                    width="auto"),
            dcc.Download(id="download-dataframe-xlsx")
        ], justify="start"),
    ], fluid=True)

def create_segment_dashboard(entity_type: str, entity_id: int, segment_key: str):
    """
    Формирует страницу дашборда по сегменту туризма для города или региона.
    """
    # Получаем данные сегмента
    if entity_type == "region":
        data_prep = RegionDashboardData()
        # Получаем название региона
        from app.data.database.models_repository import RegionRepository
        region = RegionRepository().find_region_by_id(entity_id)
        place_name = region.region_name if region else f"#{entity_id}"
    elif entity_type == "city":
        data_prep = CityDashboardData()
        from app.data.database.models_repository import CitiesRepository
        from app.models import City
        city_list = CitiesRepository().get_by_fields(model=City, id_city=entity_id)
        city = city_list[0] if city_list else None
        place_name = city.city_name if city else f"#{entity_id}"
    else:
        return dbc.Alert("Неизвестный тип", color="danger")

    plot = SegmentDashboardPlot(data_prep)
    segment_config = data_prep.SEGMENTS.get(segment_key)
    segment_label = segment_config["label"] if segment_config else segment_key
    if segment_label != 'Главная инфраструктура':
        segment_label += ' туризм'

    # Красивый заголовок
    title = f'Дашборд сегмента: "{segment_label}". {place_name}'

    # Карточки KPI
    kpi_cards = plot.make_segment_kpi_cards(
        segment_key,
        id_region=entity_id if entity_type == "region" else None,
        id_city=entity_id if entity_type == "city" else None
    )
    locations_block = SegmentDashboardPlot.make_layout(
        segment=segment_key,
        initial_rating_range=(1.0, 5.0),
        region_id=(entity_id if entity_type == "region" else None),
        city_id=(entity_id if entity_type == "city"  else None)
    )

    return dbc.Container([
        dbc.Row(dbc.Col(html.H2(title), width=12), className="my-3"),
        *kpi_cards,
        dbc.Row(dbc.Col(html.Hr(), width=12), className="my-4"),
        dbc.Row(dbc.Col(locations_block, width=12)),
    ], fluid=True)

