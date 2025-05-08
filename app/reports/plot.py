import seaborn as sns
import matplotlib.pyplot as plt
import os
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import random
from dash import Dash, html, dcc, Input, Output
from typing import List, Optional, Tuple

from app.data.transform.prepare_data import Main_page_dashboard, Region_page_dashboard, Weather_page_dashboard, City_page_dashboard
from app.data.database.models_repository import MetricValueRepository
from app.logging_config import logger
from app.data.score.base_assessment import OverallTourismEvaluation 
from app.data.metric_codes import METRIC_CODE_MAP, get_metric_code
from app.data.database.models_repository import MetricValueRepository


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
    
    def fetch_latest_value(self,
        repo: MetricValueRepository,
        id_metric: int,
        id_region: int
    ) -> Optional[float]:
        """
        Возвращает последнее числовое значение метрики для заданного региона.

        Args:
            repo: экземпляр MetricValueRepository.
            id_metric: код метрики.
            id_region: ID региона.

        Returns:
            Последнее значение value в виде float, или None.
        """
        try:
            mvs = repo.get_info_metricvalue(id_metric=id_metric, id_region=id_region)
            if not mvs:
                return None
            raw = mvs[-1].value
            return float(raw) if raw is not None else None
        except Exception as e:
            logger.warning("Ошибка при fetch_latest_value(metric=%s, region=%s): %s",
                        id_metric, id_region, e)
            return None


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

    def make_kpi_cards(self, region_id: int, repo: MetricValueRepository) -> List[dbc.Col]:
        """
        Формирует список карточек KPI для всех метрик из METRIC_CODE_MAP
        с цветовой градацией оценки.
        """
        cards: List[dbc.Col] = []
        for key, (code, rus_name) in METRIC_CODE_MAP.items():
            val = self.fetch_latest_value(repo, code, region_id)
            display = f"{val:.2f}" if isinstance(val, (int, float)) else "—"
            color = self._choose_card_color(val)

            card = dbc.Card(
                [
                    dbc.CardHeader(rus_name, className="text-white"),
                    dbc.CardBody(html.H4(display, className="card-title text-white")),
                ],
                color=color,
                inverse=True,  # делает фон карточки цветным, текст светлым
                className="mb-3 shadow-sm",
            )
            cards.append(dbc.Col(card, xs=12, sm=6, md=4, lg=3))
        return cards


    def make_flow_figure(self, region_id: int, repo: MetricValueRepository) -> dict:
        """
        Строит Plotly-figure с абсолютным турпотоком по месяцам за последний год.

        Args:
            region_id: ID региона.
            repo: репозиторий для доступа к metric_values.

        Returns:
            Словарь-figure для dcc.Graph.
        """
        ABS_FLOW_CODE = 2
        try:
            mvs = repo.get_info_metricvalue(id_metric=ABS_FLOW_CODE, id_region=region_id)
            df = pd.DataFrame([
                {"year": mv.year, "month": mv.month, "value": float(mv.value)}
                for mv in mvs if mv.year is not None and mv.month is not None and mv.value is not None
            ])
            if df.empty:
                return {}
            last_year = int(df["year"].max())
            df = df[df["year"] == last_year].sort_values("month")
            fig = px.bar(
                df,
                x="month",
                y="value",
                title=f"Турпоток (абс.) за {last_year} год",
                labels={"value": "Туристы, чел.", "month": "Месяц"}
            )
            return fig.to_dict()
        except Exception as e:
            logger.error("Ошибка при построении flow_figure для региона %s: %s", region_id, e)
            return {}


    def make_nights_figure(self, region_id: int, repo: MetricValueRepository) -> dict:
        """
        Строит Plotly-figure с абсолютными ночёвками по месяцам за последний год.

        Args:
            region_id: ID региона.
            repo: репозиторий для доступа к metric_values.

        Returns:
            Словарь-figure для dcc.Graph.
        """
        ABS_NIGHTS_CODE = 3
        try:
            mvs = repo.get_info_metricvalue(id_metric=ABS_NIGHTS_CODE, id_region=region_id)
            df = pd.DataFrame([
                {"year": mv.year, "month": mv.month, "value": float(mv.value)}
                for mv in mvs if mv.year is not None and mv.month is not None and mv.value is not None
            ])
            if df.empty:
                return {}
            last_year = int(df["year"].max())
            df = df[df["year"] == last_year].sort_values("month")
            fig = px.line(
                df,
                x="month",
                y="value",
                title=f"Ночёвки (абс.) за {last_year} год",
                labels={"value": "Ночёвки, чел.-дней", "month": "Месяц"}
            )
            return fig.to_dict()
        except Exception as e:
            logger.error("Ошибка при построении nights_figure для региона %s: %s", region_id, e)
            return {}


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