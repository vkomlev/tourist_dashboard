import csv
import os
from app.data.database import Database
from app.models import Sync

def import_csv(file_path, delimiter=','):
    # Создание экземпляра Database
    db = Database()

    # Проверка существования файла
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return

    # Открытие CSV-файла и чтение данных
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        
        # Перебор строк в CSV и добавление их в список объектов Sync
        sync_records = []
        for row in reader:
            sync_record = Sync(
                id_to=row['id_to'],
                object_type=row['object_type'],
                input_value=row['input_value'],
                input_from=row['input_from']
            )
            sync_records.append(sync_record)
        
        # Добавление всех объектов в базу данных
        db.add_all(sync_records)
        
    print(f"Data from {file_path} has been successfully imported to the sync table.")

