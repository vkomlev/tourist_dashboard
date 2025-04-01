from app.logging_config import logger
from app.data.database.models_repository import MetricValueRepository,MetricRepository
import random

class Calc:
    pass

class Region_calc(Calc):
    def __init__(self, id_region):
        self.id_region = id_region

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
            give = dp.get_info_loc_cit_reg(id_metric=i, id_region=self.id_region)
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

    def get_like_type_location(self, name:list, id_region:str = '', id_city:str = '')-> dict:
        """
        Получение оценки типа локаций по конкретному региону/городу
            name - назваине типа локации, который нужен из БД
            region_id - id региона по которому нужно выдать оценку
            city_id - id города по которому нужно выдать оценку
        """
        if not (id_region or id_city):
            logger.error(f"Region_calc - get_like_type_location - не заданы id ни регоина ни города")
            return []
        metric_name = "Средняя оценка " + name
        M = MetricRepository() 
        id_metric = M.get_id_type_location(metric_name=metric_name)
        if id_metric:
            MV = MetricValueRepository()
            mass_value = MV.get_value_location(id_metric=id_metric,
                                  id_city=id_city,
                                  id_region=id_region)
            return mass_value
        else:
            logger.error(f"Region_calc - get_like_type_location - не нашлось id_metric по metric_name = {metric_name}")

    

    

