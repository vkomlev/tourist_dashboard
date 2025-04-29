from app.data.score.base_assessment import TourismEvaluation
from app.data.imports.import_json import import_json_file
from app.data.database.models_repository import RegionRepository, CitiesRepository
import time

# Оценка составных частей для оценки сегментов и сама оценка сегмента
start_time = time.time()
t = TourismEvaluation()
r = RegionRepository()
c = CitiesRepository()
regions = r.full_region_by_id()
regions = [150, 155, 151]
for id_region in regions:
    t.calculating_segments_score(id_region=id_region)
    cities = c.get_cities_in_region(id_region=id_region)
    # cities = [(7216,)]
    for id_city in cities:
        t.calculating_segments_score(id_city=id_city[0])
end_time = time.time()
execution_time = end_time - start_time
print(f"Время выполнения: {execution_time:.2f} секунд")

# t.calculation_segment_parts(id_city='7225')

# # Оценка важных и не важных локаций 
# start_time = time.time()
# segments = import_json_file(file_path=r'app\files\segments.json')
# for i in segments:
#     t = TourismEvaluation()
#     t.get_like_locations_full(i)
# end_time = time.time()
# execution_time = end_time - start_time
# print(f"Время выполнения: {execution_time:.2f} секунд")


