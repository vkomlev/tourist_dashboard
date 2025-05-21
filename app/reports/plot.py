#app/reports/plot.py

import seaborn as sns
import matplotlib.pyplot as plt
import os
import plotly.express as px
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, dash_table
import colorlover as cl
from typing import List, Optional
import pandas as pd

from app.data.transform.prepare_data import Main_page_dashboard, Region_page_dashboard, Weather_page_dashboard, City_page_dashboard
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

class Region_page_plot:
        # Интерпретации оценок

    def __init__(self): 
        self.interpretations = { 
            (1.0, 2.0): "Туристская инфраструктура слабо развита, требуется значительное улучшение.", 
            (2.1, 3.0): "Средний уровень, подходит для локальных туристов, но имеет ограничения для международного туризма.", 
            (3.1, 4.0): "Хорошая инфраструктура, пригодная для национальных и международных туристов.", 
            (4.1, 5.0): "Высокий уровень инфраструктуры, готовый к приему большого турпотока и международных мероприятий." 
        }
        self.prepare =  Region_page_dashboard()
 
    # Вспомогательная функция для интерпретации оценок
    def get_interpretation(self, rating): 
        for (low, high), text in self.interpretations.items(): 
            if low <= rating <= high: 
                return text 
        return "Нет данных."
    

    def _choose_card_color(self, val: Optional[float]) -> str:
        """
        Выбирает цвет карточки по значению:
         - None → secondary (серый)
         - < 3.0 → danger (красный)
         - 3.0–4.0 → warning (желтый)
         - > 4.0 → success (зелёный)
        """
        if val is None:
            return "secondary"
        if val < 3.0:
            return "danger"
        if val < 4.0:
            return "warning"
        return "success"

    def make_kpi_cards(self, region_id: int) -> List[dbc.Row]:
        """
        Формирует оптимизированный layout карточек KPI для региона.
        """
        prepare = self.prepare
        METRIC_IDS = prepare.METRIC_IDS

        # 1. Главная метрика — Комплексная оценка (282)
        main_metric_key = 'Комплексная оценка развития туризма'
        main_metric_id = METRIC_IDS[main_metric_key]
        main_value = prepare.fetch_latest_metric_value(main_metric_id, region_id)
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
            style={"minHeight": "140px", "fontSize": "1.8rem"}  # Можно увеличить minHeight/fontSize
        )

        # 2. Три метрики по инфраструктуре
        infra_metrics = [
            ('Средняя оценка отелей и других мест размещения', 218),
            ('Количество отелей и других мест размещения', 240),
            ('Количество кафе, ресторанов и пр. мест питания', 241)
        ]
        infra_cards = []
        for rus_name, code in infra_metrics:
            val = prepare.fetch_latest_metric_value(code, region_id)
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            color = self._choose_card_color(val)
            infra_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(rus_name, className="text-white"),
                        dbc.CardBody(html.H4(display, className="card-title text-white")),
                    ],
                    color=color,
                    inverse=True,
                    className="mb-3 shadow-sm",
                    style={"minHeight": "110px"}
                )
            )

        # 3. Остальные метрики
        # Исключаем главную и инфраструктурные из общего списка
        exclude_keys = [main_metric_key] + [m[0] for m in infra_metrics]
        other_cards = []
        for rus_name, code in METRIC_IDS.items():
            if rus_name in exclude_keys:
                continue
            val = prepare.fetch_latest_metric_value(code, region_id)
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            color = self._choose_card_color(val)
            other_cards.append(
                dbc.Card(
                    [
                        dbc.CardHeader(rus_name, className="text-white"),
                        dbc.CardBody(html.H4(display, className="card-title text-white")),
                    ],
                    color=color,
                    inverse=True,
                    className="mb-3 shadow-sm",
                    style={"minHeight": "110px"}
                )
            )

        # Сборка финального layout
        result = [
            dbc.Row(dbc.Col(main_card, width={"size": 6, "offset": 3}), className="mb-3"),
            dbc.Row([dbc.Col(card, md=4) for card in infra_cards], className="mb-3"),
        ]

        # Разбиваем остальные карточки по 3–4 в ряд
        cols_in_row = 4
        for i in range(0, len(other_cards), cols_in_row):
            row = dbc.Row([dbc.Col(card, md=3) for card in other_cards[i:i+cols_in_row]], className="mb-3")
            result.append(row)

        return result



    def flow_graph_with_year_selector(self, region_id: int) -> html.Div:
        """
        Возвращает Div с Dropdown по годам и графиком турпотока.
        Данные берутся из prepare_data.prepare_tourist_count_data().
        """ 
        df = self.prepare.prepare_tourist_count_data(region_id)
        years = sorted(df['year'].unique())
        dropdown = dcc.Dropdown(
            id='flow-year-dropdown',
            options=[{'label': y, 'value': y} for y in years],
            value=years[-1],
            clearable=False
        )
        graph = dcc.Graph(id='flow-graph')
        return html.Div([
            html.H4("Турпоток по месяцам"),
            dropdown,
            graph
        ])

    def nights_graph_with_year_selector(self, region_id: int) -> html.Div:
        """
        То же для ночёвок, используя prepare_data.get_region_mean_night().
        """
        rpd = Region_page_dashboard()
        # Получаем список доступных годов
        raw = rpd.prepare_tourist_count_data(region_id)
        years = sorted(raw['year'].unique())
        dropdown = dcc.Dropdown(
            id='nights-year-dropdown',
            options=[{'label': y, 'value': y} for y in years],
            value=years[-1],
            clearable=False
        )
        graph = dcc.Graph(id='nights-graph')
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
        rpd = Region_page_dashboard()

        @app_dash.callback(
            Output('flow-graph', 'figure'),
            Input('flow-year-dropdown', 'value'),
            State('url', 'pathname'),
        )
        def update_flow_chart(year, pathname):
            region_id = int(pathname.split('/')[-1])
            df = rpd.prepare_tourist_count_data(region_id)
            df = df[df['year'] == year].sort_values('month')
            fig = px.bar(df, x='month', y='value',
                         labels={'value': 'Туристы', 'month': 'Месяц'},
                         title=f"Турпоток за {year} год")
            return fig

        @app_dash.callback(
            Output('nights-graph', 'figure'),
            Input('nights-year-dropdown', 'value'),
            State('url', 'pathname'),
        )
        def update_nights_chart(year, pathname):
            region_id = int(pathname.split('/')[-1])
            df = rpd.get_region_mean_night(region_id, year)
            fig = px.line(df, x='Месяц', y='Количество ночевок',
                          title=f"Ночёвки за {year} год")
            return fig

    
    def make_municipalities_map(self, region_id) -> dcc.Graph:
        data_prep = Region_page_dashboard()
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
    
    def make_segments_table(self, region_id: int) -> dash_table.DataTable:
        """
        Строит DataTable с оценками сегментов для заданного региона.
        Считывает данные через prepare_data.load_segment_scores().
        """
        # 1) Загружаем данные
        df = Region_page_dashboard().load_segment_scores(region_id)
        # 3) Генерируем градиент
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

        # 4) Собираем и возвращаем DataTable
        return dash_table.DataTable(
            columns=[
                {'name': 'Сегмент', 'id': 'segment', 'type': 'text'},
                {'name': 'Оценка', 'id': 'value',  'type': 'numeric'},
            ],
            data=df.to_dict('records'),
            sort_action='native',
            style_cell={'textAlign': 'center', 'padding': '4px'},
            style_header={'fontWeight': 'bold'},
            style_data_conditional=style_cond,
            page_action='none',
            style_table={'maxHeight': '300px', 'overflowY': 'auto'},
        )

    def plot_region_temperature(self, temp: pd.DataFrame, water: Optional[pd.DataFrame] = None) -> go.Figure:
        """
        Строит график температур по месяцам.

        Args:
            temp (pd.DataFrame): DataFrame с дневной и ночной температурой.
            water (Optional[pd.DataFrame]): DataFrame с температурой воды.

        Returns:
            go.Figure: Plotly-график.
        """
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temp['month'], y=temp['day_t'],
            mode='lines+markers', name='Днём', line=dict(color='orange')
        ))
        fig.add_trace(go.Scatter(
            x=temp['month'], y=temp['night_t'],
            mode='lines+markers', name='Ночью', line=dict(color='blue')
        ))
        if water is not None and not water.empty:
            fig.add_trace(go.Scatter(
                x=water['month'], y=water['water'],
                mode='lines+markers', name='Вода', line=dict(color='cyan')
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

    def plot_region_rainfall(self, rainfall: pd.DataFrame) -> go.Figure:
        """
        Строит график осадков по месяцам.

        Args:
            rainfall (pd.DataFrame): DataFrame с осадками.

        Returns:
            go.Figure: Plotly-график.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=rainfall['month'],
            y=rainfall['rainfall'],
            name='Осадки',
            marker_color='blue'
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

    def make_region_weather_summary_card(self, summary: dict) -> dbc.Card:
        """
        Формирует информационную карточку с саммари по погоде.

        Args:
            summary (dict): Саммари, возвращённое get_region_weather_summary.

        Returns:
            dbc.Card: Карточка Dash Bootstrap.
        """
        if not summary:
            return dbc.Card(
                dbc.CardBody("Нет данных о погоде для региона."),
                color="secondary"
            )

        # Форматирование сезонов для вывода
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

    def make_region_weather_block(self, region_id: int) -> dbc.Container:
        """
        Комплексный блок с погодными графиками и summary для региона.
        Если какой-то тип данных отсутствует, он не отображается.
        """
        data_prep = Region_page_dashboard()
        weather_data = data_prep.get_region_weather_data(region_id)
        temp = weather_data.get('temp')
        rainfall = weather_data.get('rainfall')
        water = weather_data.get('water')
        summary = data_prep.get_region_weather_summary(region_id)

        # Проверка на отсутствие всех данных
        has_data = any([
            (df is not None and not df.empty)
            for df in (temp, rainfall, water)
        ])
        if not has_data:
            return dbc.Container(
                dbc.Alert("Нет данных о погоде для региона.", color="secondary"),
                className="mb-4"
            )

        blocks = []
        if temp is not None and not temp.empty :
            temp_fig = self.plot_region_temperature(
                weather_data['temp'],
                weather_data.get('water')  # water может быть None
            )
            blocks.append(dbc.Col(dcc.Graph(figure=temp_fig), md=8))
        if summary:
            summary_card = self.make_region_weather_summary_card(summary)
            blocks.append(dbc.Col(summary_card, md=4))
        row_temp = dbc.Row(blocks, className="mb-2") if blocks else None

        # График осадков, если есть данные
        rain_row = None
        if weather_data.get('rainfall') is not None:
            rain_fig = self.plot_region_rainfall(weather_data['rainfall'])
            rain_row = dbc.Row([dbc.Col(dcc.Graph(figure=rain_fig), md=12)])

        return dbc.Container(
            [row_temp, rain_row] if rain_row else [row_temp],
            className="mb-4"
        )


class City_page_plot:
    def __init__(self):
        self.wpd = Weather_page_dashboard()
    
    def plot_city_temp_day_night(self, id_city:int) ->plt:
        """Рисует график температуры дневной и ночной по месячно по конкретному городу"""
        df = self.wpd.get_city_temp_day_night(id_city=id_city)

        plt.figure(figsize=(12, 8))
        bar_width = 0.35
        index = df['month']

        plt.bar(index, df['day_t'], bar_width, label='День', color = 'orange')
        plt.bar([i + bar_width for i in index], df['night_t'], bar_width, label='Ночь', color = 'blue')

        plt.xlabel('Месяц')
        plt.ylabel('Температура (°C)')
        plt.title('Дневная и ночная температура')
        plt.xticks([i + bar_width / 2 for i in index], df['month'])
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        # Сохранение графика
        output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f'histogram_city_{id_city}_temperature_day_night.png'))
        plt.close()

    def plot_city_rainfall(self, id_city: int) -> plt:
        """Рисует график осадков в мм по месячно по конкретному городу"""
        df = self.wpd.get_city_rainfall(id_city=id_city)
        plt.figure(figsize=(12, 8))

        if isinstance(df, bool):
            plt.text(0.5, 0.5, 'Данных по осадкам в данном городе нету',
                    fontsize=16, ha='center', va='center', transform=plt.gca().transAxes)
            plt.axis('off')
        else:
            plt.plot(df['month'], df['rainfall'], marker='o', color='blue', label='Осадки', linewidth=2)

            plt.xlabel('Месяц')
            plt.ylabel('Количество осадков (мм)')
            plt.title('Осадки по месяцам')
            plt.xticks(df['month'])
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()

        # Сохранение графика
        output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f'histogram_city_{id_city}_rainfall.png'))
        plt.close()
    
    def plot_city_temp_water(self, id_city: int) -> plt:
        """Рисует график температуры воды по месячно по конкретному городу"""
        df = self.wpd.get_city_temp_water(id_city=id_city)
        plt.figure(figsize=(12, 8))

        if isinstance(df, bool):
            plt.text(0.5, 0.5, 'Данных по температуре водоемов в данном городе нету',
                    fontsize=16, ha='center', va='center', transform=plt.gca().transAxes)
            plt.axis('off')
        else:
            plt.fill_between(df['month'], df['water'], color='blue', alpha=0.5, label='Температура воды')
            plt.plot(df['month'], df['water'], marker='o', color='blue', linewidth=2)

            plt.xlabel('Месяц')
            plt.ylabel('Температура (°C)')
            plt.title('Температура водоемов по месяцам')
            plt.xticks(df['month'])
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()

        # Сохранение графика
        output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f'histogram_city_{id_city}_temperature_water.png'))
        plt.close()

    def create_layout(self, id_city):
        """Создает визуальное представление погодных условий."""
        # Словарь символов для каждого погодного условия
        symbols = {
            'warm': '☀️',  
            'cold': '❄️', 
            'warm_water': '🌊',
            'rainfall': '🌧️' 
        }
        
        # Получаем данные о погоде
        df = City_page_dashboard()
        weather_summary = df.get_city_weather_summary(id_city=id_city)

        # Создаем фигуру и оси для 4 подграфиков
        fig, axs = plt.subplots(2, 2, figsize=(10, 8))  # 2 строки, 2 столбца
        fig.patch.set_facecolor('white')  # Устанавливаем белый фон

        # Определяем условия
        conditions = ['warm', 'cold', 'warm_water', 'rainfall']
        colors = ['orange', 'blue', 'cyan', 'green']  # Цвета для значков

        for ax, condition, color in zip(axs.flatten(), conditions, colors):
            ax.set_facecolor('white')  # Устанавливаем белый фон для каждого подграфика
            ax.axis('off')  # Убираем оси

            # Добавляем значок слева
            ax.text(0.2, 0.5, symbols[condition], fontsize=40, ha='center', va='center', color=color)

            # Получаем соответствующие данные для каждого погодного условия
            data = weather_summary[condition]

            # Добавляем названия месяцев и значения справа от значка
            for i, (month, value) in enumerate(data.items()):
                ax.text(0.5, 0.5 - i * 0.1, f"{month}: {value}°C" if condition != 'rainfall' else f"{month}: {value} мм", 
                        fontsize=12, ha='left', va='center')

        # Устанавливаем общий заголовок
        plt.suptitle('Погода', fontsize=16)

        # Показываем график
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # Убираем лишнее пространство
        plt.show()