import numpy as np
import pandas as pd
from app.logging_config import logger
from app.data.database.models_repository import (LocationsRepository, 
                                                 MetricValueRepository, 
                                                 MetricRepository,
                                                 RegionRepository
                                                 )
from app.data.parsing.perplexity_parsing import ParsePerplexity
from app.data.imports.import_json import import_json_file
from app.data.calc.base_calc import Region_calc
from datetime import datetime
from dateutil.relativedelta import relativedelta
from shapely import wkb
from geoalchemy2.shape import to_shape


class OverallTourismEvaluation:
    def __init__(self, segment_scores=3, general_infra=3, safety=3, flow=3, nights=3, climate=3, prices=3, distance=3):
        """
        Комплексная оценка развития туризма.

        :param segment_scores: Средняя оценка сегментов туризма.
        :param general_infra: Оценка общей инфраструктуры (1–5).
        :param safety: Уровень безопасности (1–5).
        :param flow: Турпоток (1–5).
        :param nights: Среднее количество ночевок (1–5).
        :param climate: Климат (1–5).
        :param prices: Цены (обратный показатель, 1–5).
        :param distance: Удаленность (обратный показатель, 1–5).
        """
        self.segment_scores = segment_scores
        self.general_infra = general_infra
        self.safety = safety
        self.flow = flow
        self.nights = nights
        self.climate = climate
        self.prices = prices
        self.distance = distance

    def calculate_overall_score(self):
        """Рассчитывает комплексную оценку региона."""
        weights = {
            'segments': 0.4,
            'infra': 0.2,
            'safety': 0.1,
            'flow': 0.1,
            'nights': 0.05,
            'climate': 0.05,
            'prices': 0.05,
            'distance': 0.05
        }

        total_score = (
            weights['segments'] * self.segment_scores +
            weights['infra'] * self.general_infra +
            weights['safety'] * self.safety +
            weights['flow'] * self.flow +
            weights['nights'] * self.nights +
            weights['climate'] * self.climate +
            weights['prices'] * self.prices +
            weights['distance'] * self.distance
        )
        return round(total_score, 2)


class TourismEvaluation:
    def __init__(self):
        """
        Базовый класс для оценки туризма.
        """
        pass



    def get_like_locations_full(self, name_segment):
        """
        Оценка типов локаций lvl1 и lvl2 у сегмента
        """
        logger.info('Инициализация get_like_locations - оценка локаций и количеств локаций')
        segments = import_json_file(file_path=r'app\files\segments.json')
        lvl1 = segments[name_segment]['lvl1']
        self.calculate_like_locations_lvl1(lvl1)
        lvl2 = segments[name_segment]['lvl2']
        lvl2 = lvl2 + [i for i in lvl1.keys()]
        self.calculate_like_locations_lvl2(lvl2)
        logger.info("Оценка окончена")


    def calculate_like_locations_lvl1(self, types_locations):
        """
        Оценка важных локаций из списка types_locations
        """
        for type_location in types_locations:
            logger.info(f'Обработка важного типа локации {type_location}')
            l = LocationsRepository()
            # получении списка локаций одного типа
            df = l.get_locations_by_type(type_location=type_location)
            # преобразование столбца и получение перцентилей
            df = pd.DataFrame(df)
            df['count_reviews'] = pd.to_numeric(df['count_reviews'])
            percentiles = df['count_reviews'].quantile([i*0.01 for i in range(1,101)])
            percentiles = [percentiles[i*0.01] for i in range(1,101)]
            # обработка каждой локации
            for index, row in df.iterrows():
                # Проверка на существование оценки локации и её давность
                m = MetricValueRepository()
                info_loc = m.get_info_metricvalue(id_metric=236, 
                                        id_location=row.id_location,
                                        id_city=int(row.id_city) if 'id_city' in row and (not pd.isna(row.id_city)) else '',
                                        id_region=int(row.id_region) if 'id_region' in row and (not pd.isna(row.id_region)) else '',
                                       )
                if info_loc:
                    if self.check_limit_month(date=info_loc[0].modify_time):
                        logger.info(f"Посчитано для id_loc - {row.id_location} и = {info_loc[0].value}, пропускаем")
                        continue
                logger.info(f'Обработка локации {row.id_location} с оценкой яндекс {row.like} и кол. отзывов {row.count_reviews}')
                p = ParsePerplexity()
                r = Region_calc('')
                # получение оценки яндекс
                like_yandex = row.like.replace(',', '.') if row.like else 0
                # получение оценки количества отзывов
                like_count_reviews = self.get_tour_flow_rating(x=row.count_reviews, pcts=percentiles)
                # получение отзывов для их оценки
                reviews = r.get_reviews_top50(id_location=row.id_location)
                if reviews:
                    reviews = ';'.join([review["text"] for review in reviews])
                    text = types_locations[type_location]
                    text = f'{text} {reviews}'.replace('\n', ' ').replace('  ', ' ')
                    # отправка отзывов в бота
                    like_reviews = p.analyze_text_with_perplexity(request_bot=text)
                    if not like_reviews:
                        like_reviews = 0
                else:
                   like_reviews = 0 
                # подсчет итоговой оценки
                logger.info(f'0.35 * {float(like_yandex)} + 0.35 * {float(like_reviews)} + 0.3 * {float(like_count_reviews)}')
                like = 0.35 * float(like_yandex) + 0.35 * float(like_reviews) + 0.3 * float(like_count_reviews)
                like = str(round(like,2))
                logger.info(f'Для локации {row.id_location} типа {type_location} итоговая оценка {like}')
                m.loading_info(id_mv=info_loc[0].id_mv if info_loc else '',
                                id_metric=236, 
                                id_location=row.id_location,
                                id_city=int(row.id_city) if 'id_city' in row and (not pd.isna(row.id_city)) else '',
                                id_region=int(row.id_region) if 'id_region' in row and (not pd.isna(row.id_region)) else '',
                                value=like
                            )

    def calculate_like_locations_lvl2(self, types_locations):
        """
        Оценка не важных локаций из списка types_locations, по их количеству при помощи перцентиля
        """
        l = LocationsRepository()
        m = MetricValueRepository()
        for type_location in types_locations:
            logger.info(f'Обработка не важного типа локации {type_location}')
            # получении списка локаций одного типа
            df = l.get_locations_by_type(type_location=type_location)
            # преобразование столбца и получение перцентилей
            df = pd.DataFrame(df)
            # Группировка по городам
            df_cities = df.groupby('id_city').size().reset_index(name='count_locations')
            # Определение перцентиля
            percentiles_cities = df_cities['count_locations'].quantile([i*0.01 for i in range(1,101)])
            percentiles_cities = [percentiles_cities[i*0.01] for i in range(1,101)]

            # Группировка по регионам 
            df_regions = df.groupby('id_region').size().reset_index(name='count_locations')
            # Определение перцентиля
            percentiles_regions = df_regions['count_locations'].quantile([i*0.01 for i in range(1,101)])
            percentiles_regions = [percentiles_regions[i*0.01] for i in range(1,101)]
            # цикл для очередной оценки, сначала города, потом регионы
            for id in ['city', 'region']:
                logger.info(f"Обработка для {id}")
                place = df_cities if id =='city' else df_regions
                for index, row in place.iterrows():
                    info_locations = m.get_info_metricvalue(
                                            id_metric=239,
                                            id_city=int(row.id_city) if 'id_city' in row and (not pd.isna(row.id_city)) else '',
                                            id_region=int(row.id_region) if 'id_region' in row and (not pd.isna(row.id_region)) else '',
                                            type_location=type_location
                                            )
                    # if info_locations:
                    #     # проверка на давность рассчитанной метрики
                    #     if self.check_limit_month(date=info_locations[0].modify_time):
                    #         logger(f"Посчитано для {id}-{row.id_city if id == "city" else row.id_region} пропускаем")
                    #         continue
                    # Оценка и загрузка/обноление полученного значения
                    like_count_locations = self.get_tour_flow_rating(x=row.count_locations, 
                                                                    pcts=percentiles_cities 
                                                                    if id =='city' else percentiles_regions)
                    like_count_locations = like_count_locations if like_count_locations > 2 else 2.0
                    like_count_locations = str(like_count_locations)
                    logger.info(f'Оценка для {id}-{row.id_city if id == "city" else row.id_region} = {like_count_locations}')
                    m.loading_info( id_mv=info_locations[0][-1] if info_locations else '',
                                    id_metric=239, 
                                    type_location=type_location,
                                    id_city=int(row.id_city) if 'id_city' in row and (not pd.isna(row.id_city)) else '',
                                    id_region=int(row.id_region) if 'id_region' in row and (not pd.isna(row.id_region)) else '',
                                    value=like_count_locations
                        )

                    
    def get_tour_flow_rating(self, x: float, pcts: list) -> float:
        """
        Возвращает рейтинг в диапазоне [1.0; 5.0] с одним знаком после запятой
        по расширенной перцентильной шкале.
        """
        # 1. Если x меньше первого перцентиля
        if x < pcts[0]:
            return 2.0
        
        # 2. Если x больше последнего перцентиля
        if x > pcts[-1]:
            return 5.0
        
        # 3. Иначе ищем, в какой промежуток попадает x
        for i in range(len(pcts) - 1):
            if pcts[i] <= x < pcts[i+1]:
                # 4. Доля внутри интервала
                alpha = (x - pcts[i]) / (pcts[i+1] - pcts[i])
                
                # 5. Индекс процентиля i + alpha
                # 6. Переводим в шкалу 1..5:
                rating = 1 + 4 * ((i + alpha) / 99.0)
                
                # 7. Округляем
                return round(rating, 2)
        
        # На всякий случай, если x == pcts[-1]
        return 5.0
    
    def check_limit_month(self, date):
        date = datetime(date.year, date.month, date.day)
        current_date = datetime.now().date()
        difference = relativedelta(current_date, date)
        if difference.months != 0:
            return False
        return True
    

    def calculate_segment_score(self, climate_score: float, num_objects: int):
        """Рассчитывает комплексную оценку сегмента.
        avg_object_score средняя оценка по объекту
        num_objects количество объектов
        climate_score климат региона
        """
        avg_object_score = self.data['score'].mean()
        total_score = (
            self.segment_weights['avg_score'] * avg_object_score +
            self.segment_weights['num_objects'] * num_objects +
            self.segment_weights['climate'] * climate_score
        )
        return round(total_score, 2)

    def calculation_segment_parts(self, id_city='', id_region=''):
        """
        Рассчет составных частей, оценки сегмента
        """
        try:
            if id_region and id_city:
                logger.error("Указаны сразу регион и город, должно быть что-то одно")
                return False
            logger.info(f"Запуск рассчета составных частей оценки сегмента для id_r - {id_region}, id_c - {id_city}")
            segments = import_json_file(file_path=r'app\files\segments.json')
            calc = Region_calc(id_city=id_city, id_region=id_region)
            for name_segment, loc in segments.items():
                dictionary = calc.get_segment_calc(segment={name_segment:loc})
                # Средняя оценка основных локаций
                o = np.mean([v for k, v in dictionary[name_segment]['lvl1'].items()])
                o = round(o, 2) if o > 2 else 2.0
                # Средняя оценка количества основных локаций
                n = np.mean([v for k, v in dictionary[name_segment]['count']['lvl1'].items()])
                n = round(n, 2) if n > 2 else 2.0
                # Средняя оценка количества дополнительных локаций
                l = np.mean([v for k, v in dictionary[name_segment]['count']['lvl2'].items()])
                l = round(l, 2) if l > 2 else 2.0
                # Оценка погоды
                w = dictionary['like_weather']
                m = MetricRepository()
                mv = MetricValueRepository()
                logger.info(f'Рассчитаны значения для оценки сегмента {name_segment}')
                calculated_values = {'o':o, 'n':n, 'l':l, 'w':w}
                for name_value in calculated_values:
                    # Определение id метрики
                    id_metric = m.get_id_type_location(metric_name=f'{name_segment}_{name_value}')
                    metric = mv.get_info_metricvalue(id_metric=id_metric,
                                                    id_city=id_city,
                                                    id_region=id_region)
                    id_mv = metric[0].id_mv if metric else ''
                    mv.loading_info(id_mv=id_mv,
                                    id_metric=id_metric,
                                    id_city=int(id_city) if id_city else '',
                                    id_region=int(id_region) if id_region else '',
                                    value=str(calculated_values[name_value]))
        except:
            logger.error(f'id_city={id_city}, id_region={id_region}, o={o}, n={n}, l={l}, w={w}')

    def calculating_segments_score(self, id_city='', id_region=''):
        """
        Рассчет оценки сегментов
        """
        try:
            logger.info(f'Рассчет оценки сегментов для id_city={id_city}, id_region={id_region}')
            segments = import_json_file(file_path=r'app\files\segments.json')
            calc = Region_calc(id_city=id_city, id_region=id_region)
            m = MetricRepository()
            mv = MetricValueRepository()
            for segment_name in segments:
                if segment_name == 'complex':
                    continue
                values = calc.get_like_segment(segment_name=segment_name)
                if segment_name == 'sports':
                    segment_like = 0.65 * values['o'] + 0.35 * (
                                    0.7 * values['n'] + 0.3 * values['l'])
                else:
                    segment_like = 0.5 * values['o'] + 0.3 * values['w'] + 0.2 * (
                        0.7 * values['n'] + 0.3 * values['l'])
                segment_like = round(segment_like, 2)       
                id_metric = m.get_id_type_location(metric_name=f'segment_{segment_name}')
                if id_metric:
                    metrics = mv.get_info_metricvalue(id_metric=id_metric,
                                                    id_city=id_city,
                                                    id_region=id_region)
                    if id_region and metrics:
                        metrics = [i for i in metrics if not i.id_city]
                    if len(metrics) >= 2:
                        logger.error(f'Найдено несколько значений для метрики {id_metric}, id_r={id_region}, id_c={id_city}')
                    id_mv = metrics[0].id_mv if metrics else ''
                    mv.loading_info(id_mv=id_mv,
                                    id_metric=id_metric,
                                    id_city=int(id_city) if id_city else '',
                                    id_region=int(id_region) if id_region else '',
                                    value=str(segment_like))
                else:
                    logger.error(f'Не найдено id_metric, проверить в БД таблице метрик')
        except:
            logger.error('Ошбика при оценке сегмента')
    
    def calculating_complex_parts(self, id_region, id_city=''):
        '''
        Рассчет и загрузка составных составных частей комплексной оценки
        '''
        try:
            logger.info(f"Рассчет составных частей комплексной оценки для id_r = {id_region}, id_c = {id_city}")
            self.calculating_complex_tur_nig(id_region=id_region,
                                            id_city=id_city)
            self.calculating_complex_distance(id_region=id_region,
                                            id_city=id_city)
            if id_city:
                self.calculating_complex_segments(id_city=id_city)
                self.calculating_complex_price(id_city=id_city)
            else:
                self.calculating_complex_segments(id_region=id_region)
                self.calculating_complex_price(id_region=id_region)
        except Exception as e:
            logger.error(f"Ошибка в calculating_complex_parts: {e}")

    def calculating_complex_tur_nig(self, id_region, id_city=''):
        """
        Рассчет оценки суммарного турпотока и количества ночевок для регоина
        """
        try:
            r = Region_calc(id_region = id_region)
            mv = MetricValueRepository()
            t_n= r.get_tur_night()
            metrics = {'tur':283, 'night':284}
            for key, df in t_n.items():
                percentiles = df['value'].quantile([i*0.01 for i in range(1,101)])
                percentiles = [percentiles[i*0.01] for i in range(1,101)]
                value = df[df['id_region'] == id_region].value
                value = float(value.iloc[0])
                like_count = self.get_tour_flow_rating(x=value, 
                                                        pcts=percentiles
                                                        )
                like_count = round(like_count, 2) if like_count >= 2 else 2
                metric = mv.get_info_metricvalue(id_metric=metrics[key],
                                                id_city=id_city,
                                                id_region=id_region
                                                )
                id_mv = metric[0].id_mv if metric else ''
                mv.loading_info(id_mv = id_mv,
                                id_metric=metrics[key],
                                id_city=id_city,
                                id_region=id_region,
                                value = str(like_count)
                                )
                # logger.info(f'Добавлена метрика {key} со значением {like_count}')
        except Exception as e:
            logger.error(f'Ошибка в методе calculating_complex_tur_nig: {e}')

    def calculating_complex_distance(self, id_region, id_city=''):
        """
        Рассчет оценки расстояния от столицы до региона
        """
        try:
            r = Region_calc(id_region = id_region)
            if not id_city:
                reg = RegionRepository()
                region = reg.find_region_by_id(id_region=id_region)
                id_city = region.capital

            distance = r.get_distance_cities()
            # получение координат столицы
            wkb_element = distance['capital'][0].coordinates
            point = to_shape(wkb_element)
            longitude_capital, latitude_capital = point.x, point.y
            mass = []
            for city in distance['cities']:
                point = to_shape(city.coordinates)
                longitude_city, latitude_city = point.x, point.y
                longitude = (longitude_city - longitude_capital)**2
                latitude = (latitude_city - latitude_capital)**2
                length = (longitude + latitude)**0.5
                mass.append(length)
            mass.sort()
            df =  pd.DataFrame({'length':mass})
            percentiles = df['length'].quantile([i*0.01 for i in range(1,101)])
            percentiles = [percentiles[i*0.01] for i in range(1,101)]
            city = [i for i in distance['cities'] if i.id_city == id_city][0]
            point = to_shape(city.coordinates)
            longitude_city, latitude_city = point.x, point.y
            longitude = (longitude_city - longitude_capital)**2
            latitude = (latitude_city - latitude_capital)**2
            length = (longitude + latitude)**0.5
            
            pcts = percentiles
            x = length
            # 1. Если x меньше первого перцентиля
            if x <= pcts[0]:
                like_distance = 5.0
            
            # 2. Если x больше последнего перцентиля
            elif x >= pcts[-1]:
                like_distance = 2.0
            
            # 3. Иначе ищем, в какой промежуток попадает x
            else:
                for i in range(len(pcts) - 1):
                    if pcts[i] <= x < pcts[i+1]:
                        # 4. Доля внутри интервала
                        alpha = (x - pcts[i]) / (pcts[i+1] - pcts[i])
                        
                        # 5. Индекс процентиля i + alpha
                        # 6. Переводим в шкалу 1..5:
                        rating = 1 + 4 * ((len(pcts) - 1 - i + alpha) / 99.0)
                        
                        # 7. Округляем
                        like_distance = round(rating, 2)

            like_distance = round(like_distance, 2) if like_distance >= 2 else 2
            mv = MetricValueRepository()
            metric = mv.get_info_metricvalue(id_metric = 285,
                                            id_region = id_region,
                                            id_city = id_city)
            id_mv = metric[0].id_mv if metric else ''
            mv.loading_info(id_mv = id_mv,
                            id_metric = 285,
                            id_region = id_region,
                            id_city = id_city,
                            value = str(like_distance))
        except Exception as e:
            logger.error(f'Ошибка в методе calculating_complex_distance: {e}')
    
    def calculating_complex_segments(self, id_region='', id_city=''):
        """
        Рассчет средней оценки сегментов для региона
        """
        r = Region_calc(id_city=id_city, id_region=id_region)
        mv = MetricValueRepository()
        segments = r.get_like_segments()
        like = np.mean([float(segments[i]) for i in segments]) if segments else 2 
        like = round(like, 2)
        metric = mv.get_info_metricvalue(id_metric = 217,
                                        id_region = id_region,
                                        id_city = id_city)
        id_mv = metric[0].id_mv if metric else ''
        mv.loading_info(id_mv = id_mv,
                        id_metric = 217,
                        id_region = id_region,
                        id_city = id_city,
                        value = str(like))
        
    def calculating_complex_price(self, id_city='', id_region=''):
        """
        Рассчитывает среднюю стоимость проживания, оценку проживания в регионах
        """
        r = Region_calc(id_region='150')
        mv = MetricValueRepository()
        h_f = r.get_housing()

        def prepare_df(data):
            """
            достает цены жилья и преобразует
            возвразает dataframe
            """
            df = pd.DataFrame(data)
            if df.empty:
                return pd.DataFrame(columns=['id_city', 'id_region', 'price'])
            df['price'] = df['characters'].apply(lambda c: c.get('Цена') if c and c.get('Цена') is not None else None)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df.dropna(subset=['price'])
            return df

        df_hotel = prepare_df(h_f.get('hotel', []))
        df_flat = prepare_df(h_f.get('flat', []))

        # Определяем по чему группируем
        group_key = None
        if id_city:
            group_key = 'id_city'
        elif id_region:
            group_key = 'id_region'
        else:
            raise ValueError("Необходимо указать id_city или id_region для группировки")

        # Группируем, считаем среднее и перцентиля
        df_hotel = df_hotel.loc[df_hotel['price'] <= 15000]
        mean_hotel = df_hotel.groupby(group_key)['price'].mean()
        percentiles_hotel = df_hotel['price'].quantile([i*0.01 for i in range(1,101)])
        percentiles_hotel = [percentiles_hotel[i*0.01] for i in range(1,101)]

        df_flat = df_flat.loc[df_flat['price'] <= 15000]
        mean_flat = df_flat.groupby(group_key)['price'].mean()
        percentiles_flat = df_flat['price'].quantile([i*0.01 for i in range(1,101)])
        percentiles_flat = [percentiles_flat[i*0.01] for i in range(1,101)]

        # Получаем средние цены по конкретному id_city или id_region
        mean_price_hotel = 0
        mean_price_flat = 0

        if id_city and id_city in mean_hotel.index:
            mean_price_hotel = mean_hotel.loc[id_city]
        elif id_region and id_region in mean_hotel.index:
            mean_price_hotel = mean_hotel.loc[id_region]

        if id_city and id_city in mean_flat.index:
            mean_price_flat = mean_flat.loc[id_city]
        elif id_region and id_region in mean_flat.index:
            mean_price_flat = mean_flat.loc[id_region]

        like_hotel = self.get_tour_flow_rating(x=mean_price_hotel, 
                                        pcts=percentiles_hotel) if mean_price_hotel else 0.0
        like_flat = self.get_tour_flow_rating(x=mean_price_flat, 
                                        pcts=percentiles_flat) if mean_price_flat else 0.0
        like = round((like_hotel+like_flat)/2, 2)
        like = like if like >=2 else 2.0
        calc = {
            '287': str(round(mean_price_hotel, 2)),
            '288': str(round(mean_price_flat, 2)),
            '286': str(like) if isinstance(like, float) and like >= 2 else '2.0'
        }
        for id_metric in calc:
            metric = mv.get_info_metricvalue(id_metric = id_metric,
                                            id_region = id_region,
                                            id_city = id_city)
            id_mv = metric[0].id_mv if metric else ''
            mv.loading_info(id_mv = id_mv,
                            id_metric = id_metric,
                            id_region = id_region,
                            id_city = id_city,
                            value = calc[id_metric])
            logger.info(f'Стоимости и оценка f {mean_price_flat}; h {mean_price_hotel}; like {like}')
        
    
    def calculating_complex_like(self, id_region, id_city = ''):
        """
        Рассчет комплексной оценки
        """
        try:
            logger.info(f"Рассчет комплексной оценки id_region = {id_region}, id_city = {id_city}")
            r = Region_calc(id_city=id_city, 
                            id_region=id_region)
            mv = MetricValueRepository()
            metrics_value = r.get_like_parts_complex()
            complex_like = (0.35 * metrics_value['complex_t']) + (
                            0.2 * metrics_value['complex_o']) + (
                            0.1 * (
                                (0.7 * metrics_value['complex_n']) + (
                                0.3 * metrics_value['complex_l']))
                            ) + (
                            0.1 * metrics_value['complex_tru']) + (
                            0.1 * metrics_value['complex_night']) + (
                            0.05 * metrics_value['complex_distance']) + (
                            0.1 * metrics_value['complex_price'])
            complex_like = round(complex_like, 2) if complex_like >= 2 else 2
            metric = mv.get_info_metricvalue(id_metric = 282,
                                            id_region = id_region,
                                            id_city = id_city)
            id_mv = metric[0].id_mv if metric else ''
            mv.loading_info(id_mv = id_mv,
                            id_metric = 282,
                            id_region = id_region,
                            id_city = id_city,
                            value = str(complex_like))
        except Exception as e:
            logger.error(f'Ошибка в методе calculating_complex_like: {e}')



        
        
            









            




class WellnessTourismEvaluation(TourismEvaluation):
    """Класс для оценки оздоровительного туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }
        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)


class BeachEvaluation(TourismEvaluation):
    """Класс для оценки пляжного туризма."""
    def __init__(self, data):
        weights = {
            'popularity': 0.25,
            'infrastructure': 0.20,
            'accessibility': 0.15,
            'safety': 0.15,
            'ecology': 0.15,
            'rating': 0.10
        }
        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)

class FamilyTourismEvaluation(TourismEvaluation):
    """Класс для оценки семейного и детского туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }
        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)

class KnowledgeTourismEvaluation(TourismEvaluation):
    """Класс для оценки позновательного туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }

        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)



class PilgrimageEvaluation(TourismEvaluation):
    """Класс для оценки паломнического туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }

        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)

class SportsExtremeEvaluation(TourismEvaluation):
    """Класс для оценки спортивного и экстремальног туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }

        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)

class BusinessScientificEvaluation(TourismEvaluation):
    """Класс для оценки делового и научного туризма."""
    def __init__(self, data):
        weights = {
            'accessibility': 0.3,
            'quality': 0.25,
            'safety': 0.15,
            'ecology': 0.1,
            'functionality': 0.1,
            'reputation': 0.1
        }

        segment_weights = {
            'avg_score': 0.5,
            'num_objects': 0.2,
            'climate': 0.3,
        }
        super().__init__(data, weights, segment_weights)