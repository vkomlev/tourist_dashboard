from app.data.processing import DataProcessor
# from app.data.parsing.base_parsing import Parse

dp = DataProcessor()
dp.process_yandex_locations(specific_region=('Свердловская область', 'Новоуральск'), level_loc_type = 1, restart=True)
