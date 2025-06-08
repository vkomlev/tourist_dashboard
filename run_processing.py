from app.data.processing import DataProcessor,WeatherProcessor
# from app.data.parsing.base_parsing import Parse
# from app.data.database import LocationsRepository
# from app.data.database.models_repository import LocationsRepository, MetricValueRepository
# from app.reports.plot import City_page_plot, Region_page_plot
# from app.data.transform.prepare_data import Region_page_dashboard
# from app.data.calc.base_calc import Region_calc
# from app.data.score.base_assessment import WellnessTourismEvaluation, OverallTourismEvaluation
# import pandas as pd


dp = DataProcessor()
dp.process_yandex_locations(specific_region=('Карачаево-Черкесская Республика',), level_loc_type = 1, restart=False)

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