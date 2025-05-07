import seaborn as sns
import matplotlib.pyplot as plt
import os
import pandas as pd
import plotly.express as px
import random
from dash import Dash, html, dcc, Input, Output

from app.data.transform.prepare_data import Main_page_dashboard, Region_page_dashboard, Weather_page_dashboard, City_page_dashboard
from app.data.database.models_repository import MetricValueRepository
from app.logging_config import logger
from app.data.score.base_assessment import OverallTourismEvaluation 


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
 
    # Вспомогательная функция для интерпретации оценок
    def get_interpretation(self, rating): 
        for (low, high), text in self.interpretations.items(): 
            if low <= rating <= high: 
                return text 
        return "Нет данных."
    
    def plot_region_flow_histogram(self, region_id, region_name):
            rpd = Region_page_dashboard()
            df = rpd.get_region_tourist_flow_data(region_id)

            plt.figure(figsize=(12, 8))
            plt.bar(df['period'], df['value'], color='blue')
            plt.xlabel('Период (год-месяц)')
            plt.ylabel('Турпоток')
            plt.title(f'Турпоток по региону: {region_name}')
            plt.xticks(rotation=90)

            # Сохранение графика
            output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(os.path.join(output_dir, f'histogram_flow_{region_id}.png'))
            plt.close()
 

    def plot_region_dynamics_tourist(self, id_region, year):
        """График турпотока для нескольких годов"""
        dp = MetricValueRepository()
        tur = dp.get_region_metric_value(region_id=id_region)
        df = {
            'x': [i[2] for i in tur],
            'y': [i[1] for i in tur],
            'month': [i[2] for i in tur],
            'year': [i[3] for i in tur]
              }
        df = pd.DataFrame(df)
        df = df[df['year'] == int(year)].sort_values('month')
        # df = df['x'].to_dict()|df['y'].to_dict()
        fig = px.line(df, x='x', y='y').show()
        return fig
    
    def plot_region_night(self, 
                          id_region:int,
                          year:int
                          ):
        dp = Region_page_dashboard()
        df = dp.get_region_mean_night(id_region=id_region, year=year)
        logger.debug(f"Данные для графика: {df.head(12)}")
        # logger.debug(f"Данные для графика: {df.info()}")
        fig_night = px.bar(df, x='Месяц', y='Количество ночевок', title='Количество ночевок на туриста в регионе') 
        return fig_night
    
    def plot_region_leisure_rating(self, id_region):
        dp = Region_page_dashboard()
        df = dp.get_region_leisure_rating(id_region=id_region)
        fig_segmetns = px.bar(df, x='Оценка', y='Название сегмента', title='Топ сегментов туризма') 
        return fig_segmetns
    
    def create_tabs_layout(self, region_id: int):
        """
        Создает Dash layout с вкладками по годам.

        Args:
            region_id (int): Идентификатор региона.

        Returns:
            html.Div: Макет с вкладками.
        """
        try:
            # Получаем данные и формируем список годов
            rd = Region_page_dashboard()
            df = rd.prepare_tourist_count_data(region_id=region_id)
            years = df['year'].unique()

            # Генерируем вкладки по годам
            tabs = dcc.Tabs(
                id='year-tabs',
                value=str(years[0]),
                children=[
                    dcc.Tab(label=str(year), value=str(year)) for year in years
                ]
            )
            return html.Div([
                html.H3("Динамика турпотока по годам"),
                tabs,
                dcc.Graph(id='tourist-flow-chart')  # Пустой график
            ])
        except Exception as e:
            logger.error(f"Ошибка при создании вкладок: {e}")
            return html.Div([html.H3("Ошибка загрузки данных")])

    def create_tourist_flow_chart(self, region_id: int, year: int) -> dict:
        """
        Генерирует график турпотока для выбранного года.

        Args:
            region_id (int): Идентификатор региона.
            year (int): Год.

        Returns:
            dict: Объект figure для Plotly.
        """
        try:
            # Получаем данные
            rd = Region_page_dashboard()
            df = rd.prepare_tourist_count_data(region_id=region_id)

            # Фильтруем по году
            df_year = df[df['year'] == year]

            # Генерируем график
            fig = px.bar(
                df_year,
                x='month',
                y='value',
                title=f"Туристический поток в {year} году",
                labels={'value': 'Количество туристов', 'month': 'Месяц'}
            )
            logger.debug(f"Создан график турпотока для региона {region_id} за {year} год.")
            return fig
        except Exception as e:
            logger.error(f"Ошибка при построении графика: {e}")
            return {}
    
    def create_region_header(self, region_name: str):
        return html.H2(f"Регион: {region_name}")

    def create_rating_section(self, id_region):
        rd = Region_page_dashboard()
        overall_metrics, segment_scores = rd.region_overall_calculation(id_region)
        fig_segments = self.plot_region_leisure_rating(id_region)
        overall = OverallTourismEvaluation(**overall_metrics)
        rating = overall.calculate_overall_score()
        stars = '★' * int(rating) + '☆' * (5 - int(rating))
        description = self.get_interpretation(rating)
        country_rank = f"место по стране 50" 
        macro_rank = f"Место по макрорегиону 50"  
        return html.Div([
            html.H2(f"Рейтинг: {rating:.1f} {stars}"),
            dcc.Graph(figure=fig_segments),
            html.P(description),
            html.P(country_rank), 
            html.P(macro_rank),
        ],)

    def create_details_section(self, id_region):
        rd = Region_page_dashboard()
        overall_metrics, segment_scores = rd.region_overall_calculation(id_region)
        overall = OverallTourismEvaluation(**overall_metrics)
        rating = overall.calculate_overall_score()
        detail = (
                f" Подробный расчет: \n Ttotal = 0.4 * {overall.segment_scores} + 0.2 * "
                f" {overall.general_infra} + 0.1 * {overall.safety} +  0.1 * {overall.flow}" 
                f"+ 0.05 * {overall.nights} + 0.05 * {overall.climate} + 0.05 * {overall.prices} + 0.05 * {overall.distance} = {rating:.2f}"
        )
        return html.Pre(detail)
    
    def create_night_count_section(self, id_region, year):
        fig_night = self.plot_region_night(id_region, year)
        return html.Div([dcc.Graph(figure = fig_night)])


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