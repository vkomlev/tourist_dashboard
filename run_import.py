from app.data.import_csv import import_csv
import os

if __name__ == "__main__":
    # Указание пути к CSV-файлу
    csv_file_path = os.path.join(os.path.dirname(__file__),'app','data', 'sync.csv')
    import_csv(csv_file_path, delimiter=';')  # Пример использования с точкой с запятой в качестве разделителя
