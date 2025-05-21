#app/reports/plot.py

import seaborn as sns
import matplotlib.pyplot as plt
import os
import plotly.express as px
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, dash_table, MATCH
import colorlover as cl
from typing import List, Optional
import pandas as pd

from app.data.transform.prepare_data import Main_page_dashboard, BaseDashboardData, RegionDashboardData, CityDashboardData
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
            infra_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(name, className="text-white"),
                        dbc.CardBody(html.H4(display, className="card-title text-white")),
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
            other_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(name, className="text-white"),
                        dbc.CardBody(html.H4(display, className="card-title text-white")),
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
        df = self.data_prep.get_segment_scores(id_region=id_region, id_city=id_city)
        colors = cl.scales['5']['div']['RdYlGn']
        style_cond = []
        for i, cell in enumerate(df['value']):
            try:
                num = float(cell)
                frac = (num - 1.0) / 4.0
                idx = min(int(frac * (len(colors)-1)), len(colors)-1)
                bg = colors[idx]
            except:
                bg = 'lightgray'
            style_cond.append({
                'if': {'row_index': i, 'column_id': 'value'},
                'backgroundColor': bg,
                'color': 'black'
            })
        
        return dash_table.DataTable(
            columns=[
                {'name': 'Сегмент', 'id': f'segment', 'type': 'text'},
                {'name': 'Оценка', 'id': f'value',  'type': 'numeric'},
            ],
            data=df.to_dict('records'),
            sort_action='native',
            style_cell={'textAlign': 'center', 'padding': '4px'},
            style_header={'fontWeight': 'bold'},
            style_data_conditional=style_cond,
            page_action='none',
            style_table={'maxHeight': '300px', 'overflowY': 'auto'},
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
                f"{n}<br>Население: {pop or '—'}<br>Оценка: {m or '—'}"
                for n, pop, m in zip(muni_df['name'], muni_df['population'], muni_df['metric_282'])
            ],
            hoverinfo='text',
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
    
 