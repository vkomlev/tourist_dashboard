#app/data/transform/prepare_data.py

import pandas as pd
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
import json
import os

from typing import Optional, Dict, Any

from app.data.database import MetricValueRepository, CitiesRepository, SyncRepository, RegionRepository
from app.models import Region, City
from app.logging_config import logger
from app.data.calc.base_calc import Region_calc



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

class BaseDashboardData:
    """
    Базовый универсальный класс для подготовки данных о метриках, сегментах и погоде
    для любых сущностей: регион или город.
    """

    METRIC_IDS = {
        'Комплексная оценка развития туризма': 282,
        'Комплексная оценка сегментов': 217,
        'Средняя оценка отелей и других мест размещения': 218,
        'Турпоток (оценка)': 283,
        'Ночёвки (оценка)': 284,
        'Оценка климата': 222,
        'Стоимость туристических услуг': 286,
        'Удаленность от столицы': 285,
        'Количество отелей и других мест размещения': 240,
        'Количество кафе, ресторанов и пр. мест питания': 241,
    }

    SEGMENT_METRICS = {
        'Пляжный': 274,
        'Оздоровительный': 275,
        'Деловой': 276,
        'Паломнический': 277,
        'Познавательный': 278,
        'Семейный': 279,
        'Спортивный': 280,
        'Эко-походный': 281,
    }

    def __init__(self):
        self.mv_repo = MetricValueRepository()
        # Кэш погоды можно реализовать тут, если потребуется
        self._weather_cache: Dict[str, Dict[int, pd.DataFrame]] = {'temp': {}, 'rainfall': {}, 'water': {}}

    def fetch_latest_metric_value(
        self,
        id_metric: int,
        *,
        id_region: Optional[int] = None,
        id_city: Optional[int] = None
    ) -> Optional[float]:
        """
        Получает последнее числовое значение метрики для региона или города.

        Args:
            id_metric (int): Идентификатор метрики.
            id_region (Optional[int]): Идентификатор региона.
            id_city (Optional[int]): Идентификатор города.

        Returns:
            Optional[float]: Последнее значение метрики, либо None.
        """
        try:
            filters = {"id_metric": id_metric}
            if id_region is not None:
                filters["id_region"] = id_region
                filters["id_city"] = None
            if id_city is not None:
                filters["id_city"] = id_city
                filters["id_region"] = None
            mvs = self.mv_repo.get_info_metricvalue(**filters)
            if not mvs:
                return None
            raw = mvs[-1].value
            return float(raw) if raw is not None else None
        except Exception as e:
            logger.warning(f"Ошибка при fetch_latest_metric_value(metric={id_metric}, region={id_region}, city={id_city}): {e}")
            return None

    def get_segment_scores(
        self,
        *,
        id_region: Optional[int] = None,
        id_city: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Получает DataFrame с оценками сегментов туризма для региона или города.

        Args:
            id_region (Optional[int]): Идентификатор региона.
            id_city (Optional[int]): Идентификатор города.

        Returns:
            pd.DataFrame: Таблица сегментов и оценок.
        """
        records = []
        for name, metric_id in self.SEGMENT_METRICS.items():
            val = self.fetch_latest_metric_value(metric_id, id_region=id_region, id_city=id_city)
            records.append({
                'segment': name,
                'value': f"{val:.2f}" if val is not None else "—"
            })
        df = pd.DataFrame(records)
        return df.sort_values('value', ascending=False).reset_index(drop=True)

    def _get_city_temp_day_night(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика температуры дневной и ночной в городе'''
        if id_city in self._weather_cache.get('temp',{}):
            return self._weather_cache['temp'][id_city]
        # Получаем данные о температуре воздуха в городе
        data = self.mv_repo.get_city_weather(id_city=id_city, key_ratio=['day', 'night'])
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
        self._weather_cache['temp'][id_city] = df
        return df

    def _get_city_rainfall(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика осадков в городе'''
        if id_city in self._weather_cache.get('rainfall',{}):
            return self._weather_cache['rainfall'][id_city]
        # Получаем данные о температуре воздуха в городе
        data = self.mv_repo.get_city_weather(id_city=id_city, key_ratio=['rainfall'])
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
        self._weather_cache['rainfall'][id_city] = df
        return df
    
    def _get_city_temp_water(self, id_city: int) -> pd.DataFrame:
        '''Получает данные для графика температуры воды в городе'''
        if id_city in self._weather_cache.get('water',{}):
            return self._weather_cache['water'][id_city]
        # Получаем данные о температуре воды в городе
        data = self.mv_repo.get_city_weather(id_city=id_city, key_ratio=['water'])
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
        self._weather_cache['water'][id_city] = df
        return df

    def _get_weather_by_city(self, id_city: Optional[int]) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Вспомогательный метод: возвращает погодные данные по id_city.
        """
        if id_city is None:
            logger.warning("Не удалось определить id_city для погодных данных.")
            return {"temp": None, "rainfall": None, "water": None}
        temp = self._get_city_temp_day_night(id_city)
        rainfall = self._get_city_rainfall(id_city)
        water = self._get_city_temp_water(id_city)
        return {
            "temp": temp if isinstance(temp, pd.DataFrame) and not temp.empty else None,
            "rainfall": rainfall if isinstance(rainfall, pd.DataFrame) and not rainfall.empty else None,
            "water": water if isinstance(water, pd.DataFrame) and not water.empty else None
        }
    
    def get_weather_summary(self, weather_data: Dict[str, Optional[pd.DataFrame]]) -> Optional[Dict[str, Any]]:
        """
        Формирует summary по погоде по универсальным данным (используется и для города, и для региона).
        """
        temp = weather_data.get("temp")
        rainfall = weather_data.get("rainfall")
        water = weather_data.get("water")

        if temp is None or temp.empty or 'month' not in temp.columns:
            return None

        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август",
                  "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

        temp = temp[temp['month'].apply(lambda x: isinstance(x, (int, float)) and 1 <= int(x) <= 12)].copy()
        temp['month'] = temp['month'].astype(int)
        temp['month_name'] = temp['month'].apply(lambda x: months[x - 1])

        summary = {}
        if not temp.empty:
            warm = temp.nlargest(3, 'day_t')[['month_name', 'day_t']]
            summary['warm'] = {row['month_name']: row['day_t'] for _, row in warm.iterrows()}
            cold = temp.nsmallest(3, 'day_t')[['month_name', 'day_t']]
            summary['cold'] = {row['month_name']: row['day_t'] for _, row in cold.iterrows()}
            summary['t_min'] = float(temp['day_t'].min())
            summary['t_max'] = float(temp['day_t'].max())
            summary['t_mean'] = float(temp['day_t'].mean())
        else:
            summary['warm'] = {}
            summary['cold'] = {}
            summary['t_min'] = summary['t_max'] = summary['t_mean'] = None

        if rainfall is not None and not rainfall.empty and 'month' in rainfall.columns and 'rainfall' in rainfall.columns:
            rainfall = rainfall[rainfall['month'].apply(lambda x: isinstance(x, (int, float)) and 1 <= int(x) <= 12)].copy()
            rainfall['month'] = rainfall['month'].astype(int)
            rainfall['month_name'] = rainfall['month'].apply(lambda x: months[x - 1])
            rain = rainfall.nlargest(3, 'rainfall')[['month_name', 'rainfall']]
            summary['rainfall'] = {row['month_name']: row['rainfall'] for _, row in rain.iterrows()}
        else:
            summary['rainfall'] = {}

        if water is not None and not water.empty and 'month' in water.columns and 'water' in water.columns:
            water = water[water['month'].apply(lambda x: isinstance(x, (int, float)) and 1 <= int(x) <= 12)].copy()
            water['month'] = water['month'].astype(int)
            water['month_name'] = water['month'].apply(lambda x: months[x - 1])
            warm_water = water.nlargest(3, 'water')[['month_name', 'water']]
            summary['warm_water'] = {row['month_name']: row['water'] for _, row in warm_water.iterrows()}
            swim = water[water['water'] > 18]
            summary['swimming_season'] = [row['month_name'] for _, row in swim.iterrows()]
        else:
            summary['warm_water'] = {}
            summary['swimming_season'] = []

        return summary
    
    def prepare_tourist_count_data(
        self,
        *,
        id_region: Optional[int] = None,
        id_city: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Универсальный метод подготовки данных по турпотоку для региона или города.
        """
        try:
            repository = MetricValueRepository()
            if id_region is not None:
                data = repository.get_region_metric_value(id_region=id_region, id_metric=2)
                columns = ["id_region", "value", "month", "year"]
            elif id_city is not None:
                data = repository.get_city_metric_value(id_city=id_city, id_metric=2)
                columns = ["id_city", "value", "month", "year"]
            else:
                return pd.DataFrame()  # нет входных данных

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data, columns=columns)
            df['value'] = df['value'].astype(int)
            df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)
            df_grouped = df.groupby(['year', 'month'], as_index=False).sum()
            logger.debug(f"Подготовлены данные для гистограммы (region={id_region}, city={id_city}).")
            return df_grouped

        except Exception as e:
            logger.error(f"Ошибка при подготовке данных для потока (region={id_region}, city={id_city}): {e}")
            return pd.DataFrame()

    
    def get_kpi_metrics(
        self,
        *,
        id_region: Optional[int] = None,
        id_city: Optional[int] = None
    ) -> Dict[str, Optional[float]]:
        """
        Получает словарь KPI-метрик для региона или города.

        Args:
            id_region (Optional[int]): Идентификатор региона.
            id_city (Optional[int]): Идентификатор города.

        Returns:
            Dict[str, Optional[float]]: Словарь {имя_метрики: значение}.
        """
        result = {}
        for rus_name, code in self.METRIC_IDS.items():
            val = self.fetch_latest_metric_value(code, id_region=id_region, id_city=id_city)
            result[rus_name] = val
        return result
    
class CityDashboardData(BaseDashboardData):

    def get_weather_data(self, *, id_city: int, id_region: Optional[int] = None) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Возвращает погодные данные для города (по id города).
        """
        return self._get_weather_by_city(id_city)
    
    def get_weather_summary(self, id_city: int) -> Optional[Dict[str, Any]]:
        weather_data = self.get_weather_data(id_city = id_city)
        return super().get_weather_summary(weather_data)



class RegionDashboardData(BaseDashboardData):
    def __init__(self):
        super().__init__()
        self.region_repo = RegionRepository()

    def get_capital_city_id(self, id_region: int) -> Optional[int]:
        region = self.region_repo.find_region_by_id(id_region)
        return region.capital if region and region.capital else None

    def get_weather_data(self, *, id_region: int, id_city: Optional[int] = None) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Возвращает погодные данные для региона (по столице региона).
        """
        capital_city_id = self.get_capital_city_id(id_region)
        return self._get_weather_by_city(capital_city_id)
    
    def get_weather_summary(self, id_region: int) -> Optional[Dict[str, Any]]:
        weather_data = self.get_weather_data(id_region = id_region)
        return super().get_weather_summary(weather_data)
  
    
    def get_region_mean_night(self, 
                         id_region:int,
                         year:int):
        """Получение данных для графика среднего количества ночевок"""
        month ={1: 'Январь', 
                2: 'Февраль', 
                3: 'Март', 
                4: 'Апрель', 
                5: 'Май', 
                6: 'Июнь', 
                7: 'Июль', 
                8: 'Август', 
                9: 'Сентябрь', 
                10: 'Октябрь', 
                11: 'Ноябрь', 
                12: 'Декабрь'}
        # получаем количество ночевок и преобразуем в словарь
        dp = MetricValueRepository()
        night = dp.get_region_metric_value(
                id_region=id_region,
                id_metric=3
                )
        night = [i for i in night if int(i[3]) == year]
        filter_night = {'night':[],
                        'month':[]
                        }
        for i in range(len(night)):
            long = len(night)
            if i != long - 1:
                filter_night['night'].insert(
                    0,
                    int(night[long-1-i][1])-
                    int(night[long-2-i][1]))
                filter_night['month'].insert(0, night[long-1-i][2])
            else:
                filter_night['night'].insert(0, int(night[0][1]))
                filter_night['month'].insert(0, night[0][2])
        # получаем турпоток и преобразуем в словарь
        # через турпоток сделать процентное отношение к ночевкам и так разделить их по месячно
        tourist = dp.get_region_metric_value(
                id_region=id_region,
                id_metric=2
                )
        filter_tourist = {'tourist':[],
                          'month':[]
                          }
        tourist = [i for i in tourist if int(i[3]) == year]
        for i in tourist:
            filter_tourist['tourist'].append(int(i[1]))
            filter_tourist['month'].append(i[2])

        # распределяем количество ночевок по месяцам, основываясь на распеределии турпотока
        # в процентах по сезонам
        filter_tourist_night = {'Количество ночевок':[],
                                'Месяц':[]
                                }
        for x in filter_night['month']:
            mass_tour = sum(filter_tourist['tourist'][x-3: x])
            for y in range(x-3, x):
                month_night = float(filter_night['night'][(x//3)-1]*(filter_tourist['tourist'][y]/mass_tour))
                mean_night = (month_night/filter_tourist['tourist'][y])
                filter_tourist_night['Количество ночевок'].append(mean_night)
                filter_tourist_night['Месяц'].append(month[y+1])
        df = pd.DataFrame(filter_tourist_night)
        return df
    
    def get_region_leisure_rating(self, id_region):
        dp = Region_calc(id_region=id_region) 
        result_segment = dp.get_segment_scores() 
        df = pd.DataFrame( 
            { 
            'Название сегмента':list(result_segment.keys()), 
            'Оценка':list(result_segment.values()) 
            } 
            ).sort_values('Оценка') 
        return df
    
    def region_overall_calculation(self, id_region):
        # Рассчитываем общие показатели
        region_calc = Region_calc(id_region)
        overall_metrics = region_calc.get_overall_metrics()
        segment_scores = region_calc.get_segment_scores()
        return overall_metrics, segment_scores
    
    def load_region_boundary(self, region_id: int) -> Optional[Dict[str, Any]]:
        """
        Читает файл app/files/regions.geojson и возвращает GeoJSON Feature
        для заданного region_id. Если не найдено — None.
        """
        path = os.path.join(os.getcwd(), 'app', 'files', 'regions.geojson')
        if not os.path.exists(path):
            return None
        sync_repo = SyncRepository()
        with open(path, 'r', encoding='utf-8') as f:
            gj = json.load(f)

        for feat in gj.get('features', []):
            region_name = feat.get('properties', {}).get('name:ru', {}) or feat.get('name:ru', {})
            id = sync_repo.find_id(region_name, 'region', 'OSM')
            if id == region_id:
                return feat
        return None


    def load_municipalities(self, region_id: int) -> pd.DataFrame:
        """
        Возвращает DataFrame с городами региона и колонками:
        ['id_city','name','lon','lat','population','metric_282'].
        """
        # 1) получаем все города региона
        cities_repo = CitiesRepository()
        cities = cities_repo.get_by_fields(model=City, id_region=region_id)
        
        # 2) подготовка списков
        records = []
        mv_repo = MetricValueRepository()
        for city in cities:
            # имя
            name = city.city_name

            # координаты
            coords = None
            if city.coordinates:
                geom: Point = to_shape(city.coordinates)
                coords = (geom.x, geom.y)
            lon, lat = coords if coords else (None, None)

            # population из JSONB characters
            pop = None
            if city.characters:
                pop_raw = city.characters.get('population')
                try:
                    pop = int(pop_raw)
                except Exception:
                    pop = 0

            # метрика 282 для этого города (берем последнее значение)
            metric_val = None
            mvs = mv_repo.get_info_metricvalue(id_metric=282, id_city=city.id_city, id_location=None)
            if mvs and mvs[-1].value is not None:
                try:
                    metric_val = float(mvs[-1].value)
                except Exception:
                    metric_val = None

            records.append({
                'id_city': city.id_city,
                'name': name,
                'lon': lon,
                'lat': lat,
                'population': pop,
                'metric_282': metric_val
            })

        df = pd.DataFrame(records)
        return df
    
    def load_segment_scores(self, region_id: int) -> pd.DataFrame:
        """
        Возвращает DataFrame с оценками T_segment для каждого туристического сегмента.
        Колонки: ['segment', 'value'].
        """
        mv_repo = MetricValueRepository()
        records = []
        for name, metric_id in self.SEGMENT_METRICS.items():
            mvs = mv_repo.get_info_metricvalue(id_region=region_id, id_metric=metric_id, id_city=None, id_location=None)
            val = None
            if mvs and mvs[-1].value is not None:
                try:
                    val = float(mvs[-1].value)
                except:
                    val = None
            records.append({'segment': name, 'value': val})
        df = pd.DataFrame(records)
        df['value'] = df['value'].map(lambda v: f"{v:.2f}" if pd.notnull(v) else "—")
        return df.sort_values('value', ascending=False).reset_index(drop=True)
    
    