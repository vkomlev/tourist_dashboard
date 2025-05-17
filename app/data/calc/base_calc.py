from app.logging_config import logger
from app.data.database.models_repository import (MetricValueRepository, 
                                                 MetricRepository, 
                                                 ReviewRepository, 
                                                 CitiesRepository, 
                                                 LocationsRepository,
                                                 RegionRepository)
import random
import pandas as pd
import re
from app.data.imports.import_json import import_json_file

class Calc:
    pass

class Region_calc(Calc):
    def __init__(self, id_region = None, id_city = None):
        self.id_region = int(id_region) if id_region and not id_city else None
        self.id_city = int(id_city) if id_city else None
        # if self.id_city and self.id_region:
        #     raise ValueError('Нельзя указывать одновременно id_city и id_region')

    def get_overall_metrics(self)->dict:
        """
        Получение нужных метрик для оценки туризма как отросли в Регионе
            Определение собираемых метрик:
            segment_scores - Средняя оценка всех сегментов туризма
            general_infra - Средняя оценка общей инфраструктуры
            safety - Средняя оценка безопасности
            flow - Средняя оценка турпотока
            nights - Средняя оценка количества ночевой
            climate - Средняя оценка климата
            prices - Средняя оценка цен
            distance - Средняя оценка доступности
        """
        # нужные id типов метрик
        id_metrics = [i for i in range(217,225)]
        name_metrics = [
            'segment_scores', 
            'general_infra', 
            'safety', 
            'flow', 
            'nights', 
            'climate', 
            'prices', 
            'distance'
            ]
        dp = MetricValueRepository()
        final =[]
        for i in id_metrics:
            give = dp.get_info_metricvalue(id_metric=i, 
                                           id_region=self.id_region,
                                           id_city = self.id_city)
            if give:
                final.append(float(give[0][0]))
            else:
                final.append(3)
        return dict(zip(name_metrics, final))
    
    def get_segment_scores(self)->dict:
        """
        Получение метрик по оценке сегментов туризма в Регионе
            Определение собираемых метрик:
            t_beach - Оценка состояния пляжного туризма в регионе
            t_health - Оценка состояния оздоровительного туризма в регионе
            t_business - Оценка состояния делового туризма в регионе
            t_pilgrimage - Оценка состояния паломнического туризма в регионе
            t_educational - Оценка состояния познавательного туризма в регионе
            t_family - Оценка состояния семейного туризма в регионе
            t_sports - Оценка состояния спортивного туризма в регионе
            t_eco_hiking - Оценка состояния экологического и походного туризма в регионе
        """
        # нужные id типов метрик
        id_metrics = [i for i in range(225,233)]
        name_metrics = [
            't_beach', 
            't_health', 
            't_business', 
            't_pilgrimage', 
            't_educational', 
            't_family', 
            't_sports', 
            't_eco_hiking'
            ]
        
        dp = MetricValueRepository()
        final =[]
        for i in id_metrics:
            give = dp.get_info_loc_cit_reg(id_metric=i, id_region=self.id_region)
            if give:
                final.append(float(give[0][0]))
            else:
                final.append(random.choice([2, 3, 4]))
        # df = {'name':name_metrics, 'value': final}
        return dict(zip(name_metrics, final))
        # return [name_metrics, final]

    def get_like_type_location(self, 
                               name:list, 
                              )-> dict:
        """
        Получение оценки типа локаций по конкретному региону/городу
            name - назваине типа локации, который нужен из БД
            region_id - id региона по которому нужно выдать оценку
            city_id - id города по которому нужно выдать оценку
        """
        if not (self.id_region or self.id_city):
            logger.error(f"Region_calc - get_like_type_location - не заданы id ни регоина ни города")
            return []
        metric_name = "Средняя оценка " + name
        M = MetricRepository() 
        id_metric = M.get_id_type_location(metric_name=metric_name)
        if id_metric:
            MV = MetricValueRepository()
            mass_value = MV.get_value_location(id_metric=id_metric,
                                  id_city=self.id_city,
                                  id_region=self.id_region)
            return mass_value
        else:
            logger.error(f"Region_calc - get_like_type_location - не нашлось id_metric по metric_name = {metric_name}")

    
    def get_reviews_top50(self, id_location) -> list[dict]:
        """
        Возвращает 50 самых длинных отзывов, отбирая по 10 из каждой даты 
        начиная с самой новой. Если отзывов в дате меньше 10 - берёт все.
        """
        r = ReviewRepository()
        query = r.get_reviews(id_location=id_location)
        
        # Конвертация в DataFrame
        result = [{"id_location": r.id_location, 
                    "text": r.text, 
                    "data": r.data} for r in query]
        
        if not result or len(result) <= 50:
            return result
        df = pd.DataFrame(result)
        
        # Предобработка данных
        df['data'] = pd.to_datetime(df['data'])
        df['text_length'] = df['text'].str.len()
        # df = df.dropna(subset=['data', 'text'])  # Фильтрация некорректных записей
        
        # Основная логика выборки
        final_selection = []
        
        # Шаг 1. Сортировка по дате (новые сначала) и длине текста
        df_sorted = df.sort_values(
            by=['data', 'text_length'], 
            ascending=[False, False]
        )
        
        # Шаг 2. Группировка по датам с сохранением порядка
        grouped = df_sorted.groupby(
            pd.Grouper(key='data', freq='D'), 
            sort=False  # сохраняем исходный порядок сортировки
        )
        
        # Шаг 3. Итерация по группам с накоплением результатов
        for _, group in grouped:
            if len(final_selection) >= 50:
                break
                
            # Берём топ-10 самых длинных отзывов группы
            needed = min(10, 50 - len(final_selection))
            final_selection.extend(
                group.nlargest(needed, 'text_length')
                .to_dict('records')
            )
            
        return final_selection[:50]  # Гарантируем не более 50 записей


    def get_segment_calc(self, segment):
        """
        Получает значения по сегменту для их рассчета и загрузки в БД
        """
        segment_like = self.get_like_locations(segment=segment)
        like_weather = self.get_weather_calc(segment=list(segment.keys())[0])
        return {list(segment.keys())[0]:segment_like, 'like_weather':like_weather}

    def get_weather_calc(self, segment=''):
        """
        Получает погоду в городе
        """
        try:
            if segment == 'sports' or segment == 'complex':
                return None
            if self.id_region:
                r = RegionRepository()
                region = r.find_region_by_id(id_region=self.id_region)
                self.id_city = region.capital
            if segment == 'beach':
                return self.get_weather_calc_beach()
            id_metric = 213
            m = MetricValueRepository()
            weathers = m.get_info_metricvalue(
                                id_city=self.id_city,
                                id_metric = id_metric
                                )
            if not weathers:
                logger.warning(f'Данных о погоне нет у города {self.id_city} ')
                return 2
            mass = [weather.__dict__ for weather in weathers]
            df = pd.DataFrame(mass)
            df_weather = df[['id_region', 'id_city', 'value', 'month']]
            count_month = 0
            like_month = [23, 32]
            for index, month in df_weather.iterrows():
                if month.value and re.match(r"\d+\.*\d*", month.value) and like_month[0] <= float(month.value) <= like_month[1]:
                        count_month += 1
            # Оценка количества теплых месяцев
            like = {0:2, 1:3, 2:4, 3:5}
            if count_month in like:
                return like[count_month]
            elif count_month > 3:
                return 5
            return 2
        except:
            logger.error(f"""Произошла ошибка в get_weather_calc, 
                         при обработке id_r - {self.id_region}, id_c - {self.id_city}
                        segment - {segment}""")
            return 2
    
    def get_weather_calc_beach(self):
        """
        Получение погоды для пляжного сегмента
        """
        try:
            id_metric = [216, 213]
            like_month = [[20, 40], [23, 35]]
            temperature = {}
            for i in range(len(id_metric)):
                m = MetricValueRepository()
                weathers = m.get_info_metricvalue(
                                    id_city=self.id_city,
                                    id_metric = id_metric[i]
                                    )
                mass = [weather.__dict__ for weather in weathers]
                temperature[i] = mass
            count_month = 0
            for index in range(len(temperature[0])):
                if temperature[0][index]['value'] and re.match(r"\d+\.*\d*", temperature[0][index]['value']):
                    if temperature[1][index]['value'] and re.match(r"\d+\.*\d*", temperature[1][index]['value']):
                        if like_month[0][0] <= float(temperature[0][index]['value']) <= like_month[0][1]:
                            if like_month[1][0] <= float(temperature[1][index]['value']) <= like_month[1][1]:
                                count_month += 1
            # Оценка количества теплых месяцев
            like = {0:2, 1:3, 2:4, 3:5}
            if count_month in like:
                return like[count_month]
            elif count_month > 3:
                return 5
            logger.warning(f"""В get_weather_calc_beach не выбран ни один из вариантов, 
                           количество месяцев = {count_month}""")
            return 2
        except:
            logger.error(f"""Произошла ошибка в get_weather_calc_beach, 
                         при обработке id_r - {self.id_region}, id_c - {self.id_city}
                        segment - beach""")
            return 2

        
    def get_like_locations(self, segment):
        """
        Получение оценок локаций lvl1 и lvl2 по месту и типу локации
        """
        logger.info('Инициализация get_like_locations - Получение оценок локаций по месту и типу локации')
        name_segment = list(segment.keys())[0]
        types_locations = list(segment[name_segment]['lvl1'].keys())
        # перебор уровней локаций у сегмента
        like_type_lvl1 = self.get_like_locations_lvl1(types_locations=types_locations)
        like_type_count_lvl1 = self.get_like_locations_lvl2(types_locations=types_locations)
        types_locations = segment[name_segment]['lvl2']
        like_type_count_lvl2 = self.get_like_locations_lvl2(types_locations=types_locations)
        segment_like = {'lvl1': like_type_lvl1, 
                        'count':{'lvl1':like_type_count_lvl1, 
                                'lvl2':like_type_count_lvl2
                                }
                        }
        return segment_like
            

    def get_like_locations_lvl1(self, types_locations):
        """
        Получение общей оценки lvl1 типа локации
        """
        result = {}
        l = LocationsRepository()
        m = MetricValueRepository()
        # перебор типов локаций
        for type_location in types_locations:
            mass = l.get_locations_by_type(type_location=type_location)
            if self.id_city:
                locations = [loc['id_location'] for loc in mass if loc['id_city'] == self.id_city]
            else:
                locations = [loc['id_location'] for loc in mass if loc['id_region'] == self.id_region]
            mass_value = []
            # перебор полученных локаций по месту
            for location in locations:
                # получение метрик по локациям
                loc = m.get_info_metricvalue(id_metric = 236, 
                                id_location=location
                                )
                if not loc:
                    continue
                value = loc[0].value
                if value:
                    mass_value.append(float(value))
                else:
                    continue
            value =  round(sum(mass_value)/len(mass_value), 2) if mass_value else 0
            result[type_location] = value
        return result
    
    def get_like_locations_lvl2(self, types_locations):
        """
        Получение оценки lvl2 количества типа локации
        """
        result = {}
        m = MetricValueRepository()
        # перебор типов локаций
        for type_location in types_locations:
            # получение метрик по локациям
            loc = m.get_info_metricvalue(id_metric = 239, 
                            type_location = type_location,
                            id_city = self.id_city,
                            id_region = self.id_region
                            )
            if not loc:
                continue
            value = round(float(loc[0].value), 2) if loc[0].value else 0
            result[type_location] = value
        return result
    
    def get_like_segment(self, segment_name):
        """
        Получение значений для оценки сегмента, в БД
        """
        try:
            m = MetricRepository()
            mv = MetricValueRepository()
            name_values = ['o', 'n', 'l', 'w']
            values = {}
            for name_value in name_values:
                # Определение id метрики
                id_metric = m.get_id_type_location(metric_name=f'{segment_name}_{name_value}')
                metric = mv.get_info_metricvalue(id_metric=id_metric,
                                        id_city=self.id_city,
                                        id_region=self.id_region)
                if metric:
                    metric = metric[0]
                    if metric.value and metric.value != 'None':
                        metric_value = metric.value
                        metric_value = float(metric_value) if float(metric_value) >= 2 else 2
                        values[name_value] = metric_value
                    else:
                        metric_value == 2
                else:
                    values[name_value] = 2
            return values
        except Exception as e:
            logger.error(f'Ошибка в get_like_segment: {e}')

    def get_tur_night(self):
        """
        Получение сумарного турпотока и количества ночевок в регионах, для их оценки
        """
        try:
            mv = MetricValueRepository()
            metrics = {'tur': 2, 'night': 3}
            result = {}
            for metric, id in metrics.items():
                mass = mv.get_info_metricvalue(id_metric=id)
                mass = [i.__dict__ for i in  mass]
                df = pd.DataFrame(mass)
                df = df[['id_region', 'value']]
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                result[metric] = df.groupby('id_region', as_index=False).agg({'value': 'sum'})
            return result
        except Exception as e:
            logger.error(f'Ошибка в методе get_like_segments: {e}')

    def get_distance_cities(self):
        """
        Получение списка городов из региона, для дальнейшего рассчета расстояния
        """
        try:
            r = RegionRepository()
            c = CitiesRepository()
            capital = c.get_cities_full(id_city=5178)
            cities = c.get_cities_full()
            return{'cities': cities, 'capital': capital}
        except Exception as e:
            logger.error(f'Ошибка в методе get_distance_cities: {e}')

    def get_like_segments(self):
        """
        Получение оценки сегмента для региона
        """
        try:
            metrics = {
                'beach':274,
                'health':275,
                'business':276,
                'pilgrimage':277,
                'educational':278,
                'family':279,
                'sports':280,
                'eco_hiking':281,
            }
            mv = MetricValueRepository()
            segments = {}
            for metric, id_metric in metrics.items():
                value = mv.get_info_metricvalue(
                    id_metric = id_metric,
                    id_city = self.id_city,
                    id_region = self.id_region
                )
                segments[metric] = float(value[0].value) if value else 0
            return segments
        except Exception as e:
            logger.error(f'Ошибка в методе get_like_segments: {e}')

    def get_like_parts_complex(self):
        """
        Получение оценок составных частей комплексной оценки
        """
        try:
            metrics = {
                'complex_t':217,
                'complex_o':218,
                'complex_n':240,
                'complex_l':241,
                'complex_tru':283,
                'complex_night':284,
                'complex_distance':285,
                'complex_price':286,
            }
            mv = MetricValueRepository()
            metric_value = {}
            for metric, id_metric in metrics.items():
                value = mv.get_info_metricvalue(
                    id_metric = id_metric,
                    id_city = self.id_city,
                    id_region = self.id_region
                )
                metric_value[metric] = float(value[0].value) if value else 2
            return metric_value
        except Exception as e:
            logger.error(f'Ошибка в методе get_like_segments: {e}')

    def get_housing(self):
        """
        Получение жилья для дальнейшего подсчета средних цен проживания и оценки
        """
        housing = {'hotel':[],'flat':[]}
        l = LocationsRepository()
        locations = l.get_by_type(type_location='calc')
        for location in locations:
            if 'flat' in location['characters']['type']:
                housing['flat'].append(location)
            else:
                housing['hotel'].append(location)
        return housing

