# app\data\parsing\weather_parsing.py

import logging
from typing import Dict, Optional


from bs4 import BeautifulSoup

from app.data.compare import CompareCities
from app.data.parsing import Parse, ParseError

logger = logging.getLogger(__name__)


class ParseWeather(Parse):
    """Класс для парсинга погодных данных."""

    def __init__(self) -> None:
        """Инициализирует класс ParseWeather."""
        super().__init__(url='http://russia.pogoda360.ru')
        logger.info("Инициализирован ParseWeather.")

    def get_region(self) -> BeautifulSoup:
        """
        Получает HTML-код блока с регионами.

        Returns:
            BeautifulSoup: Парсенный HTML блока регионов.
        """
        logger.debug("Получение региона из страницы.")
        return self.get_data(tag='div', id='statesPanel', url='/')

    def get_cities(self, url: str) -> BeautifulSoup:
        """
        Получает HTML-код блока с городами по заданному URL.

        Args:
            url (str): Относительный URL для получения городов.

        Returns:
            BeautifulSoup: Парсенный HTML блока городов.
        """
        logger.debug(f"Получение городов по URL: {url}")
        return self.get_data(url=url, tag='div', id='citiesPanel')

    def parse_data(self, result: BeautifulSoup, tag: str) -> Dict[str, str]:
        """
        Парсит данные из HTML-элементов.

        Args:
            result (BeautifulSoup): Парсенный HTML.
            tag (str): Тег для поиска элементов.

        Returns:
            Dict[str, str]: Словарь с названиями и URL.
        """
        elements = result.find_all(tag)
        data: Dict[str, str] = {}
        for item in elements:
            name = item.text.strip()
            href = item.get('href', '').strip()
            if '(' in name:
                name = name[:name.rfind('(')].strip()
            # data[name] = f'http://{self.url.split("//")[1]}{href}'
            data[name] = f'{href}'
            logger.debug(f"Парсинг элемента: {name} -> {data[name]}")
        return data

    def parse_regions(self) -> Dict[str, str]:
        """
        Парсит список регионов.

        Returns:
            Dict[str, str]: Словарь регионов и их URL.
        """
        logger.info("Парсинг регионов.")
        result = self.get_region()
        return self.parse_data(result, tag='a')

    def parse_cities(self, url: str) -> Dict[str, str]:
        """
        Парсит список городов по заданному региону.

        Args:
            url (str): URL региона для получения городов.

        Returns:
            Dict[str, str]: Словарь городов и их URL.
        """
        logger.info(f"Парсинг городов по URL: {url}")
        result = self.get_cities(url)
        return self.parse_data(result, tag='a')

    def get_city_from_region(self, region_name: str, data: Dict[str, str]) -> Dict[str, str]:
        """
        Получает список городов для конкретного региона.

        Args:
            region_name (str): Название региона.
            data (Dict[str, str]): Словарь регионов и их URL.

        Returns:
            Dict[str, str]: Словарь городов и их URL.
        """
        logger.debug(f"Получение городов для региона: {region_name}")
        return self.parse_cities(data.get(region_name, ''))

    def get_dayly_temperature(self, soup: BeautifulSoup) -> Dict[int, str]:
        """
        Получает дневные температуры.

        Args:
            soup (BeautifulSoup): Парсенный HTML страницы.

        Returns:
            Dict[int, str]: Словарь с номерами месяцев и дневными температурами.
        """
        try:
            chart_temp = soup.find(id='chartTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            result_dict: Dict[int, str] = {}
            for element in series_elements:
                text_value = element.get_text().strip()
                for class_name in element.get('class', []):
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        point_number = int(class_name.split('-')[-1]) + 1
                        result_dict[point_number] = text_value
                        logger.debug(f"Дневная температура: Месяц {point_number} -> {text_value}")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка получения дневных температур: {e}")
            raise ParseError(f"Ошибка получения дневных температур: {e}") from e

    def get_night_temperature(self, soup: BeautifulSoup) -> Dict[int, str]:
        """
        Получает ночные температуры.

        Args:
            soup (BeautifulSoup): Парсенный HTML страницы.

        Returns:
            Dict[int, str]: Словарь с номерами месяцев и ночными температурами.
        """
        try:
            chart_temp = soup.find(id='chartTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-1')
            result_dict: Dict[int, str] = {}
            for element in series_elements:
                text_value = element.get_text().strip()
                for class_name in element.get('class', []):
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        point_number = int(class_name.split('-')[-1]) + 1
                        result_dict[point_number] = text_value
                        logger.debug(f"Ночная температура: Месяц {point_number} -> {text_value}")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка получения ночных температур: {e}")
            raise ParseError(f"Ошибка получения ночных температур: {e}") from e

    def get_rainfall(self, soup: BeautifulSoup) -> Dict[int, str]:
        """
        Получает количество осадков.

        Args:
            soup (BeautifulSoup): Парсенный HTML страницы.

        Returns:
            Dict[int, str]: Словарь с номерами месяцев и количеством осадков.
        """
        try:
            chart_temp = soup.find(id='chartPrecip')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            result_dict: Dict[int, str] = {}
            for element in series_elements:
                text_value = element.get_text().strip()
                for class_name in element.get('class', []):
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        point_number = int(class_name.split('-')[-1]) + 1
                        result_dict[point_number] = text_value
                        logger.debug(f"Количество осадков: Месяц {point_number} -> {text_value}")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка получения количества осадков: {e}")
            raise ParseError(f"Ошибка получения осадков: {e}") from e

    def get_water_temperature(self, soup: BeautifulSoup) -> Dict[int, Optional[str]]:
        """
        Получает температуры воды.

        Args:
            soup (BeautifulSoup): Парсенный HTML страницы.

        Returns:
            Dict[int, Optional[str]]: Словарь с номерами месяцев и температурами воды.
        """
        try:
            chart_temp = soup.find(id='chartSeaTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            result_dict: Dict[int, Optional[str]] = {}
            for element in series_elements:
                text_value = element.get_text().strip()
                for class_name in element.get('class', []):
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        point_number = int(class_name.split('-')[-1]) + 1
                        result_dict[point_number] = text_value
                        logger.debug(f"Температура воды: Месяц {point_number} -> {text_value}")
            return result_dict
        except Exception as e:
            logger.warning(f"Нету температуры моря: {e}")
            return {i: None for i in range(1, 13)}

    def get_temperature(self, _url: str) -> Dict[str, Dict[int, Optional[str]]]:
        """
        Получает температуры для конкретного города.

        Args:
            _url (str): Относительный URL города.

        Returns:
            Dict[str, Dict[int, Optional[str]]]: Словарь температур по месяцам.
        """
        try:
            full_url = self.url + _url
            soup = self.get_js_page_content(full_url, by='id', what='chartTemp', run=True)
            day_t = self.get_dayly_temperature(soup)
            night_t = self.get_night_temperature(soup)
            rainfall = self.get_rainfall(soup)
            water_t = self.get_water_temperature(soup)
            temperature_data = {
                'day': day_t,
                'night': night_t,
                'rainfall': rainfall,
                'water': water_t
            }
            logger.info(f"Получены температуры для URL: {full_url}")
            return temperature_data
        except ParseError as e:
            logger.error(f"Ошибка получения температур: {e}")
            raise

    def get_all_temperature(self) -> Dict[int, Dict[int, Dict[str, Optional[str]]]]:
        """
        Получает температуры для всех городов.

        Returns:
            Dict[int, Dict[int, Dict[str, Optional[str]]]]: Словарь с ID городов и их температурами по месяцам.
        """
        try:
            compare_cities = CompareCities()
            compare_cities.union_cities()
            full_cities_data: Dict[int, Dict[int, Dict[str, Optional[str]]]] = {}

            for id_city, value in compare_cities.all_found_cities.items():
                city_name = value[0]
                city_url = value[1]
                logger.info(f"Начало работы с городом: {city_name} (ID: {id_city})")
                try:
                    temperature = self.get_temperature(city_url)
                    full_cities_data[id_city] = {
                        month: {
                            'day': temperature['day'].get(month),
                            'night': temperature['night'].get(month),
                            'rainfall': temperature['rainfall'].get(month),
                            'water': temperature['water'].get(month)
                        }
                        for month in range(1, 13)
                    }
                    logger.info(f"Завершение работы с городом: {city_name} (ID: {id_city})")
                except ParseError:
                    logger.warning(f"Не удалось получить температуры для города: {city_name} (ID: {id_city})")
                    continue

            logger.info("Получение температур для всех городов завершено.")
            return full_cities_data
        except Exception as e:
            logger.error(f"Ошибка в методе get_all_temperature: {e}")
            raise ParseError(f"Ошибка получения всех температур: {e}") from e