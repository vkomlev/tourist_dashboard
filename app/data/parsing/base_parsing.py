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


from app.config import USER_AGENTS_FILE


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