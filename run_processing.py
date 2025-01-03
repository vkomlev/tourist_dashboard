from app.data.processing import DataProcessor,WeatherProcessor
# from app.data.parsing.base_parsing import Parse
# from app.data.database import LocationsRepository
# from app.data.database.models_repository import MetricValueRepository
from app.reports.plot import City_page_plot, Region_page_plot
# from app.reports.table_data import Region_page_dashboard
from app.data.score.base_assessment import WellnessTourismEvaluation, OverallTourismEvaluation
import pandas as pd

dp = DataProcessor()
dp.process_yandex_locations(specific_region=('Челябинская область',), level_loc_type = 1, restart=True)

# dp = City_page_plot()
# dp.create_layout(5848)

# dp = Region_page_plot()
# dp.plot_region_results_card(1)
# dp.plot_region_leisure_rating(1)

