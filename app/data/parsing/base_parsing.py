# app\data\parsing\base_parsing.py

import random
import time
import logging
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc
from dadata import Dadata
import pygetwindow as gw


from app.config import USER_AGENTS_FILE, DADATA_TOKEN


logger = logging.getLogger(__name__)


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
        self.MAX_RETRIES = 3 #Количество попыток получить данные

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
            if not (self.soup or url):
                logger.warning(f"Метод get_data. Нет объектов для парсинга")
                return None
            if not self.soup and url :
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
    
    def click_element(self, by, value):
        """
        Эта функция кликает на веб-элемент, используя указанный атрибут и его значение.

        Parameters:
        by (str): Тип атрибута для поиска элемента
        'id': By.ID,
        'name': By.NAME,
        'class': By.CLASS_NAME,
        'tag': By.TAG_NAME,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT,
        'xpath': By.XPATH,
        'css_selector': By.CSS_SELECTOR
        value (str): Значение атрибута для поиска элемента.
        """
        attribute_dict = {
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT,
            'xpath': By.XPATH,
            'css_selector': By.CSS_SELECTOR
        }

        if by in attribute_dict:
            try:
                element = self.driver.find_element(attribute_dict[by], value)
                ActionChains(self.driver).move_to_element(element).click().perform()
            except:
                logger.error(f"Элемент с атрибутом '{by}' и значением '{value}' не найден.")
        else:
            logger.error(f"by - '{by}' не найден в вариантах attribute_dict.")
        
    def enter_text(self, by, value, text):
        """
        Эта функция вводит текст в поле ввода текста на веб-странице.

        Parameters:
        by (str): Тип атрибута для поиска поля ввода текста.
        'id': By.ID,
        'name': By.NAME,
        'class': By.CLASS_NAME,
        'tag': By.TAG_NAME,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT,
        'xpath': By.XPATH,
        'css_selector': By.CSS_SELECTOR
        value (str): Значение атрибута для поиска поля ввода текста.
        text (str): Текст для ввода в поле ввода текста.
        """
        attribute_dict = {
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT,
            'xpath': By.XPATH,
            'css_selector': By.CSS_SELECTOR
        }

        if by in attribute_dict:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((attribute_dict[by], value))
                )
                element.click()
                self.driver.execute_script("arguments[0].value = '';", element)  # Очистка поля с помощью JavaScript
                element.send_keys(text)
            except:
                logger.error(f"Элемент с атрибутом '{by}' и значением '{value}' не найден.")
        else:
            print(f"by - '{by}' не найден в вариантах attribute_dict.")

    def coordinates_address(
        self, 
        lat: str, 
        lon: str
        )-> list:
        """
        Определяет местоположение по координатам

        Args:
            lat(str): широта
            lon(str): долгота
        Returns:
            [id_region, id_city] or [id_region] or False
        """
        if not (lat and lon):
            logger.info(f'Метод coordinates_address. Не указаны координаты lat={lat}, lon={lon}')
            return None        
        from app.data.compare import CompareYandex
        compare_yandex = CompareYandex()
        compare_yandex.load_regions_city_location_from_database()
        # список всех городов и регионов, с их id
        regions_cities = compare_yandex.input_data_r_c
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                result_dadata = self.coordinates_dadata(lat=lat, lon=lon, regions_cities=regions_cities)
                if not result_dadata:
                    result_geotree = self.coordinates_geotree(lat=lat, lon=lon, regions_cities=regions_cities)
                    if not result_geotree:
                        retries += 1
                    else:
                        logger.info(f'Местополежние определил метод coordinates_geotree - {result_geotree}')
                        return result_geotree
                else:
                    logger.info(f'Местополежние определил метод coordinates_dadata - {result_dadata}')
                    return result_dadata
            except Exception as e:
                logger.error(f'Ошибка в методе coordinates_address: {e}')
                retries += 1
        return False

                

    def coordinates_dadata(
            self, 
            lat: str, 
            lon: str, 
            regions_cities: list
            )-> list:
        """
        Определяет местоположение по координатам через API

        Args:
            lat (str): Широта
            lon (str): Долгота 
            regions_cities (dict): Словарь регионов и городов, с именами регионов и городов в качестве ключей и соответствующим ID в качестве значения.
        Returns:
            [id_region, id_city] or False
        """
        try:
            # токен аккаунта, отсюда https://dadata.ru/api/geolocate/
            token = DADATA_TOKEN
            dadata = Dadata(token)
            result_dadata = dadata.geolocate(name="address", lat=lat, lon=lon)
            result =  result_dadata
            if isinstance(result, dict):
                result = result['unrestricted_value']
            elif isinstance(result, list):
                result = result[0]['unrestricted_value']
            # сейчас result = Свердловская обл, Невьянский р-н, пгт Верх-Нейвинский, пл Революции, д 1
            # меняем сокращения на полные слова
            result =  result.replace(' обл', ' область').replace('Респ ', 'Республика ').replace('пгт ', 'г ')
            # убираем часть с улицей
            result =  [i for i in result.split(', ') if 'область' in i or 'Республика' in i or 'г ' in i]
            result = ' '.join(result).split(' г ')
            id_r_c = []
            for key in regions_cities:
                # проверяет полное совпадение
                if key[0] in result and key[1] in result:
                    id_r_c.append(regions_cities[key])
                    if len(id_r_c) > 1:
                        pass
            if len(id_r_c) == 1:
                logger.info(f'Локация находится в {result}')
                return id_r_c[0]
            elif len(id_r_c) > 1:
                logger.warning(f'Несколько совпадений - всего {id_r_c}. Запрос был - {result}')
            return False
        except Exception as e:
            logger.debug(f'Не удалось определить местоположение в методе coordinates_address: {result_dadata}')
            return False

    def coordinates_geotree(
            self, 
            lat: str, 
            lon: str, 
            regions_cities: list
            )-> list:
        """
        Определяет местоположение по координатам через вэб-скрапинг

        Args:
            lat (str): Широта
            lon (str): Долгота 
            regions_cities (dict): Словарь регионов и городов, с именами регионов и городов в качестве ключей и соответствующим ID в качестве значения.
        Returns:
            [id_region, id_city] or [id_region] or False
        """
        try:
            try:
                self.foxi_user()
                self.driver.get('https://geotree.ru/coordinates')
                self.click_bot()
                time.sleep(1)
                # ввод координат и нажание на кнопку поиска
                self.enter_text(by='id', value='input_lat', text=lat)
                self.enter_text(by='id', value='input_lon', text=lon)
                self.click_element(by='id', value='button_coordinates')
                time.sleep(1)
                self.click_element(by='id', value='button_coordinates')
            except Exception as e:
                logger.error(f'В методе coordinates_geotree при работе с браузером произошла ошбика: {e}')
                self.driver.close()
                self.driver.quit()
                return False
            time.sleep(1)
            # сбор результатов поиска
            page_source = self.driver.page_source
            self.driver.close()
            self.driver.quit()
            self.soup = BeautifulSoup(page_source, 'html.parser')
            result = self.get_data(tag='div', id='div_components_scroller')
            result = [i.text for i in result]
            for region_city in regions_cities:
                if region_city[0] in result and region_city[1] in result:
                    return regions_cities[region_city]
                
                elif region_city[0] in result:
                    region = [regions_cities[region_city][0]]
                    return region
                
                elif ' и '.join(region_city) in result:
                    return regions_cities[region_city]
                
            return False
        except:
            logger.error(f'Ошибкак в методе coordinates_geotree: {e}')
            return False
                

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
            # уточняется версия для ChromeDriver, пишется только основная версия без всяких подверсий 
            options.add_argument('--version=113')
            # options.add_argument(f'user-agent={user_agent}')
            self.driver = uc.Chrome(options=options)
            # меняет user_agent после запуска, до не получилось
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            self.driver.maximize_window()
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
            # # Получаем список всех окон и находим окно браузера
            # windows = gw.getAllTitles()
            # for window in windows:
            #     if "Chrome" in window:  # Найти окно Chrome
            #         gw.getWindowsWithTitle(window)[0].activate()  # Активировать окно
            # logger.debug("Браузер запущен с подмененным User-Agent.")
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
                    self.driver.close()
                    self.driver.quit()
                    return True
                else:
                    time.sleep(10)
            return False
        except Exception as e:
            logger.error(f"Ошибка в методе click_bot: {e}")
            # raise ParseError(f"Ошибка обработки CAPTCHA: {e}") from e


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
                    self.driver.set_page_load_timeout(15)

                self.driver.get(url)
                logger.debug(f"Метод get_js_page_content. Перешли на страницу: {url}")
                if self.click_bot():
                    continue

                if run and by and what:
                    try:
                        way = {'id': By.ID, 'class': By.CLASS_NAME}
                        WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((way.get(by, By.ID), what))
                        )
                        logger.debug(f"Элемент {what} виден на странице.")
                    except Exception as e:
                        logger.warning(f"Ошибка ожидания элемента {what}: {e}")

                if click[0] and click[1]:
                    try:
                        time.sleep(random.uniform(1, 2))
                        element = self.driver.find_element(By.CSS_SELECTOR, click[1])
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        time.sleep(random.uniform(2.5, 5.0))
                        logger.debug(f"Кликнули по элементу {click[1]}.")
                    except Exception as e:
                        logger.error(f"Ошибка клика по элементу {click[1]}: {e}")
                        raise ParseError(f"Ошибка клика: {e}") from e

                # time.sleep(15)
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

    def scroll(
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
            retries = 0
            while retries < self.MAX_RETRIES:
                if url_map:
                    self.foxi_user()
                    self.driver.get(url_map)
                    logger.debug(f"Метод scroll. Перешли на страницу: {url_map}")
                    if self.click_bot():
                        retries += 1
                        continue

                    if check_none and check_none[0]:
                        page_source = self.driver.page_source
                        self.soup = BeautifulSoup(page_source, 'html.parser')
                        self.soup = self.get_data(tag=check_none[1], class_=check_none[2])
                        if self.soup:
                            logger.debug("Необходимые элементы отсутствуют на странице.")
                            # self.driver.close()
                            # self.driver.quit()
                            return None

                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, class_name))
                    )
                    logger.debug(f"Элемент с классом '{class_name}' найден на странице.")
                except Exception as e:
                    logger.error(f"Нету элемента с классом '{class_name}'")
                    # self.driver.close()
                    # self.driver.quit()
                    return None

                try:
                    if click:
                        element = self.driver.find_element(By.CLASS_NAME, class_name)
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        logger.debug(f"Кликнули по элементу с классом '{class_name}'.")
                        time.sleep(random.uniform(1, 3))

                    reviews_section = self.driver.find_element(By.CLASS_NAME, 'scroll__container')
                    last_height = self.driver.execute_script("return arguments[0].scrollHeight", reviews_section)
                    not_good = 0

                    while not_good < self.MAX_RETRIES:
                        try:
                            self.scroll_to_bottom(reviews_section)
                            time.sleep(3)
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

                    # time.sleep(3)
                    page_source = self.driver.page_source
                    logger.debug("Прокрутка завершена, получаем содержимое страницы.")
                    return page_source

                finally:
                    # self.driver.close()
                    # self.driver.quit()
                    logger.debug("Браузер закрыт после прокрутки.")
        except Exception as e:
            logger.error(f"Ошибка в методе scroll_reviews: {e}")
            raise ParseError(f"Ошибка прокрутки страницы: {e}") from e
        
        finally:
            self.driver.close()
            self.driver.quit()
        

    def scroll_to_bottom(self, section: webdriver.remote.webelement.WebElement) -> None:
            """
            Скроллит страницу до конца.

            Args:
                section (webdriver.remote.webelement.WebElement): Секция страницы для прокрутки.
            """
            try:
                time.sleep(1)
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", section)
                logger.debug("Прокрутка до конца секции выполнена.")
            except Exception as e:
                logger.error(f"Ошибка при прокрутке до конца секции: {e}")
                raise ParseError(f"Ошибка прокрутки до конца секции: {e}") from e
    @staticmethod
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
    
    def fetch_xml_data(self) -> ET.Element:
        """
        Загружает XML-фид с указанного URL и возвращает корневой элемент.

        Returns:
            ET.Element: Корневой элемент XML-документа.

        Raises:
            ParseError: Если произошла ошибка при загрузке или парсинге XML.
        """
        try:
            logger.info(f"Загрузка XML-фида по URL: {self.url}")
            response = requests.get(self.url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            root = ET.fromstring(response.text)
            logger.info("XML-фид успешно загружен и распарсен.")
            return root
        except requests.HTTPError as e:
            logger.error(f"HTTP ошибка при загрузке XML-фида: {e}")
            raise ParseError(f"HTTP ошибка: {e}") from e
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML-фида: {e}")
            raise ParseError(f"Ошибка парсинга XML: {e}") from e
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке XML-фида: {e}")
            raise ParseError(f"Неизвестная ошибка: {e}") from e