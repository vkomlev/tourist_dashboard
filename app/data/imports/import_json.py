import json

def import_json_file(file_path: str) -> None:
    """Выводит первые ключи верхнего уровня из JSON-файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
                
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
    except json.JSONDecodeError:
        print(f"Ошибка парсинга JSON в файле {file_path}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")