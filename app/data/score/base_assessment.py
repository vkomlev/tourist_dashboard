import numpy as np
import pandas as pd

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
    def __init__(self, data, weights, segment_weights):
        """
        Базовый класс для оценки туризма.

        :param data: DataFrame с информацией об объектах инфраструктуры.
        :param weights: Веса для оценки объектов.
        :param segment_weights: Веса для расчета комплексной оценки сегмента.
        """
        self.data = data
        self.weights = weights
        self.segment_weights = segment_weights

    def evaluate_object(self, row):
        """Рассчитывает оценку для одного объекта."""
        if row.empty:
            score = 3
        else:
            score = sum(row[col] * self.weights[col] for col in self.weights)
        return round(score, 2)

    def evaluate_all_objects(self):
        """Добавляет оценку для всех объектов в DataFrame."""
        self.data['score'] = self.data.apply(self.evaluate_object, axis=1)
        return self.data

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