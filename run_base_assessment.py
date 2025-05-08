from app.data.score.base_assessment import TourismEvaluation
from app.data.imports.import_json import import_json_file
from app.data.database.models_repository import RegionRepository, CitiesRepository
import time

t = TourismEvaluation()
t.calculating_complex_distance(id_region=169)

# # Оценка сегмента
# start_time = time.time()
# t = TourismEvaluation()
# r = RegionRepository()
# c = CitiesRepository()
# # regions = r.full_region_by_id()
# regions = [150, 155, 151]
# for id_region in regions:
#     # Оценка составных частей сегментов
#     t.calculation_segment_parts(id_region=id_region)
#     # Оценка сегментов
#     t.calculating_segments_score(id_region=id_region)
#     # Оценка составных частей комплексной оценки
#     t.calculating_complex_parts(id_region=id_region, id_city=7215)
#     cities = c.get_cities_in_region(id_region=id_region)
#     # cities = [(7216,)]
#     for id_city in cities:
#         # Оценка составных частей сегментов
#         t.calculation_segment_parts(id_city=id_city[0])
#         # Оценка сегментов
#         t.calculating_segments_score(id_city=id_city[0])
#         # Оценка составных частей комплексной оценки
#         t.calculating_complex_parts(id_region=id_region, id_city=7216)
# end_time = time.time()
# execution_time = end_time - start_time
# print(f"Время выполнения: {execution_time:.2f} секунд")


# # Оценка важных и не важных локаций 
# start_time = time.time()
# segments = import_json_file(file_path=r'app\files\segments.json')
# for i in segments:
#     t = TourismEvaluation()
#     t.get_like_locations_full(i)
# end_time = time.time()
# execution_time = end_time - start_time
# print(f"Время выполнения: {execution_time:.2f} секунд")


