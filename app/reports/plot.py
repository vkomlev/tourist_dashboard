#app/reports/plot.py

import seaborn as sns
import matplotlib.pyplot as plt
import os
import plotly.express as px
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, dash_table, MATCH, callback_context, no_update
import colorlover as cl
from typing import List, Optional, Dict, Tuple
import pandas as pd

from app.data.transform.prepare_data import (
    Main_page_dashboard, 
    BaseDashboardData, 
    RegionDashboardData, 
    CityDashboardData, 
    SegmentMapping,
)
from app.logging_config import logger



class Main_page_plot:
    @staticmethod
    def plot_heatmap_tourist_count_data():
        mpd = Main_page_dashboard()
        df_pivot = mpd.generate_heatmap_tourist_count_data()
        
        # Преобразование значений в миллионы
        df_pivot = df_pivot / 1_000_000

        plt.figure(figsize=(12, 8))
        
        sns.heatmap(df_pivot, annot=False, cmap="YlGnBu", cbar_kws={'label': 'Турпоток (млн. чел.)'})
        plt.title('Турпоток по сезонам в популярных регионах')

        # Уменьшение шрифта для названий регионов
        plt.yticks(rotation=0, fontsize=8)
        plt.xticks(rotation=90, fontsize=8)

        # Сохранение графика
        output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, 'heatmap.png'))
        plt.close()

class BaseDashboardPlot:
    """
    Универсальный базовый класс для построения визуализаций дашборда
    (как для региона, так и для города).
    """
    def __init__(self, data_prep):
        """
        :param data_prep: экземпляр класса подготовки данных (RegionDashboardData или CityDashboardData)
        """
        self.data_prep = data_prep

    def _choose_card_color(self, val: Optional[float]) -> str:
        try:
            val = float(val)
        except:
            val = None
        if val is None:
            return "secondary"
        if val < 3.0:
            return "danger"
        if val < 4.0:
            return "warning"
        return "success"

    def make_kpi_cards(self, *, id_region: Optional[int] = None, id_city: Optional[int] = None) -> List[dbc.Row]:
        """
        Формирует layout карточек KPI для города или региона.
        """
        def make_segment_link(label: str, entity_type: str, entity_id: int) -> html.Div:
            url = f"/dashboard/segment/{entity_type}/main/{entity_id}"
            return dcc.Link(label, href=url, target='_blank', style={"color": "white", "textDecoration": "underline", "cursor": "pointer"})
        kpis = self.data_prep.get_kpi_metrics(id_region=id_region, id_city=id_city)
        main_metric_key = 'Комплексная оценка развития туризма'
        infra_metrics = [
            'Средняя оценка отелей и других мест размещения',
            'Количество отелей и других мест размещения',
            'Количество кафе, ресторанов и пр. мест питания'
        ]

        main_value = kpis[main_metric_key]
        main_display = f"{main_value:.2f}" if isinstance(main_value, (int, float)) else "—"
        main_color = self._choose_card_color(main_value)
        main_card = dbc.Card(
            [
                dbc.CardHeader(main_metric_key, className="text-white fs-5"),
                dbc.CardBody(html.H2(main_display, className="card-title text-white fw-bold"), className="text-center"),
            ],
            color=main_color,
            inverse=True,
            className="mb-3 shadow",
            style={"minHeight": "140px", "fontSize": "1.8rem"}
        )

        infra_cards = []
        for name in infra_metrics:
            val = kpis[name]
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            color = self._choose_card_color(val)
            entity_type = "region" if id_region else "city"
            entity_id = id_region if id_region else id_city
            card_content = make_segment_link(display, entity_type, entity_id)
            infra_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(name, className="text-white"),
                        dbc.CardBody(html.H4(card_content, className="card-title text-white")),
                    ],
                    color=color,
                    inverse=True,
                    className="mb-3 shadow-sm",
                    style={"minHeight": "110px"}
                )
            )

        exclude_keys = [main_metric_key] + infra_metrics
        other_cards = []
        for name, val in kpis.items():
            if name in exclude_keys:
                continue
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            color = self._choose_card_color(val)
            if name == 'Комплексная оценка сегментов':
                body = html.H4(
                    html.A(main_display, href="#segment-table", className="text-white", style={
                        "textDecoration": "underline", "cursor": "pointer"
                    }),
                    className="card-title"
                )
            else:
                body = html.H4(display, className="card-title text-white")
            other_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(name, className="text-white"),
                        dbc.CardBody(body),
                    ],
                    color=color,
                    inverse=True,
                    className="mb-3 shadow-sm",
                    style={"minHeight": "110px"}
                )
            )
        # Layout
        result = [
            dbc.Row(dbc.Col(main_card, width={"size": 6, "offset": 3}), className="mb-3"),
            dbc.Row([dbc.Col(card, md=4) for card in infra_cards], className="mb-3"),
        ]
        cols_in_row = 4
        for i in range(0, len(other_cards), cols_in_row):
            row = dbc.Row([dbc.Col(card, md=3) for card in other_cards[i:i+cols_in_row]], className="mb-3")
            result.append(row)
        return result

    def make_segments_table(self, *, id_region: Optional[int] = None, id_city: Optional[int] = None) -> dash_table.DataTable:
        """
        Строит DataTable с оценками сегментов для города или региона.
        """
        entity_type = "region" if id_region else "city"
        entity_id = id_region if id_region else id_city
        df = self.data_prep.get_segment_scores(id_region=entity_id if entity_type == "region" else None,
                                           id_city=entity_id if entity_type == "city" else None)
        thead = html.Thead(
            html.Tr([
                html.Th("Сегмент"),
                html.Th("Оценка"),
            ]),
            className="table-primary"
            )

        rows = []
        for i, row in df.iterrows():
            seg_name = row['segment']
            value = row['value']
            # Получаем key по русскому названию
            key = self.data_prep.SEGMENT_LABEL_TO_KEY.get(seg_name)
            if key:
                prefix = self.data_prep.SEGMENTS[key]["url_prefix"]
                url = f"/dashboard/segment/{entity_type}/{prefix}/{entity_id}"
                cell = html.Td(
                            html.A(
                                seg_name,
                                href=url,
                                target="_blank",
                                style={"textDecoration": "underline", "color": "#007bff", "cursor": "pointer"}
                            )
                )
            else:
                cell = html.Td(seg_name)
            rows.append(html.Tr([cell, html.Td(value)]))
        return html.Table(
            [thead, html.Tbody(rows)],
            className="table table-striped table-bordered table-hover align-middle text-center shadow-sm rounded mb-3",
            id='segment-table',
            style={"fontSize": "1.1rem"}
    )
            


    def make_weather_summary_card(self, summary: dict) -> dbc.Card:
        """
        Формирует информационную карточку с саммари по погоде.
        """
        if not summary:
            return dbc.Card(
                dbc.CardBody("Нет данных о погоде."),
                color="secondary"
            )

        swim_str = ', '.join(summary['swimming_season']) if summary['swimming_season'] else "—"
        return dbc.Card([
            dbc.CardHeader("Климат: основные показатели"),
            dbc.CardBody([
                html.P(f"Самые теплые месяцы: {', '.join(f'{k} ({v:.1f}°C)' for k, v in summary['warm'].items())}"),
                html.P(f"Самые холодные месяцы: {', '.join(f'{k} ({v:.1f}°C)' for k, v in summary['cold'].items())}"),
                html.P(f"Дождливые месяцы: {', '.join(f'{k} ({v:.0f} мм)' for k, v in summary['rainfall'].items())}"),
                html.P(f"Сезон для купания: {swim_str}"),
                html.P(f"Минимум: {summary['t_min']:.1f}°C, максимум: {summary['t_max']:.1f}°C, среднегодовая: {summary['t_mean']:.1f}°C")
            ])
        ], color="info", outline=True)

    def plot_temperature(self, temp: pd.DataFrame, water: Optional[pd.DataFrame] = None) -> go.Figure:
        """
        Строит график температур по месяцам.
        """
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temp['month'], y=temp['day_t'],
            mode='lines+markers', name='Днём'
        ))
        fig.add_trace(go.Scatter(
            x=temp['month'], y=temp['night_t'],
            mode='lines+markers', name='Ночью'
        ))
        if water is not None and not water.empty:
            fig.add_trace(go.Scatter(
                x=water['month'], y=water['water'],
                mode='lines+markers', name='Вода'
            ))
        fig.update_layout(
            title="Температура по месяцам",
            xaxis_title="Месяц",
            yaxis_title="Температура (°C)",
            xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=[
                'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']),
            legend=dict(orientation='h'),
            margin=dict(l=10, r=10, t=30, b=10)
        )
        return fig

    def plot_rainfall(self, rainfall: pd.DataFrame) -> go.Figure:
        """
        Строит график осадков по месяцам.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=rainfall['month'],
            y=rainfall['rainfall'],
            name='Осадки'
        ))
        fig.update_layout(
            title="Осадки по месяцам",
            xaxis_title="Месяц",
            yaxis_title="Осадки (мм)",
            xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=[
                'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']),
            margin=dict(l=10, r=10, t=30, b=10)
        )
        return fig

    def make_weather_block(self, *, id_region: Optional[int] = None, id_city: Optional[int] = None) -> dbc.Container:
        """
        Комплексный блок с погодными графиками и summary для города или региона.
        """
        weather_data = self.data_prep.get_weather_data(id_region=id_region, id_city=id_city)
        temp = weather_data.get('temp')
        rainfall = weather_data.get('rainfall')
        water = weather_data.get('water')
        summary = self.data_prep.get_weather_summary(id_region if id_region else id_city)

        has_data = any([
            (df is not None and not df.empty)
            for df in (temp, rainfall, water)
        ])
        if not has_data:
            return dbc.Container(
                dbc.Alert("Нет данных о погоде.", color="secondary"),
                className="mb-4"
            )

        blocks = []
        if temp is not None and not temp.empty:
            temp_fig = self.plot_temperature(temp, water)
            blocks.append(dbc.Col(dcc.Graph(figure=temp_fig), md=8))
        if summary:
            summary_card = self.make_weather_summary_card(summary)
            blocks.append(dbc.Col(summary_card, md=4))
        row_temp = dbc.Row(blocks, className="mb-2") if blocks else None

        rain_row = None
        if rainfall is not None and not rainfall.empty:
            rain_fig = self.plot_rainfall(rainfall)
            rain_row = dbc.Row([dbc.Col(dcc.Graph(figure=rain_fig), md=12)])

        return dbc.Container(
            [row_temp, rain_row] if rain_row else [row_temp],
            className="mb-4"
        )

class RegionPagePlot(BaseDashboardPlot):
    
    def flow_graph_with_year_selector(self, region_id: int) -> html.Div:
        """
        Возвращает Div с Dropdown по годам и графиком турпотока.
        Данные берутся из prepare_data.prepare_tourist_count_data().
        """ 
        df = self.data_prep.prepare_tourist_count_data(id_region = region_id)
        if df.empty or 'year' not in df.columns:
        # Вернуть красивый layout-заглушку
            return html.Div([html.P("Нет данных по турпотоку для выбранного региона/города.")])
        years = sorted(df['year'].unique())
        dropdown = dcc.Dropdown(
            id={'type': 'flow-year-dropdown', 'index': region_id},
            options=[{'label': y, 'value': y} for y in years],
            value=years[-1],
            clearable=False
        )
        graph = dcc.Graph(id={'type': 'flow-graph', 'index': region_id})
        return html.Div([
            html.H4("Турпоток по месяцам"),
            dropdown,
            graph
        ])

    def nights_graph_with_year_selector(self, region_id: int) -> html.Div:
        """
        То же для ночёвок, используя prepare_data.get_region_mean_night().
        """
        rpd = RegionDashboardData()
        # Получаем список доступных годов
        raw = rpd.get_region_mean_night(id_region = region_id)
        if raw.empty or 'year' not in raw.columns:
        # Вернуть красивый layout-заглушку
            return html.Div([html.P("Нет данных по ночевкам для выбранного региона/города.")])
        years = sorted(raw['year'].unique())
        dropdown = dcc.Dropdown(
            id={'type': 'nights-year-dropdown', 'index': region_id},
            options=[{'label': y, 'value': y} for y in years],
            value=years[-1],
            clearable=False
        )
        graph = dcc.Graph(id={'type': 'nights-graph', 'index': region_id})
        return html.Div([
            html.H4("Ночёвки по месяцам"),
            dropdown,
            graph
        ])

    def register_graph_callbacks(self, app_dash: Dash):
        """
        Регистрирует коллбеки обновления графиков по выбору года.
        Должен быть вызван из register_callbacks.
        """
        rpd = RegionDashboardData()

        @app_dash.callback(
            Output({'type': 'flow-graph', 'index': MATCH}, 'figure'),      # СНАЧАЛА все Output'ы
            Input({'type': 'flow-year-dropdown', 'index': MATCH}, 'value'),# затем все Input'ы
            State('url', 'pathname'),  
        )
        def update_flow_chart(year, pathname):
            region_id = int(pathname.split('/')[-1])
            df = rpd.prepare_tourist_count_data(id_region = region_id)
            if df.empty or 'year' not in df.columns or 'month' not in df.columns:
                return go.Figure(
                    layout={"title": "Нет данных по турпотоку за выбранный год"}
                )
            df = df[df['year'] == year].sort_values('month')
            fig = px.bar(df, x='month', y='value',
                         labels={'value': 'Туристы', 'month': 'Месяц'},
                         title=f"Турпоток за {year} год")
            return fig

        @app_dash.callback(
            Output({'type': 'nights-graph', 'index': MATCH}, 'figure'),
            Input({'type': 'nights-year-dropdown', 'index': MATCH}, 'value'),
            State('url', 'pathname'),
        )
        def update_nights_chart(year, pathname):
            region_id = int(pathname.split('/')[-1])
            df = rpd.get_region_mean_night(region_id)
            if df.empty or 'year' not in df.columns or 'month' not in df.columns:
                return go.Figure(
                    layout={"title": "Нет данных по ночевкам за выбранный год"}
                )
            df = df[df['year'] == year].sort_values('month')
            fig = px.line(df, x='Месяц', y='Количество ночевок',
                          title=f"Ночёвки за {year} год")
            return fig

    
    def make_municipalities_map(self, region_id) -> dcc.Graph:
        data_prep = RegionDashboardData()
        # Загрузка границы региона как GeoJSON-объекта
        boundary_feat = data_prep.load_region_boundary(region_id)
        # Табличка муниципалитетов
        muni_df = data_prep.load_municipalities(region_id)
        if muni_df.empty:
            return dcc.Graph(figure={})

        # Функции для размера и цвета
        def pop_size(pop):
            if pop is None or pop < 30_000: return 8
            if pop < 100_000: return 12
            if pop < 500_000: return 16
            if pop < 1_000_000: return 20
            return 24

        def metric_color(val):
            if val is None: return 'gray'
            if val < 3.0: return 'red'
            if val < 4.0: return 'yellow'
            return 'green'

        # Создаём scattermapbox-трейс
        fig = go.Figure(go.Scattermapbox(
            lon=muni_df['lon'],
            lat=muni_df['lat'],
            mode='markers',
            marker=dict(
                size=[pop_size(p) for p in muni_df['population']],
                color=[metric_color(m) for m in muni_df['metric_282']],
                opacity=0.8
            ),
            text=[
                (
                    f'<b><a href="/dashboard/city/{city_id}" target="_blank">{name}</a></b>'
                    f'<br>Население: {format(pop, ",").replace(",", " ") if pop else "—"}'
                    f'<br>Оценка: {m if m is not None else "—"}'
                )
                for city_id, name, pop, m in zip(
                    muni_df['id_city'], muni_df['name'], muni_df['population'], muni_df['metric_282']
                )
            ],
            hoverinfo='text',
            hoverlabel=dict(namelength=-1),  # чтобы не обрезался label
            showlegend=False
        ))

        # Центрирование
        center = {
            'lon': float(muni_df['lon'].mean()),
            'lat': float(muni_df['lat'].mean())
        }

        # Если есть граница — рисуем её как слой
        layers = []
        if boundary_feat:
            # Слой-заливка
            layers.append({
                "source": boundary_feat,
                "type": "fill",            # заливка полигона
                "below": "traces",         # под точками
                "color": "blue",           # цвет заливки
                "opacity": 0.1             # прозрачность 10%
            })
            # Слой контура (по-прежнему)
            layers.append({
                "source": boundary_feat,
                "type": "line",
                "color": "blue",
                "line": {"width": 2}
            })

        # Обновляем layout
        fig.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=center,
                zoom=5,
                layers=layers      # вот здесь подключаем слой границы
            ),
            margin={'l':0,'r':0,'t':0,'b':0},
            height=600
        )

        # Конфиг для кнопок зума
        config = {
            'displayModeBar': True,
            'modeBarButtonsToAdd': ['zoomInMapbox', 'zoomOutMapbox'],
            'modeBarButtonsToRemove': [
                'lasso2d', 'select2d', 'zoomIn2d', 'zoomOut2d',
                'pan2d', 'autoScale2d', 'hoverClosestGeo', 'hoverCompare'
            ]
        }

        return dcc.Graph(figure=fig, config=config)

class SegmentDashboardPlot (BaseDashboardPlot):
    """
    Класс для визуализации KPI одного сегмента туризма.
    """
    def __init__(self, data_prep: BaseDashboardData):
        self.data_prep = data_prep

    def make_segment_kpi_cards(
        self,
        segment_key: str,
        *,
        id_region: Optional[int] = None,
        id_city: Optional[int] = None
    ) -> List[dbc.Row]:
        """
        Формирует layout карточек KPI для выбранного сегмента.
        """
        kpis = self.data_prep.get_segment_kpi(segment_key, id_region=id_region, id_city=id_city)
        if not kpis:
            return [dbc.Row(dbc.Col(dbc.Alert("Нет данных для сегмента", color="secondary")))]

        main_label = 'Главная оценка'
        other_labels = self.data_prep.SEGMENT_METRIC_LABELS[1:4]

        # Главная метрика
        main_value = kpis.get(main_label)
        main_display = f"{main_value:.2f}" if isinstance(main_value, (int, float)) else "—"
        main_card = dbc.Card(
            [
                dbc.CardHeader(main_label, className="text-white fs-5"),
                dbc.CardBody(html.H2(main_display, className="card-title text-white fw-bold"), className="text-center"),
            ],
            color= self._choose_card_color(main_value),
            inverse=True,
            className="mb-3 shadow",
            style={"minHeight": "140px", "fontSize": "1.8rem"}
        )

        # Остальные 3 метрики
        other_cards = []
        for name in other_labels:
            val = kpis.get(name)
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            other_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(name, className="text-white"),
                        dbc.CardBody(html.H4(display, className="card-title text-white")),
                    ],
                    color= self._choose_card_color(val),
                    inverse=True,
                    className="mb-3 shadow-sm",
                    style={"minHeight": "110px"}
                )
            )
        return [
            dbc.Row(dbc.Col(main_card, width={"size": 6, "offset": 3}), className="mb-3"),
            dbc.Row([dbc.Col(card, md=4) for card in other_cards], className="mb-3"),
        ]

    @staticmethod
    def get_location_types_options(segment: str) -> List[Dict[str, str]]:
        """Возвращает список опций для мультивыбора типов локаций lvl1."""
        types = SegmentMapping.get_location_types_for_segment(segment)["lvl1"]
        return [{"label": t, "value": t} for t in types]

    @staticmethod
    def make_layout(
        segment: str,
        initial_rating_range: Tuple[float, float] = (1.0, 5.0),
        region_id: Optional[int] = None,
        city_id: Optional[int] = None
    ) -> html.Div:
        """
       Основной layout с фильтрами, таблицей, кастомной пагинацией и картой.
        """
        store = dcc.Store(id='page-store', data=0)
        types_opts = SegmentDashboardPlot.get_location_types_options(segment)

        return html.Div([
            store,
            dbc.Row([
                dbc.Col([
                    html.Label("Диапазон главной оценки:"),
                    dcc.RangeSlider(
                        id="main-rating-slider",
                        min=1, max=5, step=0.01,
                        value=list(initial_rating_range),
                        marks={i: str(i) for i in range(1, 6)},
                        tooltip={"placement": "bottom", "always_visible": False}
                    ),
                ], md=6),
                dbc.Col([
                    html.Label("Тип локаций:"),
                    dcc.Dropdown(
                        id="location-types-dropdown",
                        options=types_opts,
                        value=[opt["value"] for opt in types_opts],
                        multi=True,
                        placeholder="Выберите типы локаций"
                    ),
                ], md=6),
            ], className="mb-2"),

            # сама таблица, без встроенной пагинации
            dbc.Row([
                dbc.Col(dash_table.DataTable(
                    id="locations-table",
                    columns=[
                        {"name": "Название",            "id": "Название"},
                        {"name": "Главная оценка",      "id": "Главная оценка", "type": "numeric"},
                        {"name": "Количество отзывов",       "id": "Количество отзывов",  "type": "numeric"},
                        {"name": "Средняя оценка Яндекс",      "id": "Средняя оценка Яндекс", "type": "numeric"},
                    ],
                    page_current=0,
                    page_size=10,
                    page_action="none",        # Отключаем встроенные контролы
                    sort_action="custom",
                    sort_mode="single",
                    sort_by=[{"column_id": "Главная оценка", "direction": "desc"}],
                    style_table={"overflowX": "auto"},
                    style_cell={"fontSize": "1rem", "textAlign": "center"},
                    style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                    style_data={"backgroundColor": "#fff"},
                ), md=12)
            ], className="mb-2"),

            # кастомная пагинация, выравненная по центру
            dbc.Row([
                dbc.Col(html.Button("⏮️", id='first-page-btn'), width='auto'),
                dbc.Col(html.Button("−10",  id='minus10-page-btn'), width='auto'),
                dbc.Col(html.Button("◀️",  id='prev-page-btn'),    width='auto'),
                dbc.Col(html.Div(id='page-indicator', style={'padding':'0 1rem'}), width='auto'),
                dbc.Col(html.Button("▶️",  id='next-page-btn'),    width='auto'),
                dbc.Col(html.Button("+10",  id='plus10-page-btn'), width='auto'),
                dbc.Col(html.Button("⏭️", id='last-page-btn'),     width='auto'),
            ], justify="center", className="mb-4 align-items-center"),

            # карта
            dbc.Row([
                dbc.Col(dcc.Loading(dcc.Graph(id="locations-map"), type="circle"), md=12)
            ])
        ])

    @staticmethod
    def register_callbacks(app):
        @app.callback(
        Output("locations-table", "data"),
        Output("locations-table", "page_count"),
        Output("locations-map", "figure"),
        Output("locations-table", "page_current"),
        Output("page-store", "data"),
        Output("page-indicator", "children"),
        # фильтры
        Input("main-rating-slider", "value"),
        Input("location-types-dropdown", "value"),
        # сортировка
        Input("locations-table", "sort_by"),
        # пагинационные кнопки
        Input("first-page-btn",   "n_clicks"),
        Input("prev-page-btn",    "n_clicks"),
        Input("minus10-page-btn", "n_clicks"),
        Input("plus10-page-btn",  "n_clicks"),
        Input("next-page-btn",    "n_clicks"),
        Input("last-page-btn",    "n_clicks"),
        # и URL, чтобы знать сегмент и id
        Input("url", "pathname"),
        # размер страницы
        State("locations-table", "page_size"),
        # текущее положение
        State("locations-table", "page_current"),
        State("page-store", "data"),
        )
        def _update_all(
            rating_range,
            selected_types,
            sort_by,

            first_btn,
            prev_btn,
            m10_btn,
            p10_btn,
            next_btn,
            last_btn,

            pathname,
            page_size,
            page_current,
            stored_page
        ):
            # --- 0) парсим URL как раньше ---
            parts = pathname.rstrip("/").split("/")
            if len(parts) < 6 or parts[2] != "segment":
                # неверный URL
                empty_fig = go.Figure().update_layout(
                    mapbox=dict(style="open-street-map", center=dict(lat=55, lon=37), zoom=3),
                    margin={"l":0,"r":0,"t":0,"b":0}, height=480
                )
                return [], 0, empty_fig, 0, 0, "Страница 0 из 0"

            entity_type, prefix, entity_id = parts[3], parts[4], int(parts[5])
            seg_key = None
            for key, url_pref in BaseDashboardData.get_segment_patterns():
                if url_pref == prefix:
                    seg_key = key
                    break
            if seg_key is None:
                return [], 0, go.Figure(), 0, 0, ""

            # --- 1) какая кнопка нажата? ---
            triggered = callback_context.triggered
            if triggered:
                prop_id = triggered[0].get("prop_id", "")
                trig = prop_id.split(".")[0]
            else:
                trig = None

            page_buttons = [
                "first-page-btn", "prev-page-btn", "minus10-page-btn",
                "plus10-page-btn", "next-page-btn", "last-page-btn"
            ]

            # --- 2) получаем ВСЕ строки по фильтрам (без пагинации) ---
            full = BaseDashboardData.prepare_location_data(
                segment=seg_key,
                rating_range=(rating_range[0], rating_range[1]),
                location_types=selected_types,
                region_id=(entity_id if entity_type=="region" else None),
                city_id=(entity_id if entity_type=="city" else None),
                page=1,
                page_size=10**9,
                sort_by=(sort_by[0]["column_id"] if sort_by else "Главная оценка"),
                sort_order=(sort_by[0]["direction"] if sort_by else "desc")
            )
            all_rows = full["data"]
            total = full["total"]
            page_count = (total + page_size - 1)//page_size if page_size else 1

            # --- 3) пересчитываем page_current по кнопкам ---
            # если хранилище не пустое, берем оттуда
            page_current = stored_page or page_current
            if trig == "first-page-btn":
                page_current = 0
            elif trig == "prev-page-btn":
                page_current = max(page_current - 1, 0)
            elif trig == "minus10-page-btn":
                page_current = max(page_current - 10, 0)
            elif trig == "plus10-page-btn":
                page_current = min(page_current + 10, page_count - 1)
            elif trig == "next-page-btn":
                page_current = min(page_current + 1, page_count - 1)
            elif trig == "last-page-btn":
                page_current = page_count - 1

            # --- 4) готовим данные для текущей страницы ---
            res = BaseDashboardData.prepare_location_data(
                segment=seg_key,
                rating_range=(rating_range[0], rating_range[1]),
                location_types=selected_types,
                region_id=(entity_id if entity_type=="region" else None),
                city_id=(entity_id if entity_type=="city" else None),
                page=page_current + 1,  # prepare 1-based
                page_size=page_size,
                sort_by=(sort_by[0]["column_id"] if sort_by else "Главная оценка"),
                sort_order=(sort_by[0]["direction"] if sort_by else "desc")
            )
            table_data = res["data"]

            # --- 5) строим карту: только при не-пагинационных триггерах ---
            if trig in page_buttons:
                fig = no_update
            else:
                if all_rows:
                    latitudes  = [r["lat"] for r in all_rows if r["lat"] is not None]
                    longitudes = [r["lon"] for r in all_rows if r["lon"] is not None]
                    scores     = [r["Главная оценка"] for r in all_rows]
                    hover_text = [
                        f"<b>{r['Название']}</b><br>"
                        f"Главная: {r['Главная оценка']}<br>"
                        f"Яндекс ср.: {r['Средняя оценка Яндекс']}<br>"
                        f"Отзывы: {r['Количество отзывов']}"
                        for r in all_rows
                    ]
                    fig = go.Figure(go.Scattermapbox(
                        lat=latitudes, lon=longitudes, mode="markers",
                        marker=dict(
                            size=12, color=scores, colorscale="YlGnBu",
                            cmin=1, cmax=5, colorbar=dict(title="Главная оценка")
                        ),
                        text=hover_text, hoverinfo="text"
                    ))
                    fig.update_layout(
                        mapbox=dict(
                            style="open-street-map",
                            center=dict(
                                lat=sum(latitudes)/len(latitudes),
                                lon=sum(longitudes)/len(longitudes)
                            ),
                            zoom=7
                        ),
                        margin={"l":0,"r":0,"t":0,"b":0}, height=480
                    )
                else:
                    fig = go.Figure().update_layout(
                        mapbox=dict(style="open-street-map", center=dict(lat=55, lon=37), zoom=3),
                        margin={"l":0,"r":0,"t":0,"b":0}, height=480
                    )

            # --- 6) индикатор ---
            indicator = f"Страница {page_current+1} из {page_count}"

            return (
                table_data,
                page_count,
                fig,
                page_current,
                page_current,
                indicator
            )