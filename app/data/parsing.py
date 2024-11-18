# app/data/parsing.py

import random
import time
import logging
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc

from ymaps import Search

from app.config import USER_AGENTS_FILE
from app.data.compare import CompareCities

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ParseError(Exception):
    """Исключение, возникающее при ошибках парсинга."""
    pass


class Parse:
    """Базовый класс для парсинга веб-страниц."""

    def __init__(self, url: str) -> None:
        """
        Инициализирует базовый класс Parse.

        Args:
            url (str): Базовый URL для парсинга.
        """
        self.soup: Optional[BeautifulSoup] = None
        self.url: str = url
        self.driver: Optional[webdriver.Chrome] = None
        self.user_agents: List[str] = []
        self.load_user_agents()

    def get_data(
        self,
        url: str = '',
        tag: Optional[str] = None,
        id: Optional[str] = None,
        class_: Optional[str] = None,
        itemprop: Optional[str] = None,
        all_data: bool = False
    ) -> Union[List[BeautifulSoup], BeautifulSoup, str]:
        """
        Получает данные с веб-страницы.

        Args:
            url (str, optional): Относительный URL для запроса. По умолчанию ''.
            tag (Optional[str], optional): Название тега для поиска. По умолчанию None.
            id (Optional[str], optional): Идентификатор для поиска. По умолчанию None.
            class_ (Optional[str], optional): Класс для поиска. По умолчанию None.
            itemprop (Optional[str], optional): Атрибут itemprop для поиска. По умолчанию None.
            all_data (bool, optional): Флаг для поиска всех элементов. По умолчанию False.

        Returns:
            Union[List[BeautifulSoup], BeautifulSoup, str]: Найденные элементы или текст страницы.
        """
        try:
            if not self.soup and url:
                full_url = self.url + url
                response = requests.get(full_url)
                response.raise_for_status()
                self.soup = BeautifulSoup(response.text, 'html.parser')
                logger.debug(f"Загружена страница: {full_url}")

            if tag:
                search_conditions = {k: v for k, v in {'id': id, 'class': class_, 'itemprop': itemprop}.items() if v}
                if all_data:
                    result = self.soup.find_all(tag, search_conditions)
                    logger.debug(f"Найдено {len(result)} элементов <{tag}> с условиями {search_conditions}.")
                else:
                    result = self.soup.find(tag, search_conditions)
                    logger.debug(f"Найден один элемент <{tag}> с условиями {search_conditions}.")
            else:
                result = self.soup.get_text() if self.soup else ''
                logger.debug("Получен текст страницы.")
            return result
        except requests.HTTPError as e:
            logger.error(f"HTTP ошибка при запросе {self.url + url}: {e}")
            raise ParseError(f"HTTP ошибка: {e}") from e
        except Exception as e:
            logger.error(f"Ошибка в методе get_data: {e}")
            raise ParseError(f"Ошибка получения данных: {e}") from e

    def parse_data(self, result: BeautifulSoup, filter: Any) -> Any:
        """
        Метод для последующего парсинга данных. Реализуется в наследниках.

        Args:
            result (BeautifulSoup): Парсенные данные.
            filter (Any): Фильтр для обработки данных.

        Returns:
            Any: Результат парсинга.
        """
        pass

    def get_free_proxy(self) -> Generator[str, None, None]:
        """
        Получает бесплатные прокси-серверы.

        Yields:
            str: Прокси-сервер в формате 'IP:PORT'.
        """
        try:
            response = requests.get('https://free-proxy-list.net/')
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            for row in table.find_all('tr')[1:]:
                columns = row.find_all('td')
                ip = columns[0].text.strip()
                port = columns[1].text.strip()
                yield f'{ip}:{port}'
        except requests.HTTPError as e:
            logger.error(f"HTTP ошибка при получении прокси: {e}")
            raise ParseError(f"HTTP ошибка при получении прокси: {e}") from e
        except Exception as e:
            logger.error(f"Ошибка в методе get_free_proxy: {e}")
            raise ParseError(f"Ошибка получения прокси: {e}") from e

    def foxi_user(self, run: bool = False) -> None:
        """
        Запускает браузер с подменой User-Agent.

        Args:
            run (bool, optional): Флаг для изменения стратегии загрузки страницы. По умолчанию False.
        """
        try:
            user_agent = self.random_user_agent()
            options = uc.ChromeOptions()
            if run:
                options.page_load_strategy = 'eager'
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_argument(f'user-agent={user_agent}')

            self.driver = uc.Chrome(options=options)
            # Скрываем следы автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("window.navigator.chrome = {runtime: {}}")
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            logger.debug("Браузер запущен с подмененным User-Agent.")
        except Exception as e:
            logger.error(f"Ошибка при запуске браузера: {e}")
            raise ParseError(f"Ошибка запуска браузера: {e}") from e

    def load_user_agents(self) -> None:
        """Загружает список User-Agent из файла."""
        try:
            with open(USER_AGENTS_FILE, 'r') as file:
                self.user_agents = list(set(line.strip() for line in file))
            logger.debug(f"Загружено {len(self.user_agents)} уникальных User-Agent.")
        except FileNotFoundError:
            logger.error(f"Файл {USER_AGENTS_FILE} не найден.")
            raise ParseError(f"Файл {USER_AGENTS_FILE} не найден.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке User-Agent: {e}")
            raise ParseError(f"Ошибка загрузки User-Agent: {e}") from e

    def random_user_agent(self) -> str:
        """
        Выбирает случайный User-Agent из списка и удаляет его из списка.

        Returns:
            str: Случайный User-Agent.
        """
        try:
            if not self.user_agents:
                self.load_user_agents()
            user_agent = random.choice(self.user_agents)
            self.user_agents.remove(user_agent)
            logger.debug(f"Выбран User-Agent: {user_agent}")
            return user_agent
        except IndexError:
            logger.warning("Список User-Agent пуст, повторная загрузка.")
            self.load_user_agents()
            return self.random_user_agent()
        except Exception as e:
            logger.error(f"Ошибка в методе random_user_agent: {e}")
            raise ParseError(f"Ошибка выбора User-Agent: {e}") from e

    def click_bot(self) -> bool:
        """
        Проверяет наличие CAPTCHA и пытается её обойти.

        Returns:
            bool: True, если CAPTCHA обнаружена и обработана, иначе False.
        """
        try:
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            captcha_button = soup.find('input', {'id': 'js-button', 'type': 'submit'})
            if captcha_button:
                element = self.driver.find_element(By.ID, 'js-button')
                ActionChains(self.driver).move_to_element(element).click().perform()
                time.sleep(random.uniform(0.5, 3.0))
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                captcha_confirm = soup.find('button', {
                    'type': 'submit',
                    'data-testid': 'submit',
                    'aria-describedby': 'submit-description',
                    'class': 'CaptchaButton CaptchaButton_view_action CaptchaButton_size_l',
                    'aria-busy': 'false'
                })
                if captcha_confirm:
                    logger.info("CAPTCHA обнаружена и обработана. Повторяем запрос.")
                    time.sleep(random.uniform(30, 60))
                    return True
                else:
                    time.sleep(10)
            return False
        except Exception as e:
            logger.error(f"Ошибка в методе click_bot: {e}")
            raise ParseError(f"Ошибка обработки CAPTCHA: {e}") from e

    def get_js_page_content(
        self,
        url: str,
        by: str = '',
        what: str = '',
        click: Tuple[bool, str] = (False, ''),
        run: bool = False,
        close_: bool = True
    ) -> BeautifulSoup:
        """
        Получает содержимое страницы, которая загружается с помощью JavaScript.

        Args:
            url (str): URL страницы для загрузки.
            by (str, optional): Метод поиска элемента (например, 'id', 'class'). По умолчанию ''.
            what (str, optional): Значение для метода поиска. По умолчанию ''.
            click (Tuple[bool, str], optional): Флаг и селектор для клика. По умолчанию (False, '').
            run (bool, optional): Флаг для использования стратегии загрузки 'eager'. По умолчанию False.
            close_ (bool, optional): Флаг для закрытия браузера после выполнения. По умолчанию True.

        Returns:
            BeautifulSoup: Парсенный HTML страницы.
        """
        try:
            while True:
                self.foxi_user(run=run)
                if run:
                    self.driver.set_page_load_timeout(10)

                self.driver.get(url)
                logger.debug(f"Перешли на страницу: {url}")
                time.sleep(10)

                if self.click_bot():
                    continue

                if run and by and what:
                    try:
                        way = {'id': By.ID, 'class': By.CLASS_NAME}
                        WebDriverWait(self.driver, 20).until(
                            EC.visibility_of_element_located((way.get(by, By.ID), what))
                        )
                        logger.debug(f"Элемент {what} виден на странице.")
                    except Exception as e:
                        logger.warning(f"Ошибка ожидания элемента {what}: {e}")

                if click[0] and click[1]:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, click[1])
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        time.sleep(random.uniform(2.5, 5.0))
                        logger.debug(f"Кликнули по элементу {click[1]}.")
                    except Exception as e:
                        logger.error(f"Ошибка клика по элементу {click[1]}: {e}")
                        raise ParseError(f"Ошибка клика: {e}") from e

                time.sleep(15)
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                return soup

        except Exception as e:
            logger.error(f"Ошибка в методе get_js_page_content: {e}")
            raise ParseError(f"Ошибка получения содержимого страницы: {e}") from e

        finally:
            if close_ and self.driver:
                self.driver.close()
                self.driver.quit()
                logger.debug("Браузер закрыт.")

    @classmethod
    def dictionary_alignment(cls, location: Dict[str, Any], mass_final: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выравнивает вложенные словари.

        Args:
            location (Dict[str, Any]): Входной словарь.
            mass_final (Optional[Dict[str, Any]], optional): Итоговый словарь. По умолчанию None.

        Returns:
            Dict[str, Any]: Выравненный словарь.
        """
        if mass_final is None:
            mass_final = {}

        for key, values in location.items():
            original_key = key
            if key in mass_final:
                key = f"{key}_"
            mass_final[key] = []
            if not isinstance(values, (list, dict)):
                mass_final[key].append(values)
            elif isinstance(values, list):
                for value in values:
                    if isinstance(value, dict):
                        cls.dictionary_alignment(value, mass_final)
                    else:
                        mass_final[key].append(value)
            elif isinstance(values, dict):
                cls.dictionary_alignment(values, mass_final)
            else:
                logger.warning(f"Неизвестный тип данных для ключа {key}: {type(values)}")
        return mass_final


class ParseWeather(Parse):
    """Класс для парсинга погодных данных."""

    def __init__(self) -> None:
        """Инициализирует класс ParseWeather."""
        super().__init__(url='http://russia.pogoda360.ru/')
        logger.info("Инициализирован ParseWeather.")

    def get_region(self) -> BeautifulSoup:
        """
        Получает HTML-код блока с регионами.

        Returns:
            BeautifulSoup: Парсенный HTML блока регионов.
        """
        logger.debug("Получение региона из страницы.")
        return self.get_data(tag='div', id='statesPanel')

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
            data[name] = f'https://{self.url.split("//")[1]}{href}'
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


class ParseYandexMap(Parse):
    """Класс для парсинга данных с Яндекс.Карт."""

    def __init__(self) -> None:
        """Инициализирует класс ParseYandexMap."""
        super().__init__(url='')
        logger.info("Инициализирован ParseYandexMap.")

    def __del__(self) -> None:
        """Закрывает браузер при удалении объекта."""
        if self.driver:
            self.driver.close()
            self.driver.quit()
            logger.debug("Браузер закрыт при удалении объекта ParseYandexMap.")

    def get_location_reviews_and_photos(
        self,
        loc_url: str,
        reviews: bool = True,
        photos: bool = True
    ) -> None:
        """
        Получает отзывы и фото для конкретной локации.

        Args:
            loc_url (str): URL локации.
            reviews (bool, optional): Флаг для получения отзывов. По умолчанию True.
            photos (bool, optional): Флаг для получения фото. По умолчанию True.
        """
        try:
            if reviews:
                self.get_location_reviews(loc_url)
            if photos:
                self.get_location_photos(loc_url)
            logger.debug(f"Получены отзывы и фото для локации: {loc_url}")
        except ParseError as e:
            logger.error(f"Ошибка при получении отзывов и фото: {e}")
            raise

    def get_locations(self, region_city_loc: str) -> Dict[str, str]:
        """
        Получает локации по названию города.

        Args:
            region_city_loc (str): Название города.

        Returns:
            Dict[str, str]: Словарь с названиями локаций и их URL.
        """
        try:
            dict_locations: Dict[str, str] = {}
            self.foxi_user()
            self.driver.get("https://yandex.ru/maps")
            logger.debug("Перешли на Яндекс.Карты.")
            time.sleep(5)

            if self.click_bot():
                return {}

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            nothing_found = self.get_data(tag='div', class_='nothing-found-view__header')
            alone_location = self.get_data(tag='a', class_='card-title-view__title-link')
            mass_locations = self.get_data(tag='a', class_='link-overlay', all_data=True)

            if nothing_found:
                logger.info(f"Локации в {region_city_loc} не найдены.")
                return {}

            elif alone_location:
                dict_locations[alone_location.text.strip()] = f"https://yandex.ru{alone_location.get('href', '').strip()}"
                logger.debug(f"Найдена одна локация: {alone_location.text.strip()} -> {dict_locations[alone_location.text.strip()]}")
            elif mass_locations:
                self.soup = self.scroll_reviews(class_name='search-business-snippet-view', click=True)
                soup = BeautifulSoup(self.soup, 'html.parser')
                locations = self.get_data(tag='a', class_='link-overlay', all_data=True)
                for loc in locations:
                    loc_name = loc.get('aria-label', '').strip()
                    loc_href = loc.get('href', '').strip()
                    if loc_name and loc_href:
                        dict_locations[loc_name] = f"https://yandex.ru{loc_href}"
                        logger.debug(f"Найдена локация: {loc_name} -> https://yandex.ru{loc_href}")
            else:
                logger.warning("Неизвестная структура страницы.")
                return {}

            logger.info(f"Получено {len(dict_locations)} локаций для города {region_city_loc}.")
            return dict_locations

        except Exception as e:
            logger.error(f"Ошибка в методе get_locations: {e}")
            raise ParseError(f"Ошибка получения локаций: {e}") from e

    def get_loc_type_td(
        self,
        url: str,
        sql_city: str,
        full_get_info: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о типе локации.

        Args:
            url (str): URL локации.
            sql_city (str): Название города из базы данных.
            full_get_info (bool, optional): Флаг для полного получения информации. По умолчанию False.

        Returns:
            Optional[Dict[str, Any]]: Информация о локации или None.
        """
        try:
            id_yandex = int([part for part in url.split('/') if part.isdigit()][0])
            self.soup = self.get_js_page_content(url, by='id', what='chartTemp', run=True)
            logger.debug(f"Получение информации о локации с ID Yandex: {id_yandex}")

            # Проверка соответствия города
            html_city = self.get_data(tag='a', class_='breadcrumbs-view__breadcrumb _outline', all_data=True)
            city = html_city[1].get('title') if len(html_city) > 1 else ''
            index = 3 if len(sql_city) <= 5 else 5
            if not (city == sql_city or city[:index] == sql_city[:index]):
                alternative_city = self.get_data(tag='a', class_='business-contacts-view__address-link').text.strip().split(' ')
                if not (sql_city in alternative_city or sql_city[:5] in alternative_city):
                    logger.info(f"Локация принадлежит другому городу: {alternative_city}, требуется {sql_city}")
                    return None

            # Количество лайков
            element_like = self.get_data(tag='div', class_="business-header-rating-view__text _clickable")
            count_like = element_like.text.split(' ')[0] if element_like else '0'

            # Средняя оценка
            like = self.get_data(tag='span', class_="business-rating-badge-view__rating-text").text.strip()

            # Особенности
            features_http = self.get_data(tag='div', class_='business-features-view _wide _view_overview _orgpage')
            features = {
                'features_text': [item.text.strip() for item in features_http.find_all('div', {'class': 'business-features-view__bool-text'})],
                'features_key': {
                    item.find('span', {'class': 'business-features-view__valued-title'}).text.strip():
                        item.find('span', {'class': 'business-features-view__valued-value'}).text.strip()
                    for item in features_http.find_all('div', {'class': 'business-features-view__valued'})
                }
            }

            # Типы локации
            types = [item.text.strip() for item in self.get_data(tag='div', class_='orgpage-categories-info-view').find_all('span', {'class': 'button__text'})]

            # Координаты
            coordinates_div = self.soup.find('div', {'class': 'card-feature-view _view_normal _size_large _interactive _no-side-padding card-share-view__coordinates'})
            coordinates_text = self.get_data(tag='div', class_='card-share-view__text').text.strip().split(', ') if coordinates_div else ['', '']
            coordinates = [coordinates_text[1], coordinates_text[0]] if len(coordinates_text) == 2 else [None, None]

            loc_info = {
                'count_like': count_like,
                'like': like,
                'types': types,
                'coordinates': coordinates,
                'id_yandex': id_yandex,
                'features': features
            }

            if full_get_info:
                self.get_location_reviews_and_photos(loc_url=url)

            logger.debug(f"Информация о локации: {loc_info}")
            return loc_info

        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка обработки данных о локации: {e}")
            raise ParseError(f"Ошибка обработки данных о локации: {e}") from e
        except Exception as e:
            logger.error(f"Неизвестная ошибка в методе get_loc_type_td: {e}")
            raise ParseError(f"Неизвестная ошибка: {e}") from e

    def get_location_reviews(self, url: str) -> Dict[int, Dict[str, Union[int, str]]]:
        """
        Получает отзывы для конкретной локации.

        Args:
            url (str): URL локации.

        Returns:
            Dict[int, Dict[str, Union[int, str]]]: Словарь отзывов.
        """
        try:
            self.soup = self.scroll_reviews(
                url_map=f"{url}reviews/",
                class_name='business-reviews-card-view__space',
                click=True,
                check_none=[True, 'h2', 'tab-empty-view__title']
            )
            if self.soup is True:
                logger.info("Отзывов не найдено.")
                return {}

            soup = BeautifulSoup(self.soup, 'html.parser')
            reviews = self.get_data(tag='div', class_='business-reviews-card-view__review', all_data=True)
            reviews_filter: Dict[int, Dict[str, Union[int, str]]] = {}
            for i, review in enumerate(reviews, 1):
                try:
                    review_like = len(review.find_all('span', {'class': 'inline-image _loaded icon business-rating-badge-view__star _full'}))
                    review_text = review.find('span', {'class': 'business-review-view__body-text'}).get_text(strip=True)
                    review_date = review.find('meta', {'itemprop': 'datePublished'}).get('content', '').split('T')[0]
                    reviews_filter[i] = {
                        'like': review_like,
                        'text': review_text,
                        'date': review_date
                    }
                    logger.debug(f"Отзыв {i}: {reviews_filter[i]}")
                except AttributeError:
                    logger.warning(f"Некорректная структура отзыва #{i}.")
                    continue

            self.loc_reviews = reviews_filter
            logger.info(f"Получено {len(reviews_filter)} отзывов.")
            return reviews_filter

        except ParseError as e:
            logger.error(f"Ошибка получения отзывов: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка в методе get_location_reviews: {e}")
            raise ParseError(f"Неизвестная ошибка при получении отзывов: {e}") from e

    def get_location_photos(self, url: str) -> Dict[int, Optional[str]]:
        """
        Получает фото для конкретной локации.

        Args:
            url (str): URL локации.

        Returns:
            Dict[int, Optional[str]]: Словарь фото.
        """
        try:
            self.soup = self.scroll_reviews(
                url_map=f"{url}gallery/",
                class_name='media-wrapper__media',
                click=True,
                check_none=[True, 'h2', 'tab-empty-view__title']
            )
            if self.soup is True:
                logger.info("Фотографий не найдено.")
                return {1: None}

            soup = BeautifulSoup(self.soup, 'html.parser')
            photos_html = self.get_data(tag='img', class_='media-wrapper__media', all_data=True)
            dict_photos: Dict[int, Optional[str]] = {}
            for i, photo in enumerate(photos_html, 1):
                photo_src = photo.get('src', '').strip()
                dict_photos[i] = photo_src if photo_src else None
                logger.debug(f"Фото {i}: {dict_photos[i]}")

            self.loc_photos = dict_photos
            logger.info(f"Получено {len(dict_photos)} фотографий.")
            return dict_photos

        except ParseError as e:
            logger.error(f"Ошибка получения фото: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка в методе get_location_photos: {e}")
            raise ParseError(f"Неизвестная ошибка при получении фото: {e}") from e

    def scroll_reviews(
        self,
        class_name: str,
        check_none: Optional[List[Union[bool, str, str]]] = None,
        url_map: str = '',
        click: bool = False
    ) -> Union[str, bool]:
        """
        Скроллит страницу для загрузки всех отзывов или фотографий.

        Args:
            class_name (str): Класс элементов для поиска.
            check_none (Optional[List[Union[bool, str, str]]], optional): Параметры проверки отсутствия элементов. По умолчанию None.
            url_map (str, optional): URL для перехода. По умолчанию ''.
            click (bool, optional): Флаг для клика по элементу. По умолчанию False.

        Returns:
            Union[str, bool]: HTML страницы или True, если элементы отсутствуют.
        """
        try:
            while True:
                if url_map:
                    self.foxi_user()
                    self.driver.get(url_map)
                    logger.debug(f"Перешли на страницу: {url_map}")
                    time.sleep(10)

                    if self.click_bot():
                        continue

                    if check_none and check_none[0]:
                        soup = self.get_data(tag=check_none[1], class_=check_none[2])
                        if soup:
                            logger.info("Необходимые элементы отсутствуют на странице.")
                            self.driver.close()
                            self.driver.quit()
                            return True

                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, class_name))
                    )
                    logger.debug(f"Элемент с классом '{class_name}' найден на странице.")
                except Exception as e:
                    logger.warning(f"Элемент с классом '{class_name}' не найден: {e}")
                    self.driver.close()
                    self.driver.quit()
                    continue

                try:
                    if click:
                        element = self.driver.find_element(By.CLASS_NAME, class_name)
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        logger.debug(f"Кликнули по элементу с классом '{class_name}'.")
                        time.sleep(random.uniform(2.5, 5.0))

                    reviews_section = self.driver.find_element(By.CLASS_NAME, 'scroll__container')
                    last_height = self.driver.execute_script("return arguments[0].scrollHeight", reviews_section)
                    not_good = 0

                    while not_good < 3:
                        try:
                            self.scroll_to_bottom(reviews_section)
                            time.sleep(5)
                            new_height = self.driver.execute_script("return arguments[0].scrollHeight", reviews_section)
                            if new_height == last_height:
                                not_good += 1
                                logger.debug("Высота прокрутки не изменилась.")
                            else:
                                not_good = 0
                                last_height = new_height
                                logger.debug("Высота прокрутки изменилась, продолжаем прокрутку.")
                        except Exception as e:
                            logger.error(f"Ошибка при прокрутке: {e}")
                            not_good += 1

                    time.sleep(5)
                    page_source = self.driver.page_source
                    logger.debug("Прокрутка завершена, получаем содержимое страницы.")
                    return page_source

                finally:
                    self.driver.close()
                    self.driver.quit()
                    logger.debug("Браузер закрыт после прокрутки.")
        except Exception as e:
            logger.error(f"Ошибка в методе scroll_reviews: {e}")
            raise ParseError(f"Ошибка прокрутки страницы: {e}") from e

    def scroll_to_bottom(self, section: webdriver.remote.webelement.WebElement) -> None:
        """
        Скроллит страницу до конца.

        Args:
            section (webdriver.remote.webelement.WebElement): Секция страницы для прокрутки.
        """
        try:
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", section)
            logger.debug("Прокрутка до конца секции выполнена.")
        except Exception as e:
            logger.error(f"Ошибка при прокрутке до конца секции: {e}")
            raise ParseError(f"Ошибка прокрутки до конца секции: {e}") from e

    def get_locations_api(self, name_city: str, type_loc: str) -> List[Dict[str, Any]]:
        """
        Получает список локаций через API Яндекс.Карт.

        Args:
            name_city (str): Название города.
            type_loc (str): Тип локации.

        Returns:
            List[Dict[str, Any]]: Список локаций.
        """
        all_api_keys = ['547d8501-74fd-46af-930a-9ea2fff048bf']
        current_key = 0
        lang = 'ru_RU'
        client = Search(all_api_keys[current_key])
        address = f"{name_city} {type_loc}"
        all_loc = 1000
        get_loc = 0

        try:
            while all_loc > get_loc:
                response = client.search(text=address, lang=lang, rspn=True, results=50, skip=get_loc)
                if 'error' in response:
                    if current_key + 1 < len(all_api_keys):
                        current_key += 1
                        client = Search(all_api_keys[current_key])
                        logger.warning(f"API ключ недействителен, переключение на ключ {current_key}.")
                        continue
                    else:
                        logger.error("Достигнут лимит парсинга API.")
                        break

                properties = response.get('properties', {})
                all_loc = properties.get('ResponseMetaData', {}).get('SearchResponse', {}).get('found', 0)
                get_loc += 50

                features = response.get('features', [])
                return features

        except Exception as e:
            logger.error(f"Ошибка в методе get_locations_api: {e}")
            raise ParseError(f"Ошибка получения локаций через API: {e}") from e

    def get_location_reviews_summary(self, loc_url: str) -> Dict[str, Any]:
        """
        Получает сводную информацию об отзывах для локации.

        Args:
            loc_url (str): URL локации.

        Returns:
            Dict[str, Any]: Сводная информация об отзывах.
        """
        try:
            url = f'https://yandex.ru/maps-reviews-widget/{loc_url}?comments'
            soup = self.get_data(url=url, tag='a', class_='badge__more-reviews-link')
            href = soup.get('href', '').strip() if soup else ''
            if not href:
                logger.warning(f"Ссылка на отзывы не найдена для URL: {loc_url}")
                raise ParseError("Ссылка на отзывы не найдена.")

            number = self.get_data(tag='p', class_='mini-badge__stars-count')
            number = float(number.text.replace(',', '.')) if number else 0.0

            count_ = self.get_data(tag='a', class_='mini-badge__rating')
            count_split = count_.text.split(' ') if count_ else []
            count_data = {
                'отзывы': int(count_split[0]) if len(count_split) > 0 and count_split[0].isdigit() else 0,
                'оценки': int(count_split[3]) if len(count_split) > 3 and count_split[3].isdigit() else 0
            }

            logger.debug(f"Сводная информация об отзывах: URL_map={href}, number={number}, count={count_data}")
            return {'url_map': href, 'number': number, 'count': count_data}

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка обработки данных в get_location_reviews_summary: {e}")
            raise ParseError(f"Ошибка обработки данных: {e}") from e
        except Exception as e:
            logger.error(f"Неизвестная ошибка в методе get_location_reviews_summary: {e}")
            raise ParseError(f"Неизвестная ошибка: {e}") from e
