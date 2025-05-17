from app.data.processing import DataProcessor,WeatherProcessor, Sutochno
from app.data.parsing.base_parsing import Parse
from app.data.parsing.sutochno_parsing import ParseSutochnoXML
from time import sleep
# from app.data.database import LocationsRepository
# from app.data.database.models_repository import LocationsRepository, MetricValueRepository
# from app.reports.plot import City_page_plot, Region_page_plot
# from app.data.transform.prepare_data import Region_page_dashboard
# from app.data.calc.base_calc import Region_calc
# from app.data.score.base_assessment import WellnessTourismEvaluation, OverallTourismEvaluation
# import pandas as pd


# files_path = [
#                 r'C:\Works\tourist_dashboard\app\files\hotels_info.xlsx', 
#                 r'C:\Works\tourist_dashboard\app\files\realty_info.xlsx'
#                 ]
# for file_path in files_path:
#     s = Sutochno()
#     s.loading_sutochno(file_path=file_path,
#                         sheet_name='Sheet1')

# Сбор локаций
dp = DataProcessor()
dp.process_yandex_locations(specific_region=('Свердловская область', "Черноисточинск"), level_loc_type = 1, restart=False)

# dp = Region_page_dashboard()
# dp.get_region_mean_night(id_region=150, year=2023)

# dp = City_page_plot()
# dp.create_layout(5848)

# dp = Region_page_plot()
# dp.plot_region_dynamics_tourist(id_region=150, year='2022')

# dp = MetricValueRepository()
# print(dp.get_info_loc_cit_reg(id_region=150, id_metric=2))

# dp = Region_calc(150)
# print(dp.get_segment_scores())