from app.data.processing import DataProcessor,WeatherProcessor
# from app.data.parsing.base_parsing import Parse
# from app.data.database import LocationsRepository
# from app.data.database.models_repository import MetricValueRepository
# from app.reports.plot import City_page_plot
# from app.reports.table_data import Region_page_dashboard

dp = DataProcessor()
dp.process_yandex_locations(specific_region=('Свердловская область',), level_loc_type = 1, restart=False)

# dp = Region_page_dashboard()
# print(dp.get_city_weather_summary(5848))

# db = WeatherProcessor()
# print(db.process_weather_data())

