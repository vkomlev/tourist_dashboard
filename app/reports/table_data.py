import pandas as pd
from app.data.database import MetricValueRepository, CitiesRepository
from app.models import Region
from app.logging_config import logger

class Main_page_dashboard:
    @staticmethod
    def process_tourist_count_data(n=10, top=True):
        '''Получение топ N регионов по турпотоку и формирование datafrrame Pandas'''
        db = MetricValueRepository()
        data = db.get_tourist_count_data()

        # Преобразование данных в DataFrame
        df = pd.DataFrame(data, columns=['id_region', 'value','month','year'])
        df['value'] = df['value'].astype(int)

        # Суммарный турпоток по регионам
        df_sum = df.groupby('id_region').sum().reset_index()

        # Получение названий регионов
        region_names = {region.id_region: region.region_name for region in db.get_all(Region)}

        # Добавление названий регионов
        df_sum['region_name'] = df_sum['id_region'].map(region_names)

        # Суммарный турпоток по всем регионам
        total_tourism = df_sum['value'].sum()

        # Вычисление доли в процентах
        df_sum['percentage'] = (df_sum['value'] / total_tourism) * 100

        # Сортировка данных
        df_sum = df_sum.sort_values(by='value', ascending=False)

        # Формирование топ N регионов
        if top:
            final_df = df_sum.head(n).reset_index(drop=True)
        else:
            final_df  = df_sum.tail(n).reset_index(drop=True)

        # Добавление места региона
        final_df['rank'] = final_df.index + 1

        return final_df[['rank', 'region_name', 'value', 'percentage']]

    def generate_heatmap_tourist_count_data(self, n=10):
        '''Генерация сводной таблицы для хитмапа турпотока'''
        db = MetricValueRepository()
        data = db.get_tourist_count_data()

        # Преобразование данных в DataFrame
        df = pd.DataFrame(data, columns=['id_region', 'value', 'month', 'year'])
        df['value'] = df['value'].astype(int)

        # Суммарный турпоток по регионам
        df_sum = df.groupby(['id_region', 'year', 'month']).sum().reset_index()

        # Получение названий регионов
        region_names = {region.id_region: region.region_name for region in db.get_all(Region)}
        df_sum['region_name'] = df_sum['id_region'].map(region_names)

        # Сортировка данных и выбор топ N регионов
        top_regions = df_sum.groupby('id_region')['value'].sum().sort_values(ascending=False).head(n).index
        df_top = df_sum[df_sum['id_region'].isin(top_regions)]

        # Создание столбца для год+месяц
        df_top['year_month'] = df_top.apply(lambda row: f"{row['year']}-{row['month']:02d}", axis=1)

        # Использование метода pivot с именованными аргументами
        return df_top.pivot(index='region_name', columns='year_month', values='value')

class Weather_page_dashboard:
    """
    Работа над даными погоды, а именно температура дневная и ночная,
    количество осадков в мм, температура воды
    "day": 213,
    "night": 214,
    "rainfall": 215,
    "water": 216,
    """
    def __init__(self):
        self.mv = MetricValueRepository()

    def get_city_temp_day_night(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика температуры дневной и ночной в городе'''
        data = self.mv.get_city_weather(id_city=id_city, key_ratio=['day', 'night'])
        df = pd.DataFrame(data, columns=["month", 'day_t', 'night_t'])
        df['month'] = [i for i in range(1,13)]
        day = data.get('day')
        if day:
            # Сортируем по месяцас
            day.sort(key = lambda s: s[1])
            mass_water = []
            for i in day:
                if isinstance(i[0], str):
                    mass_water.append(float(i[0]))
                else:
                    logger.warning(f'В дневной температуре было пустое значение {i} - id_city = {id_city}')
                    return False
        else:
            return False
        df['day_t'] = mass_water
        night = data.get('night')
        if night:
            # Сортируем по месяцас
            night.sort(key = lambda s: s[1])
            mass_water = []
            for i in night:
                if isinstance(i[0], str):
                    mass_water.append(float(i[0]))
                else:
                    logger.warning(f'В ночной температуре было пустое значение {i} - id_city = {id_city}')
                    return False
        else:
            return False
        df['night_t'] = mass_water
        return df

    def get_city_rainfall(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика осадков в городе'''
        data = self.mv.get_city_weather(id_city=id_city, key_ratio=['rainfall'])
        df = pd.DataFrame(data, columns=["month", 'rainfall'])
        df['month'] = [i for i in range(1,13)]
        rainfall = data.get('rainfall')
        if rainfall:
            # Сортируем по месяцас
            rainfall.sort(key = lambda s: s[1])
            mass_water = []
            for i in rainfall:
                if isinstance(i[0], str):
                    mass_water.append(float(i[0]))
                else:
                    logger.warning(f'В осадках было пустое значение {i} - id_city = {id_city}')
                    return False
        else:
            return False
        df['rainfall'] = mass_water
        return df
    
    def get_city_temp_water(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика температуры воды в городе'''
        data = self.mv.get_city_weather(id_city=id_city, key_ratio=['water'])
        df = pd.DataFrame(data, columns=["month", 'water'])
        df['month'] = [i for i in range(1,13)]
        water = data.get('water')
        if water:
            # Сортируем по месяцас
            water.sort(key = lambda s: s[1])
            mass_water = []
            for i in water:
                if isinstance(i[0], str):
                    mass_water.append(float(i[0]))
                else:
                    logger.warning(f'В температуре воды было пустое значение {i} - id_city = {id_city}')
                    return False
        else:
            return False
        df['water'] = mass_water
        return df
    
class City_page_dashboard(Weather_page_dashboard):
    def get_city_weather_summary(self, id_city: int) -> dict:
        """Получаем топ о погоде для указанного города"""
        # Получаем данные о температуре и осадках
        city_temp_df = self.get_city_temp_day_night(id_city)
        city_rainfall_df = self.get_city_rainfall(id_city)
        city_water_temp_df = self.get_city_temp_water(id_city)

        # Создаем словарь для хранения результатов
        weather_summary = {}

        # Получаем названия месяцев
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", 
                        "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", 
                        "Ноябрь", "Декабрь"]

        # 1. Самые теплые месяцы
        city_temp_df['month_name'] = city_temp_df['month'].apply(lambda x: month_names[x - 1])
        warm_months = city_temp_df.nlargest(3, 'day_t')[['month_name', 'day_t']]
        weather_summary['warm_months'] = {row['month_name']: row['day_t'] for index, row in warm_months.iterrows()}

        # 2. Самые холодные месяцы
        cold_months = city_temp_df.nsmallest(3, 'day_t')[['month_name', 'day_t']]
        weather_summary['cold_months'] = {row['month_name']: row['day_t'] for index, row in cold_months.iterrows()}

        # 3. Самые теплые месяцы для моря
        city_water_temp_df['month_name'] = city_water_temp_df['month'].apply(lambda x: month_names[x - 1])
        warm_water_months = city_water_temp_df.nlargest(3, 'water')[['month_name', 'water']]
        weather_summary['warm_water_months'] = {row['month_name']: row['water'] for index, row in warm_water_months.iterrows()}

        # 4. Самые дождливые месяцы
        city_rainfall_df['month_name'] = city_rainfall_df['month'].apply(lambda x: month_names[x - 1])
        rainy_months = city_rainfall_df.nlargest(3, 'rainfall')[['month_name', 'rainfall']]
        weather_summary['rainy_months'] = {row['month_name']: row['rainfall'] for index, row in rainy_months.iterrows()}
        return weather_summary



class Region_page_dashboard(City_page_dashboard):
    def get_region_tourist_flow_data(self, region_id):
        '''Получение данных о турпотоке в регионе'''
        db = MetricValueRepository()
        data = db.get_tourist_count_data_by_region(region_id)

        df = pd.DataFrame(data, columns=['id_region', 'value', 'month', 'year'])
        df['value'] = df['value'].astype(int)
        df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)

        return df[['period', 'value']]
    
    def get_region_average_weather(self, id_region: int) -> pd.DataFrame:
        """Получает усредненные значения погоды по всем городам в регионе."""
        db = CitiesRepository()
        id_cities = [i[0] for i in db.get_cities_in_region(id_region)]
        
        # Создаем пустой DataFrame для хранения данных по всем городам
        all_temps = pd.DataFrame(columns=["month", "day_t", "night_t"])

        for id_city in id_cities:
            # Получение данных о температуре воздуха в городе
            city_temp_df = self.get_city_temp_day_night(id_city)
            if isinstance(city_temp_df, bool):
                continue

            # Получение данных о количестве осадков в городе
            city_rainfall_df = self.get_city_rainfall(id_city)
            if isinstance(city_rainfall_df, bool):
                city_rainfall_df = {'rainfall': [None for i in range(12)]}
                city_rainfall_df = pd.DataFrame(city_rainfall_df)

            # Получение данных о температуре водоемов в городе
            city_water_temp_df = self.get_city_temp_water(id_city)
            if isinstance(city_water_temp_df, bool):
                city_water_temp_df = {'water':[None for i in range(12)]}
                city_water_temp_df = pd.DataFrame(city_water_temp_df)

            # Объединяем данные с общим DataFrame
            city_temp_df['rainfall'] = city_rainfall_df['rainfall']
            city_temp_df['water'] = city_water_temp_df['water']
            # Объединяем данные с общим DataFrame
            all_temps = pd.concat([all_temps, city_temp_df], ignore_index=True)

        # Усредняем данные по месяцам
            average_temps = all_temps.groupby("month").agg({
                'day_t': 'mean', 'night_t': 'mean',  
                'rainfall': 'mean', 'water': 'max'
            }).reset_index()

        return average_temps