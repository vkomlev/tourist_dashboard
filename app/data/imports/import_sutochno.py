import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Tuple
from lxml import etree
import re
import tempfile
import os

from app.logging_config import logger

class ExtractSutochno:
    """
    Класс для загрузки и обработки данных с Sutochno.
    Поддерживает извлечение данных по отелям и квартирам.
    """

    HOTEL_FEED_URL = 'https://static.sutochno.ru/doc/files/xml/hotels.xml'
    APARTMENT_FEED_URL = 'https://static.sutochno.ru/doc/files/xml/yrl_searchapp.xml'

    def __init__(self) -> None:
        """
        Инициализирует экземпляр класса с пустыми DataFrame.
        """
        self.logger = logger
        self.hotel_df = pd.DataFrame()
        self.apartment_df = pd.DataFrame()

    def fetch_feed(self, url: str, timeout: int = 60) -> ET.Element:
        """
        Загружает XML-фид с удаленного сервера.

        :param url: URL фида для загрузки.
        :param timeout: Время ожидания ответа в секундах.
        :return: Корневой элемент XML-документа.
        """
        self.logger.debug(f'Загрузка данных с {url}...')
        response = requests.get(url, timeout=timeout)
        response.encoding = 'utf-8'
        self.logger.debug(f'Данные успешно загружены с {url}')
        return ET.fromstring(response.text)

    def parse_location(self, hotel: ET.Element) -> Tuple[str, str, str]:
        """
        Извлекает данные о местоположении отеля.

        :param hotel: XML-элемент отеля.
        :return: Кортеж с городом, адресом и координатами.
        """
        location = hotel.find('.//location')
        if location is not None:
            lat = location.find('latitude').text if location.find('latitude') is not None else 'N/A'
            lon = location.find('longitude').text if location.find('longitude') is not None else 'N/A'
            city = location.find('city').text if location.find('city') is not None else 'N/A'
            address = location.find('address').text if location.find('address') is not None else 'N/A'
            coord = f"{lat}, {lon}"
            return city, address, coord
        return 'N/A', 'N/A', 'N/A'

    def parse_amenities(self, hotel: ET.Element) -> dict:
        """
        Извлекает данные о удобствах отеля.
        :param hotel: XML-элемент отеля.
        :return: Словарь с удобствами отеля.
        """

        amenities = {}
        for amenity in hotel.findall('.//amenities/amenity'):
            group = amenity.attrib.get('group', 'Прочее')
            title = amenity.attrib.get('title', amenity.text)
            value = amenity.text or True
            if group not in amenities:
                amenities[group] = {}
            amenities[group][title] = value
        return amenities

    def extract_hotels(self) -> None:
        """
        Извлекает данные об отелях из XML-фида.
        """
        self.logger.debug('Извлечение данных об отелях...')
        root = self.fetch_feed(self.HOTEL_FEED_URL)
        data = []

        for hotel in root.findall('.//hotel'):
            hotel_id = hotel.attrib.get('id', 'N/A')
            stars = hotel.find('stars').text if hotel.find('stars') is not None else 'N/A'
            type_ = hotel.find('type').text if hotel.find('type') is not None else 'N/A'
            name = hotel.find('name').text if hotel.find('name') is not None else 'N/A'
            url = hotel.find('url').text if hotel.find('url') is not None else 'N/A'
            description = hotel.find('description').text if hotel.find('description') is not None else 'N/A'

            # Извлекаем фотографии
            photos = hotel.findall('.//photos/photo')
            photo_urls = [photo.text for photo in photos]
            photo_list = ', '.join(photo_urls)

            # Извлекаем расположение
            location = hotel.find('location')
            latitude = location.find('latitude').text if location.find('latitude') is not None else 'N/A'
            longitude = location.find('longitude').text if location.find('longitude') is not None else 'N/A'
            city = location.find('city').text if location.find('city') is not None else 'N/A'
            address = location.find('address').text if location.find('address') is not None else 'N/A'

            # Год открытия
            year_open = hotel.find('year_open').text if hotel.find('year_open') is not None else 'N/A'

            # Удобства
            amenities = self.parse_amenities(hotel)

            # Количество комнат, время заезда и выезда
            rooms_total = hotel.find('rooms_total').text if hotel.find('rooms_total') is not None else 'N/A'
            check_in = hotel.find('check_in').text if hotel.find('check_in') is not None else 'N/A'
            check_out = hotel.find('check_out').text if hotel.find('check_out') is not None else 'N/A'

            data.append([
                hotel_id, stars, type_, name, url, description, photo_list, latitude, longitude,
                city, address, year_open, amenities, rooms_total, check_in, check_out
            ])

        self.hotel_df = pd.DataFrame(data, columns=[
            'ID', 'Звезды', 'Тип', 'Название', 'Ссылка', 'Описание', 'Фотографии',
            'Широта', 'Долгота', 'Город', 'Адрес', 'Год открытия', 'Удобства',
            'Количество комнат', 'Время заезда', 'Время выезда'
        ])
        self.logger.debug('Данные об отелях успешно извлечены.')

    def recover_xml(self, input_file: str, output_file: str) -> None:
        """
        Восстанавливает некорректный XML-файл с использованием lxml в режиме восстановления.
        """
        self.logger.debug('Восстановление XML-файла с использованием lxml в режиме recover...')
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            tree = etree.parse(input_file, parser)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            self.logger.debug(f'Восстановленный XML-файл сохранен в {output_file}')
        except Exception as e:
            self.logger.error(f'Ошибка восстановления XML: {e}')
            raise

    def extract_apartments(self) -> None:
        """
        Извлекает все данные о квартирах из XML-фида.
        """
        self.logger.debug('Извлечение данных о квартирах...')
        ns = {'y': 'http://webmaster.yandex.ru/schemas/feed/realty/2010-06'}
        data = []
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                temp_input = os.path.join(temp_dir, 'raw_apartments.xml')
                temp_output = os.path.join(temp_dir, 'cleaned_apartments.xml')

                # Скачиваем и сохраняем исходный файл для потоковой очистки
                with requests.get(self.APARTMENT_FEED_URL, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    with open(temp_input, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1 MB
                            file.write(chunk)

                # Очистка XML-файла
                self.recover_xml(temp_input, temp_output)

                # Потоковая обработка XML с lxml
                context = etree.iterparse(temp_output, events=('start', 'end'))
                for event, elem in context:
                    if event == "end" and elem.tag.endswith('offer'):
                        # ID объекта
                        offer_id = elem.attrib.get('internal-id', 'N/A')

                        # Основные данные
                        type_ = elem.find('y:type', ns).text if elem.find('y:type', ns) is not None else 'N/A'
                        property_type = elem.find('y:property-type', ns).text if elem.find('y:property-type', ns) is not None else 'N/A'
                        category = elem.find('y:category', ns).text if elem.find('y:category', ns) is not None else 'N/A'
                        url = elem.find('y:url', ns).text if elem.find('y:url', ns) is not None else 'N/A'
                        creation_date = elem.find('y:creation-date', ns).text if elem.find('y:creation-date', ns) is not None else 'N/A'
                        last_update = elem.find('y:last-update-date', ns).text if elem.find('y:last-update-date', ns) is not None else 'N/A'

                        # Локация
                        location = elem.find('y:location', ns)
                        if location is not None:
                            country = location.find('y:country', ns).text if location.find('y:country', ns) is not None else 'N/A'
                            region = location.find('y:region', ns).text if location.find('y:region', ns) is not None else 'N/A'
                            locality = location.find('y:locality-name', ns).text if location.find('y:locality-name', ns) is not None else 'N/A'
                            address = location.find('y:address', ns).text if location.find('y:address', ns) is not None else 'N/A'
                            latitude = location.find('y:latitude', ns).text if location.find('y:latitude', ns) is not None else 'N/A'
                            longitude = location.find('y:longitude', ns).text if location.find('y:longitude', ns) is not None else 'N/A'
                        else:
                            country, region, locality, address, latitude, longitude = 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'

                        # Агент
                        sales_agent = elem.find('y:sales-agent', ns)
                        agent_name = sales_agent.find('y:name', ns).text if sales_agent is not None and sales_agent.find('y:name', ns) is not None else 'N/A'
                        agency_id = sales_agent.find('y:agency-id', ns).text if sales_agent is not None and sales_agent.find('y:agency-id', ns) is not None else 'N/A'

                        # Цена
                        price = elem.find('y:price', ns)
                        price_value = price.find('y:value', ns).text if price is not None and price.find('y:value', ns) is not None else 'N/A'
                        currency = price.find('y:currency', ns).text if price is not None and price.find('y:currency', ns) is not None else 'N/A'
                        period = price.find('y:period', ns).text if price is not None and price.find('y:period', ns) is not None else 'N/A'

                        # Извлечение описания
                        description = elem.find('y:description', ns).text if elem.find('y:description', ns) is not None else 'N/A'

                        # Площадь
                        area_element = elem.find('y:area', ns)
                        area = area_element.find('y:value', ns).text if area_element is not None and area_element.find('y:value', ns) is not None else 'N/A'
                        area_unit = area_element.find('y:unit', ns).text if area_element is not None and area_element.find('y:unit', ns) is not None else 'N/A'

                        # Комнаты и удобства
                        rooms = elem.find('y:rooms', ns).text if elem.find('y:rooms', ns) is not None else 'N/A'
                        renovation = elem.find('y:renovation', ns).text if elem.find('y:renovation', ns) is not None else 'N/A'
                        internet = elem.find('y:internet', ns).text if elem.find('y:internet', ns) is not None else 'N/A'
                        television = elem.find('y:television', ns).text if elem.find('y:television', ns) is not None else 'N/A'
                        parking = elem.find('y:parking', ns).text if elem.find('y:parking', ns) is not None else 'N/A'
                        rooms_offered = elem.find('y:rooms-offered', ns).text if elem.find('y:rooms-offered', ns) is not None else 'N/A'
                        floor = elem.find('y:floor', ns).text if elem.find('y:floor', ns) is not None else 'N/A'
                        floors_total = elem.find('y:floors-total', ns).text if elem.find('y:floors-total', ns) is not None else 'N/A'
                        rent_pledge = elem.find('y:rent-pledge', ns).text if elem.find('y:rent-pledge', ns) is not None else 'N/A'

                        # Извлечение параметров <param>
                        params_elements = elem.findall('y:param', ns)
                        param_values = [f"{param.attrib.get('name', 'N/A')}: {param.text}" for param in params_elements]
                        params_str = '; '.join(param_values) if param_values else 'N/A'

                        # Фотографии
                        images = elem.findall('y:image', ns)
                        photo_list = ', '.join([image.text for image in images if image.text]) if images else 'N/A'

                        # Добавляем данные в список
                        data.append([
                            offer_id, type_, property_type, category, url, creation_date, last_update,
                            country, region, locality, address, latitude, longitude,
                            agent_name, agency_id, price_value, currency, period, description,
                            area, area_unit, rooms, renovation, internet, television, parking, 
                            rooms_offered, floor, floors_total, rent_pledge, params_str, photo_list
                        ])

                        # Очистка обработанных данных
                        elem.clear()

                # Создание DataFrame
                self.apartment_df = pd.DataFrame(data, columns=[
                    'ID', 'Тип', 'Тип собственности', 'Категория', 'Ссылка', 'Дата создания', 'Дата обновления',
                    'Страна', 'Регион', 'Населенный пункт', 'Адрес', 'Широта', 'Долгота',
                    'Имя агента', 'ID агента', 'Цена', 'Валюта', 'Период', 'Описание',
                    'Площадь', 'Ед. измерения', 'Комнаты', 'Ремонт', 'Интернет', 'Телевидение', 'Парковка', 
                    'Количество комнат', 'Этаж', 'Количество этажей', 'Сумма оплаты', 'Параметры', 'Фотографии'
                ])
                self.logger.debug('Данные о квартирах успешно извлечены.')

            except etree.XMLSyntaxError as e:
                # Извлекаем номер строки с помощью новой функции
                error_line_number = self.extract_line_number_from_error(str(e))
                self.log_problematic_line(temp_output, error_line_number)
                self.logger.error(f'Ошибка разбора XML: {e}')
                raise ValueError(f'Ошибка разбора XML: {e}')

            except Exception as e:
                self.logger.error(f'Произошла ошибка: {e}')
                raise ValueError(f'Произошла ошибка: {e}')




    def log_problematic_line(self, file_path: str, error_line_number: int, context: int = 5) -> None:
        """
        Логирует проблемную строку и её окружение из XML-файла для диагностики.

        :param file_path: Путь к файлу XML.
        :param error_line_number: Номер строки с ошибкой.
        :param context: Количество строк до и после ошибки для вывода.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            start = max(0, error_line_number - context - 1)
            end = min(len(lines), error_line_number + context)

            self.logger.error(f'Проблемная строка и её окружение (строка {error_line_number}):')
            for i in range(start, end):
                prefix = '>> ' if i + 1 == error_line_number else '   '
                self.logger.error(f'{prefix}{i + 1}: {lines[i].strip()}')

        except Exception as e:
            self.logger.error(f'Ошибка чтения проблемной строки: {e}')
    
    def extract_line_number_from_error(self, error_message: str) -> int:
        """
        Извлекает номер строки из сообщения об ошибке XMLSyntaxError.

        :param error_message: Сообщение об ошибке XML.
        :return: Номер строки.
        """
        match = re.search(r'line (\d+)', error_message)
        if match:
            return int(match.group(1))
        raise ValueError(f'Не удалось извлечь номер строки из сообщения об ошибке: {error_message}')



    def save_to_excel(self, hotels_file: str = 'hotels_info.xlsx', apartments_file: str = 'apartments_info.xlsx') -> None:
        """
        Сохраняет данные в Excel-файлы.

        :param hotels_file: Имя файла для сохранения данных об отелях.
        :param apartments_file: Имя файла для сохранения данных о квартирах.
        """
        if not self.hotel_df.empty:
            self.hotel_df.to_excel(hotels_file, index=False)
            self.logger.debug(f'Данные об отелях сохранены в {hotels_file}.')
        if not self.apartment_df.empty:
            self.apartment_df.to_excel(apartments_file, index=False)
            self.logger.debug(f'Данные о квартирах сохранены в {apartments_file}.')