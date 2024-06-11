import pandas as pd
from app.data.database import MV_repo
from app.models import Region

def process_tourism_data(n=10):
    db = MV_repo()
    data = db.get_tourism_data()

    # Преобразование данных в DataFrame
    df = pd.DataFrame(data, columns=['id_region', 'value'])
    df['value'] = df['value'].astype(int)

    # Суммарный турпоток по регионам
    df_sum = df.groupby('id_region').sum().reset_index()

    # Получение названий регионов
    region_names = {region.id_region: region.region_name for region in db.query(Region)}

    # Добавление названий регионов
    df_sum['region_name'] = df_sum['id_region'].map(region_names)

    # Суммарный турпоток по всем регионам
    total_tourism = df_sum['value'].sum()

    # Вычисление доли в процентах
    df_sum['percentage'] = (df_sum['value'] / total_tourism) * 100

    # Сортировка данных
    df_sum = df_sum.sort_values(by='value', ascending=False)

    # Формирование топ N регионов
    top_n = df_sum.head(n)
    bottom_n = df_sum.tail(n)

    # Итоговый DataFrame
    final_df = pd.concat([top_n, bottom_n])#.reset_index(drop=True)

    # Добавление места региона
    final_df['rank'] = final_df.index + 1

    return final_df[['rank', 'region_name', 'value', 'percentage']]