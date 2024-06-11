import seaborn as sns
import matplotlib.pyplot as plt
from app.reports.table_data import generate_heatmap_tourist_count_data, get_region_tourist_flow_data
import os

def plot_heatmap_tourist_count_data():
    df_pivot = generate_heatmap_tourist_count_data()
    
    # Преобразование значений в миллионы
    df_pivot = df_pivot / 1_000_000

    plt.figure(figsize=(12, 8))
    
    sns.heatmap(df_pivot, annot=False, cmap="YlGnBu", cbar_kws={'label': 'Турпоток (млн. чел.)'})
    plt.title('Турпоток по сезонам в популярных регионах')

    # Уменьшение шрифта для названий регионов
    plt.yticks(rotation=0, fontsize=8)
    plt.xticks(rotation=90, fontsize=8)

    # Сохранение графика
    output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'heatmap.png'))
    plt.close()

def plot_region_flow_histogram(region_id, region_name):
        df = get_region_tourist_flow_data(region_id)

        plt.figure(figsize=(12, 8))
        plt.bar(df['period'], df['value'], color='blue')
        plt.xlabel('Период (год-месяц)')
        plt.ylabel('Турпоток')
        plt.title(f'Турпоток по региону: {region_name}')
        plt.xticks(rotation=90)

        # Сохранение графика
        output_dir = os.path.join(os.getcwd(), 'app', 'static', 'images')
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f'histogram_flow_{region_id}.png'))
        plt.close()