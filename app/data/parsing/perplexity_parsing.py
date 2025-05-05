from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys  # Для отправки Enter
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc
import time
import os
import random
import json
from bs4 import BeautifulSoup
from app.data.parsing import Parse
import re

class ParsePerplexity(Parse):
    def __init__(self):
        self.user_id = 1
        super().__init__(url='https://www.perplexity.ai/search/')
        

    def create_driver(self, us_ag = False):
        """
         us_ag - подмена user_agent, для телеграма и вацапа не требуется
        Запускает браузер и если необходимо с использованием профиля для сайтов с авторизацией
        user_id номер профиля
            telegram = 1
            WhatsApp = 2
            perplexity = 3
        """
        if us_ag:
            user_agent = self.random_user_agent()
        options = uc.ChromeOptions()

        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--version=113')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')

        # if self.user_id != 0:
        #     user_directory = os.path.join(self.create_file_profile(), f'user_{self.user_id}')
        #     if not os.path.exists(user_directory):
        #         os.makedirs(user_directory)

        #     options.add_argument(f"user-data-dir={user_directory}")

        driver = uc.Chrome(options=options)

        # увеличиваем время ожидания выполнения какой либо задачи, 
        # всегда нужно когда длинный текст вводится с имитацией человеческого ввода
        driver.command_executor.set_timeout(10000)
        if us_ag:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        driver.maximize_window()

        # Скрываем следы автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("window.navigator.chrome = {runtime: {}}")
        driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        driver.execute_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        return driver
    
    def registration_perplexity(self):
        """
        регистрация в perplexity
        """
        restart = 0
        driver = self.create_driver(us_ag=True)
        driver.get(self.url)
        while restart < 30:
            # Элемент который есть только если вы ещё не авторезировались 
            element_email = self.search_element(driver=driver,
                        element= 'w-full outline-none focus:outline-none focus:ring-borderMain font-sans flex items-center dark:bg-offsetDark dark:text-textMainDark dark:placeholder-textOffDark dark:border-borderMainDark dark:focus:ring-borderMainDark selection:bg-superDuper selection:text-textMain duration-200 transition-all bg-background border text-textMain border-borderMain focus:ring-1 placeholder-textOff rounded-t-[32px] rounded-b-[32px] rounded-b-[4px] rounded-t-[4px] py-sm md:text-sm px-md pr-md',
                        by= 'class'
                        )
            
            # Элемент который есть только в чате с ботом
            element_question = self.search_element(driver=driver,
                        element= '__next',
                        by= 'id'
                        )
            if not element_email and element_question:
                driver.close()
                driver.quit()
                print(f"Авторизация на {self.url} прошла успешно")
                break
            else:
                restart +=1
        if not element_question:
            print('Если вы видете это сообщение это значит что вы не успели авторизоваться на сайте')
        
    def analyze_text_with_perplexity(self, request_bot):
        """
        Принимает инструкцию и текст, отправляет запрос в Perplexity AI,
        собирает ответ и выводит таблицу pandas.

        Args:
            instruction (str): Инструкция для анализа текста.
            text_to_analyze (str): Текст, который необходимо проанализировать.

        Returns:
            pandas.DataFrame: DataFrame с результатами анализа, или None в случае ошибки.
        """
        try:
            driver = self.create_driver()
            driver.get(self.url)

            # Находим поле ввода промпта (замените селектор, если необходимо)
            input = self.search_element(driver=driver,
                                        element="textarea",
                                        by='css',
                                        )

            # Формируем промпт
            self.get_txt_imitation(input=input, 
                        driver=driver,
                        request_bot=request_bot
                        )
            array_elements = self.extract_array(driver=driver)
            return array_elements

        except Exception as e:
            print(f"Произошла ошибка: {e}")
            return None

        finally:
            driver.close()
            driver.quit()

    def extract_array(self, driver):
        # Ищем последний элемент с кодом
        text= self.search_element(driver=driver,
                                        element="my-0",
                                        by='class',
                                        alone=True
                                        ).text

        # Берем последний элемент
        pattern = r'\d+\.\d+|\d+'
        numbers = re.findall(pattern, text)

        return numbers[0]
    
    def search_element(self, driver, element:str, by:str, alone:bool=True):
        """
        Поиск элемента на странице по заданному локатору.
        :param driver: Объект WebDriver для взаимодействия с браузером.
        :param element: Строка-локатор для поиска элемента.
        :param by: Тип локатора (по умолчанию 'css'). Доступные варианты:
            - 'css': CSS-селектор
            - 'xpath': XPath-выражение
            - 'id': ID элемента
            - 'name': Имя элемента
            - 'tag': Тег элемента
            - 'class': Класс элемента
            - 'link_text': Текст ссылки
            - 'partial_link_text': Частичный текст ссылки
        :param alone: Определяет количество элементов которые необходимо найти 
                По умолчанию True - находим первое совпадение
        :return: Найденный элемент или None, если элемент не найден.
        """

        # Словарь для сопоставления строковых вариантов с константами By
        by_variants = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'tag': By.TAG_NAME,
            'class': By.CLASS_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT
        }
        time.sleep(5)
        if by in by_variants.keys():
            try:
                if alone:
                    element_s = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((by_variants[by], element))
                                    )
                else:
                    element_s = WebDriverWait(driver, 10).until(
                                    EC.presence_of_all_elements_located((by_variants[by], element))
                                    )
                if element_s:
                    return element_s
                else:
                    # print('Такой элемент по такому локатору не найден')
                    # print(f'Элемент:{element}\nЛокатор {by}')
                    return None
                    
            except:
                # print('Ошибка в функциипри search_element')
                return None
        else:
            print(f"Такого значения by нету, выберите из списка представленного в функции search_element")

    def get_txt_imitation(self, input, driver, request_bot = 'Продолжи'):
        """
        Имитация ввода текста человеком, чтобы не блокал сайт
        input - элемент строки
        driver - образ браузера
        request_bot - вводимый текст
        """
        actions = ActionChains(driver)
        actions.send_keys_to_element(input, request_bot).send_keys(Keys.ENTER).perform()
        time.sleep(5)

    def create_file_profile(self):
        # Создаем папку users в корне проекта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_directory = os.path.join(script_dir, 'users')

        if not os.path.exists(base_directory):
            os.makedirs(base_directory)
        return base_directory
    
