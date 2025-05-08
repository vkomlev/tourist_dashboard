# app/reports/dashboard.py

import io
import logging
from typing import Dict, Optional

import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from flask import Flask

from app.data.metric_codes import get_metric_code
from app.data.database.models_repository import MetricValueRepository, RegionRepository
from app.reports.plot import (
    Region_page_plot
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
        if len(parts) >= 4 and parts[2] == "region":
            try:
                region_id = int(parts[3])
                return create_region_layout(region_id)
            except ValueError:
                return page_not_found()
        return page_not_found()

    @app_dash.callback(
        Output("download-dataframe-xlsx", "data"),
        Input("btn-download", "n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def download_metrics(n_clicks: int, pathname: str):
        """
        Формирует и отдает Excel-файл с последними KPI-метриками региона.
        """
        buffer = io.BytesIO()
        repo = MetricValueRepository()
        parts = pathname.rstrip("/").split("/")
        entity_field = f"id_{parts[2]}"
        entity_id = int(parts[3])

        # Только относительные KPI (те, что в METRIC_CODE_MAP)
        metric_keys = list(get_metric_code.__self__.keys())  # словарь METRIC_CODE_MAP
        records: Dict[str, Optional[float]] = {}

        for key in metric_keys:
            try:
                code, rus_name = get_metric_code(key)
                mvs = repo.get_info_metricvalue(id_metric=code, **{entity_field: entity_id})
                if mvs:
                    records[rus_name] = float(mvs[-1].value)
                else:
                    records[rus_name] = None
            except Exception as e:
                logger.warning("Не удалось экспортировать %s: %s", key, e)
                records[rus_name] = None

        df = pd.DataFrame([records])
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Metrics")
        buffer.seek(0)
        filename = f"{parts[2]}_{entity_id}_metrics.xlsx"
        return dcc.send_bytes(buffer.read(), filename)


def page_not_found():
    """Заглушка для нераспознанных URL."""
    return dbc.Alert("Страница не найдена", color="danger")


def create_region_layout(region_id: int):
    """
    Компоновка дашборда региона.
    Собирает KPI, графики абсолютных значений и кнопку экспорта.
    """
    repo = MetricValueRepository()
    region_repo = RegionRepository()
    rpp = Region_page_plot()
    # Пытаемся получить экземпляр региона
    region = region_repo.find_region_by_id(region_id)
    region_name = region.region_name if region else f"#{region_id}"
    # KPI
    cards = rpp.make_kpi_cards(region_id, repo)

    # Графики
    flow_fig = rpp.make_flow_figure(region_id, repo)
    nights_fig = rpp.make_nights_figure(region_id, repo)

    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H2(f"Дашборд региона: {region_name}"), width=12),
            className="my-3"
        ),

        dbc.Row(cards, className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=flow_fig), md=6),
            dbc.Col(dcc.Graph(figure=nights_fig), md=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("Скачать метрики в Excel", id="btn-download", color="primary"),
                    width="auto"),
            dcc.Download(id="download-dataframe-xlsx")
        ], justify="start"),
    ], fluid=True)
