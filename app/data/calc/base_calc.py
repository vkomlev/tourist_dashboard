from app.logging_config import logger
from app.data.database.models_repository import MetricValueRepository
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