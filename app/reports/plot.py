import seaborn as sns
import matplotlib.pyplot as plt
from app.reports.table_data import Main_page_dashboard, Region_page_dashboard, Weather_page_dashboard, City_page_dashboard
from app.data.database import MetricValueRepository
import os
import pandas as pd
import plotly.express as px
import random
from dash import Dash, html, dcc, Input, Output

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

    def plot_region_leisure_rating(self, id_region):
        # перенести из дэш
        pass

    def plot_region_dynamics_tourist(self, 
                                     id_region:int, 
                                     year:int
                                     ):
        """График турпотока для нескольких годов"""
        dp = MetricValueRepository()
        # Запрашиваем данные по турпотоку
        tur = dp.get_region_metric_value(
            id_region=id_region, 
            id_metric= 2)
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
                          id_region:int
                          ):
        dp = Region_page_dashboard()
        df = dp.get_region_night(id_region=id_region)
        


    # def plot_region_leisure_rating(self, id_region):
    #     # Не используется уже
    #     leisure_data = id_region
    #     # ЗАГЛУШКА
    #     leisure_data = {
    #         'Пляжный отдых': 4.5,
    #         'Деловой': 3.8,
    #         'Оздоровительный туризм': 0,
    #         'Экстремальный туризм': 4.9,
    #         'Паломнический': None,
    #         'Познавательный': 3.2,
    #         'Экологический': None,
    #         'Экскурсионный': None
    #     }

    #     # Заменяем отсутствующие или равные 0 оценки на случайную из диапазона [2:4]
    #     for leisure_name, rating in leisure_data.items():
    #         if rating is None or rating == 0:
    #             leisure_data[leisure_name] = random.choice([2, 3, 4])

    #     # Сортируем данные по возростанию
    #     sorted_leisure_data = dict(sorted(leisure_data.items(), key=lambda item: item[1]))

    #     # Разделяем ключи и значения на два отдельных списка
    #     leisure_names = list(sorted_leisure_data.keys())
    #     ratings = list(sorted_leisure_data.values())

    #     # Создаем график
    #     plt.barh(leisure_names, ratings, color='skyblue')
    #     plt.xlabel('Оценка')
    #     plt.title('Развитость вида отдыха в Регионе')
    #     plt.show()

    # def plot_region_results_card(self, id_region):
    #     # Не используется уже
    #     # ЗАГЛУШКА
    #     results_data = {
    #         'Итог 1': {
    #             'Под итог 1': 312,
    #             'Под итог 2': 12,
    #             'Под итог 3': 312
    #         },
    #         'Итог 2': 456,
    #         'Итог 3': 456,
    #         'Итог 4': 456,
    #         '':''
    #     }

    #     # Создаем пустой список для строк данных
    #     data = []

    #     # Итерируем по данным и добавляем их в список строк данных
    #     for label, value in results_data.items():
    #         if isinstance(value, dict):
    #             data.append(f"{label}:")
    #             for sub_label, sub_value in value.items():
    #                 data.append(f"{''.join(['  ' for i in range(len(label))])}{sub_label} - {sub_value}")
    #         else:
    #             data.append(f"{label} - {value}")

    #     # Определяем количество строк на карточке
    #     num_rows = len(data) // 2 + len(data) % 2

    #     # Определяем количество столбцов на карточке
    #     num_cols = 2

    #     # Создаем фигуру и оси с уменьшенным размером и уменьшенным расстоянием между строк и столбцами
    #     fig = plt.figure(figsize=(8, num_rows * 0.5))
    #     gs = fig.add_gridspec(num_rows, num_cols, hspace=0.05, wspace=0.02)
    #     ax = gs.subplots(sharex=True, sharey=True)

    #     # Итерируем по элементам и добавляем их на карточку с выравниванием по левому краю
    #     row = 0
    #     col = 0
    #     for line in data:
    #         ax[row, col].text(0.05, 0.5, line, fontsize=12, ha='left', va='center')
    #         ax[row, col].axis('off')
    #         row += 1
    #         if row == num_rows:
    #             row = 0
    #             col += 1

    #     # Добавляем заголовок
    #     fig.suptitle('Результаты', fontsize=16)

    #     # Отображаем карточку
    #     plt.tight_layout()
    #     plt.show()
    

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