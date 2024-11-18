# app\data\parsing\sutochno_parsing.py

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import xml.etree.ElementTree as ET

from app.data.parsing import Parse, ParseError 

logger = logging.getLogger(__name__)

class ParseSutochno(Parse):
    def __init__(self, url: str) -> None:
        """
        Инициализирует класс ParseXMLFeed.

        Args:
            url (str): URL XML-фида.
        """
        super().__init__(url)
        logger.info(f"Инициализирован ParseSutochno с URL: {self.url}")
    
    def parse_hotels_data(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Парсит данные об отелях из корневого элемента XML.

        Args:
            root (ET.Element): Корневой элемент XML-документа.

        Returns:
            List[Dict[str, Any]]: Список словарей с информацией об отелях.
        """
        hotels_data = []
        logger.info("Начало парсинга данных об отелях.")

        for hotel in root.findall('.//hotel'):
            try:
                hotel_id = hotel.attrib.get('id', 'N/A')
                name = hotel.find('name').text.strip() if hotel.find('name') is not None else 'N/A'
                type_ = hotel.find('type').text.strip() if hotel.find('type') is not None else 'N/A'

                # Извлечение данных о местоположении
                location = hotel.find('.//location')
                if location is not None:
                    lat = location.find('latitude').text.strip() if location.find('latitude') is not None else 'N/A'
                    lon = location.find('longitude').text.strip() if location.find('longitude') is not None else 'N/A'
                    city = location.find('city').text.strip() if location.find('city') is not None else 'N/A'
                    address = location.find('address').text.strip() if location.find('address') is not None else 'N/A'
                    coord = f"{lat}, {lon}"
                else:
                    lat, lon, city, address, coord = 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'

                # Извлечение списка удобств
                amenities = [amenity.text.strip() for amenity in hotel.findall('.//amenities/amenity') if amenity.text]
                amenities_str = ', '.join(amenities) if amenities else 'N/A'

                # Извлечение данных о питании
                meals = hotel.findall('.//meal/*')
                meal_details = []
                for meal in meals:
                    meal_type = meal.attrib.get('type', 'N/A').strip()
                    meal_title = meal.attrib.get('title', '').strip()
                    meal_text = meal.text.strip() if meal.text else ''
                    meal_details.append(f"{meal.tag.capitalize()}: {meal_type} ({meal_title}) - {meal_text}")
                meal_str = '; '.join(meal_details) if meal_details else 'N/A'

                # Обработка типов номеров и цен
                rooms = hotel.findall('.//rooms/room')
                if rooms:
                    for room in rooms:
                        room_type = room.attrib.get('type', 'N/A').strip()
                        price = room.find('price').text.strip() if room.find('price') is not None else 'N/A'

                        hotel_info = {
                            'ID отеля': hotel_id,
                            'Название отеля': name,
                            'Тип отеля': type_,
                            'Город': city,
                            'Адрес': address,
                            'Координаты': coord,
                            'Тип номера': room_type,
                            'Цена': price,
                            'Удобства': amenities_str,
                            'Питание': meal_str
                        }
                        hotels_data.append(hotel_info)
                        logger.debug(f"Добавлена информация об отеле: {hotel_info}")
                else:
                    # Добавление данных для отеля без комнат
                    hotel_info = {
                        'ID отеля': hotel_id,
                        'Название отеля': name,
                        'Тип отеля': type_,
                        'Город': city,
                        'Адрес': address,
                        'Координаты': coord,
                        'Тип номера': 'N/A',
                        'Цена': 'N/A',
                        'Удобства': amenities_str,
                        'Питание': meal_str
                    }
                    hotels_data.append(hotel_info)
                    logger.debug(f"Добавлена информация об отеле без комнат: {hotel_info}")

            except Exception as e:
                logger.error(f"Ошибка при парсинге отеля с ID {hotel.attrib.get('id', 'N/A')}: {e}")
                continue

        logger.info(f"Парсинг завершен. Найдено отелей: {len(hotels_data)}")
        return hotels_data

    def get_hotels_dataframe(self, hotels_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Преобразует список словарей с данными об отелях в DataFrame.

        Args:
            hotels_data (List[Dict[str, Any]]): Список словарей с информацией об отелях.

        Returns:
            pd.DataFrame: DataFrame с данными об отелях.
        """
        try:
            logger.info("Преобразование данных в DataFrame.")
            df = pd.DataFrame(hotels_data)
            logger.info("Преобразование успешно выполнено.")
            return df
        except Exception as e:
            logger.error(f"Ошибка при создании DataFrame: {e}")
            raise ParseError(f"Ошибка создания DataFrame: {e}") from e

    def get_hotels_data(self) -> List[Dict[str, Any]]:
        """
        Получает и парсит данные об отелях из XML-фида.

        Returns:
            List[Dict[str, Any]]: Список словарей с информацией об отелях.
        """
        try:
            root = self.fetch_xml_data()
            hotels_data = self.parse_hotels_data(root)
            return hotels_data
        except ParseError as e:
            logger.error(f"Ошибка при получении данных об отелях: {e}")
            return []

    def get_hotels_dataframe_without_saving(self) -> Optional[pd.DataFrame]:
        """
        Получает данные об отелях и возвращает их в виде DataFrame без сохранения в файл.

        Returns:
            Optional[pd.DataFrame]: DataFrame с данными об отелях или None в случае ошибки.
        """
        try:
            hotels_data = self.get_hotels_data()
            if not hotels_data:
                logger.warning("Нет данных для создания DataFrame.")
                return None
            df = self.get_hotels_dataframe(hotels_data)
            return df
        except ParseError as e:
            logger.error(f"Ошибка при получении DataFrame: {e}")
            return None