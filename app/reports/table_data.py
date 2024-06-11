import pandas as pd
from app.data.database import MV_repo
from app.models import Region

def process_tourist_count_data(n=10, top=True):
    '''Получение топ N регионов по турпотоку и формирование datafrrame Pandas'''
    db = MV_repo()
    data = db.get_tourist_count_data()

    # Преобразование данных в DataFrame
    df = pd.DataFrame(data, columns=['id_region', 'value','month','year'])
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
    if top:
        final_df = df_sum.head(n).reset_index(drop=True)
    else:
        final_df  = df_sum.tail(n).reset_index(drop=True)

    # Добавление места региона
    final_df['rank'] = final_df.index + 1

    return final_df[['rank', 'region_name', 'value', 'percentage']]

def generate_heatmap_tourist_count_data(n=10):
    '''Генерация сводной таблицы для хитмапа турпотока'''
    db = MV_repo()
    data = db.get_tourist_count_data()

    # Преобразование данных в DataFrame
    df = pd.DataFrame(data, columns=['id_region', 'value', 'month', 'year'])
    df['value'] = df['value'].astype(int)

    # Суммарный турпоток по регионам
    df_sum = df.groupby(['id_region', 'year', 'month']).sum().reset_index()

    # Получение названий регионов
    region_names = {region.id_region: region.region_name for region in db.query(Region)}
    df_sum['region_name'] = df_sum['id_region'].map(region_names)

    # Сортировка данных и выбор топ N регионов
    top_regions = df_sum.groupby('id_region')['value'].sum().sort_values(ascending=False).head(n).index
    df_top = df_sum[df_sum['id_region'].isin(top_regions)]

    # Создание столбца для год+месяц
    df_top['year_month'] = df_top.apply(lambda row: f"{row['year']}-{row['month']:02d}", axis=1)

    # Использование метода pivot с именованными аргументами
    return df_top.pivot(index='region_name', columns='year_month', values='value')

def get_region_tourist_flow_data(region_id):
    '''Получение данных о турпотоке в регионе'''
    db = MV_repo()
    data = db.get_tourist_count_data_by_region(region_id)

    df = pd.DataFrame(data, columns=['id_region', 'value', 'month', 'year'])
    df['value'] = df['value'].astype(int)
    df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)

    return df[['period', 'value']]
