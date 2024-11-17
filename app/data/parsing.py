import requests 
from bs4 import BeautifulSoup 
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
import time
from ymaps import Search
# from selenium.webdriver.firefox.options import Options as FirefoxOptions
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.proxy import Proxy, ProxyType
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
import secrets
import random
# from webdriver_manager.chrome import ChromeDriverManager
# from app.data.compare import Compare_cities
from app.config import USER_AGENTS_FILE

class Parse:

    def __init__(self, url):
        self.soup = None
        self.url = url


    def get_data(self, url='', tag = None, id = None, class_ = None, itemprop = None, all_data = False): 
        try:
            if not self.soup and url:
                response = requests.get(self.url + url) 
                self.soup = BeautifulSoup(response.text, 'html.parser')
            if tag:
                elements = {'id':id, 'class':class_, 'itemprop': itemprop}
                conditions = {f'{k}': v for k,v in elements.items() if v != None}
                if all_data:
                    result = self.soup.find_all(tag, conditions)
                else:
                    result = self.soup.find(tag, conditions)
            else:
                result = self.soup.text
            return result
        except Exception as e:
            print(f'Ошибка в get_data, {e}')
    
    def parse_data(self, result, filter):
        pass
    
    def get_free_proxy(self):
        response = requests.get('https://free-proxy-list.net/')
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        for row in table.find_all('tr')[1:]:
            columns = row.find_all('td')
            ip = columns[0].text
            port = columns[1].text
            yield f'{ip}:{port}'
            
    # запускает браузер лиса с user_agent
    def foxi_user(self,  run =False):
        # для случайных User-Agent  
        user_agent = self.random_user_agent() 
        # print(user_agent)       
              
        # profile = FirefoxProfile()
        # # устанавливаем своего User-Agent 
        # profile.set_preference("general.useragent.override", user_agent)
        # # попытка скрыть, бота
        # profile.set_preference("dom.webdriver.enabled", False)
        # profile.set_preference('useAutomationExtension', False)
        # profile.update_preferences
        # options = FirefoxOptions()
        # options.add_argument('--disable-features=NetworkService')
        # options.add_argument('--disable-dev-shm-usage')
        # options.add_argument('--no-first-run')
        # options.add_argument('--no-default-browser-check')
        # options.add_argument('--no-sandbox')
        # options.add_argument('--disable-blink-features=AutomationControlled')
        # options.set_preference('excludeSwitches', 'enable-automation')
        # proxy = next(self.get_free_proxy())
        # options.set_preference('network.proxy.type', 1)
        # options.set_preference('network.proxy.http', proxy.split(':')[0])
        # options.set_preference('network.proxy.http_port', int(proxy.split(':')[1]))

        # # Быстрая загрузка, не дожидается полной загрузки ресурсов
        # if run:
        #     options.page_load_strategy = 'eager'  
        
        # self.driver = webdriver.Firefox(options=options)

        options = uc.ChromeOptions()
        if run:
            options.page_load_strategy = 'eager'
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument(f'user-agent={user_agent}')
        self.driver = uc.Chrome(options=options)
        # Пример скрытия некоторых следов автоматизации
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
        



    # берёт user_agents из файла 
    def get_user_agents(self):
        try:
            file = open(USER_AGENTS_FILE, 'r')
            self.user_agents = list(set(file.readlines()))
            # self.user_agents = [i for i in user_agents if not 'Safari' in i]
            # print(len(self.user_agents))
        finally:
            file.close()
    
    # берёт рандомнй и удаляет из списка, чтобы не повторялись
    def random_user_agent(self):
        while True:
            try:
                user_agent = secrets.choice(self.user_agents)
                self.user_agents.remove(user_agent)
                return user_agent
            except:
                # print('Агенты кончились, повторяем')
                self.get_user_agents()
                continue

    def click_bot(self):
        # <input type="submit" id="js-button" class="CheckboxCaptcha-Button" aria-ch>
        html = self.driver.page_source
        html = BeautifulSoup(html, 'html.parser')
        elements = {'id':'js-button', 'type':'submit'}
        result = html.find('input', elements)
        if result:
            element = self.driver.find_element(By.ID, 'js-button')
            actions = ActionChains(self.driver)
            actions.move_to_element(element).click().perform()
            time.sleep(random.randrange(1,6)/2)
            html = self.driver.page_source
            html = BeautifulSoup(html, 'html.parser')
            elements = {'type':'submit', 
                        'data-testid':'submit',
                        'aria-describedby':'submit-description',
                        'class':'CaptchaButton CaptchaButton_view_action CaptchaButton_size_l',
                        'aria-busy':'false'
                        }
            result = html.find('button', elements)
            if result:
                print('Проверка на бота ожидаем и повторяем')
                time.sleep(random.randrange(60,120))
                return True
            else:
                time.sleep(10)


    # обращается к сайту как пользователь и возвращает его код
    def get_JS_page_content(self, url, by='', what='', click = [False, ''], run =False, close_ = True): 
        while True:
            try: 
                # словарь с методами поиска
                way = {'id' : By.ID, 'class' : By.CLASS_NAME}

                # запуск браузера
                self.foxi_user(run=run)

                if run:
                    # Установка времени загрузки страницы
                    self.driver.set_page_load_timeout(10)
                
                self.driver.get(url)
                time.sleep(10)
                check_bot = self.click_bot()
                if check_bot:
                    continue
                
                # если не нужно ждать прогрузки всего сайта а только чего то конкретного
                # используется для ускорения сбора данных
                if run:
                    # Явное ожидание, например, ожидание видимости элемента с id 'content'
                    try:
                        WebDriverWait(self.driver, 20).until(
                            EC.visibility_of_element_located((way[by], what))
                        )
                    except Exception as e:
                        print(f"Ожидание завершено с ошибкой: {e}")

                # если куда-то нужно нажать для прогрузки элементов
                if click[0]:
                    element = self.driver.find_element(By.CSS_SELECTOR, click[1])
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).click().perform()
                    time.sleep(random.randrange(5,10))

                time.sleep(15)
                # Получаем HTML страницы
                pageSource = self.driver.page_source
                # Используем BeautifulSoup для анализа страницы
                bs = BeautifulSoup(pageSource, 'html.parser')
                return bs
            
            except Exception as e: 
                print(e)

            finally: 
                if close_:
                    self.driver.close()
                    self.driver.quit()
                    

    # Выравнивание словаря
    @classmethod
    def dictionary_alignment(self, location, mass_final = {}):
        for key, values in location.items():
            if mass_final.get(key):
                key = key + '_'
            mass_final[key] = []
            if not (isinstance(values, list) or isinstance(values, dict)) :
                mass_final[key] = mass_final[key] + [values]
            elif isinstance(values, list):
                for value in values:
                    if isinstance(value, dict):
                        mass_final = mass_final|self.dictionary_alignment(value, mass_final)
                    else:
                        mass_final[key] = mass_final[key] + [value]
            elif isinstance(values, dict):
                mass_final = mass_final|self.dictionary_alignment(values, mass_final)
            else:
                print(key, value)
                print(type(value))
        return mass_final
        
class Parse_weather(Parse):

    def __init__(self):
        super().__init__('')
        self.url = 'http://russia.pogoda360.ru/'

    # берёт таблицу с регионами
    def get_region(self):
        return self.get_data(tag='div', id='statesPanel')
    
    # берёт таблицу с городами
    def get_cities(self, url):
        return self.get_data(url=url ,tag='div', id='citiesPanel')

    # делает словарь где ключ - регион или город, а значение добавочный url
    def parse_data(self, result, tag):
        result = result.find_all(tag)
        data = {}
        for item in result:
            if '(' in item.text:
                data[item.text[:item.text.rfind('(')-1]] = item.get('href')
            else: 
                data[item.text] = item.get('href')
        return data
    
    # берёт список регионов, фильтрует и выдает в формате словаря
    def parse_regions(self):
        result = self.get_region()
        return self.parse_data(result, tag='a')
    
    # берёт список городов, фильтрует и выдает в формате словаря
    def parse_cities(self, url):
        # try:
            result = self.get_cities(url)
            return self.parse_data(result, tag='a')
        # except Exception as e:
        #     print(e)
        # finally:
        #     self.driver.close()
        #     self.driver.quit()

    
    # выдает список городов для конкретного региона
    def get_city_from_region(self, region_name, data):
        return self.parse_cities(data[region_name])
    
    # Делает словарь где ключ - номер месяца, а значение температура возруха днем
    def get_dayly_temperature(self, bs):
        try:
            # Находим родительский элемент с ID 'chartTemp'
            chart_temp = bs.find(id='chartTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            # Создаем словарь для хранения результатов
            result_dict = {}
            # Обрабатываем найденные элементы
            for element in series_elements:
                # Извлекаем текст элемента
                text_value = element.get_text()
                # Ищем класс с шаблоном 'jqplot-point-*'
                for class_name in element['class']:
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        # Извлекаем число из класса 
                        point_number = int(class_name.split('-')[-1])
                        # Увеличиваем число на 1 и используем его в качестве ключа
                        result_dict[point_number + 1] = text_value
            return result_dict
    
        except Exception as e:
            print(e)
    
    # Делает словарь где ключ - номер месяца, а значение температура возруха ночью
    def get_night_temperature(self, bs):
        try:
            # Находим родительский элемент с ID 'chartTemp'
            chart_temp = bs.find(id='chartTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-1')
            # Создаем словарь для хранения результатов
            result_dict = {}
            # Обрабатываем найденные элементы
            for element in series_elements:
                # Извлекаем текст элемента
                text_value = element.get_text()
                # Ищем класс с шаблоном 'jqplot-point-*'
                for class_name in element['class']:
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        # Извлекаем число из класса 
                        point_number = int(class_name.split('-')[-1])
                        # Увеличиваем число на 1 и используем его в качестве ключа
                        result_dict[point_number + 1] = text_value
            return result_dict
        
        except Exception as e:
            print(e)
    
    # Делает словарь где ключ - номер месяца, а значение количество осадков в мм
    def get_rainfall(self, bs):
        try:
            # Находим родительский элемент с ID 'chartTemp'
            chart_temp = bs.find(id='chartPrecip')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            # Создаем словарь для хранения результатов
            result_dict = {}
            # Обрабатываем найденные элементы
            for element in series_elements:
                # Извлекаем текст элемента
                text_value = element.get_text()
                # Ищем класс с шаблоном 'jqplot-point-*'
                for class_name in element['class']:
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        # Извлекаем число из класса 
                        point_number = int(class_name.split('-')[-1])
                        # Увеличиваем число на 1 и используем его в качестве ключа
                        result_dict[point_number + 1] = text_value
            return result_dict
    
        except Exception as e:
            print(e)

    # Делает словарь где ключ - номер месяца, а значение температура воды
    def get_water_temperature(self, bs):
        try:
            # Находим родительский элемент с ID 'chartTemp'
            chart_temp = bs.find(id='chartSeaTemp')
            series_elements = chart_temp.find_all('div', class_='jqplot-series-0')
            # Создаем словарь для хранения результатов
            result_dict = {}
            # Обрабатываем найденные элементы
            for element in series_elements:
                # Извлекаем текст элемента
                text_value = element.get_text()
                # Ищем класс с шаблоном 'jqplot-point-*'
                for class_name in element['class']:
                    if class_name.startswith('jqplot-point-') and class_name != 'jqplot-point-label':
                        # Извлекаем число из класса 
                        point_number = int(class_name.split('-')[-1])
                        # Увеличиваем число на 1 и используем его в качестве ключа
                        result_dict[point_number + 1] = text_value
            return result_dict
        
        except Exception as e:
            print('\t\tНету температуры моря: ', e)

    # Потучает словарь температур в одном городе 
    # (дневная ночная температура воздуха и температуру воды)
    def get_temperature(self, _url):
        while True:
            try:
                url = self.url + _url
                bs = self.get_JS_page_content(url, by = 'id', what='chartTemp', run=True)
                day_t = self.get_dayly_temperature(bs)
                night_t = self.get_night_temperature(bs)
                rainfall = self.get_rainfall(bs)
                water_t = self.get_water_temperature(bs)
                if water_t:
                    return {'day': day_t, 'night': night_t, 'rainfall': rainfall, 'water': water_t}
                else:
                    return {'day': day_t, 'night': night_t, 'rainfall': rainfall, 'water': {f'{i}':None for i in range(1,13)}}      
            except Exception as e:
                print(e)
                print('что-то сломалось жду 60 секунд и пробую ещё раз')
                time.sleep(60)
                continue
    
    # ЗАПУСКАТЬ - выдает температуры по городам, где ключ это id города из БД,
    # а значение словарь где ключ номер месяца, а значение словарь температур day, night и water
    def get_all_temperature (self):
        from app.data.compare import Compare_cities
        compare_cities = Compare_cities()
        compare_cities.union_cities()
        self.full_cities_data = {}
        for id_city, value in compare_cities.all_found_cities.items():
            while True:
                try:
                    print('Начало работы с ', value[0])
                    temperature = self.get_temperature(value[1])
                    self.full_cities_data[id_city] = {}
                    for i in range(1,13):
                        self.full_cities_data[id_city][i] = {
                            'day':temperature.get('day').get(i),
                            'night':temperature.get('night').get(i),
                            'rainfall':temperature.get('rainfall').get(i),
                            'water':temperature.get('water').get(i)
                            }
                    print('Окончание работы с ', value[0])
                    break
                except:
                    print('-'*20)
                    print('Что то пошло не так c', id_city)
                    print(temperature)
                    print('-'*20)
                    continue
        


# Парсит яндекс карты для получения отзывов, оценок и фото локаций
class Parse_yandex_map(Parse):

    def __init__(self):
        self.soup = None
        self.url = ''
        self.driver = None

    def __del__(self):
        pass
        

    # Запускаем для полного сбора информации в одной локации
    def get_location_rewiews_and_photos(self, loc_url, rewiews=True, photos = True):
        if rewiews:
            self.get_location_rewiews(loc_url)
        if photos:
            self.get_location_photos(loc_url)

    # берёт локации по городу и выдает словарь, где ключ это название локации, а значение ее url
    def get_locations(self, region_city_loc):
        restart = 0
        while True:
            try:
                # словарь где ключ название локации, а значение url
                dict_locations = {}
                # запуск поисковика
                self.foxi_user()
                # переход на сайт
                self.driver.get("https://yandex.ru/maps")
                # проверка на проверку бота
                check_bot = self.click_bot()
                if check_bot:
                    continue
                time.sleep(5)
                # поиск поисковой строки
                element = self.driver.find_element(By.TAG_NAME, "input")
                # ввод запроса
                element.send_keys(f'{region_city_loc}', Keys.ENTER)
                time.sleep(2)
                # проверяем что получили - нет элементов или есть один элемент или список элементов
                self.soup = self.driver.page_source
                self.soup = BeautifulSoup(self.soup, 'html.parser')
                none_location = self.get_data(tag='div', class_='nothing-found-view__header')
                alone_location = self.get_data(tag='a', class_='card-title-view__title-link')
                mass_locations = self.get_data(tag = 'a', class_= 'link-overlay', all_data= True)
                # проверяем на отсутствие такой локации
                if none_location:
                    print(f'таких локаций в {region_city_loc} не найдено')
                    if restart == 1:
                        self.driver.close()
                        self.driver.quit()
                        return False 
                    time.sleep(10)
                    restart += 1
                    self.driver.close()
                    self.driver.quit()
                    continue

                elif alone_location:
                    dict_locations[f'{alone_location.text}'] = 'https://yandex.ru'+ alone_location.get('href')
                    self.driver.close()
                    self.driver.quit()

                elif mass_locations:
                    self.soup = self.reviews_scrol(class_name = 'search-business-snippet-view', click=True)
                    self.soup = BeautifulSoup(self.soup, 'html.parser')
                    locations = self.get_data(tag = 'a', class_= 'link-overlay', all_data= True)
                    for i in locations:
                        dict_locations[f'{i.get('aria-label')}'] = 'https://yandex.ru'+ i.get('href')
                
                else:
                    print('хз')
                    self.driver.close()
                    self.driver.quit()
                    continue
                
                return dict_locations
                
            except Exception as e:
                print(f'Ошибка в get_locations, {e}')
                continue
            

    # Берёт с вкладки обзор основную информацию и запускает полный сбор если True в full_get_info
    def get_loc_type_td (self, url, sql_city, full_get_info = False):
        while True:
            try:
                
                id_yandex = int([id for id in url.split('/') if id.isdigit()][0])
                self.soup = self.get_JS_page_content(url, click=[True, 'div.action-button-view._type_share'], close_=True)
            # проверяем местоположение локации по названию города
                html_city = self.get_data(tag='a', class_='breadcrumbs-view__breadcrumb _outline', all_data=True)
                city = html_city[1].get('title')
                if len(sql_city) <= 5:
                    index = 3
                else:
                    index = 5
                if city == sql_city or city[:index] == sql_city[:index]:
                    pass
                else:
                    # elements = {'role':'link', 'class':'breadcrumbs-view__breadcrumb _outline', 'tabindex':'0'}
                    elements = {'class':'business-contacts-view__address-link'}
                    html_city = self.soup.find('a', elements).text
                    city =  html_city.split(' ')
                    if sql_city in html_city or sql_city[:5] in html_city:
                        pass
                    else:
                        print(f'У локации другой город - {city}, а нас нужен {sql_city}')
                        return True   
            # количество оценок
                element_like = self.get_data(tag='div', class_="business-header-rating-view__text _clickable")
                if element_like:
                    count_like = element_like.text
                    count_like = count_like.split(' ')[0]
                else:
                    count_like = '0'
            # средняя оценка
                like = self.get_data(tag='span', class_="business-rating-badge-view__rating-text").text
            # раздел особенности    
                features_http = self.get_data(tag='div', class_='business-features-view _wide _view_overview _orgpage')
                features = {}
                mass = [i.text for i in features_http.find_all('div', {'class':'business-features-view__bool-text'})]
                features['featurs_text'] = mass 
                mass = {i.find('span', {'class':'business-features-view__valued-title'}).text: 
                        i.find('span', {'class':'business-features-view__valued-value'}).text 
                        for i in features_http.find_all('div', {'class':'business-features-view__valued'})}
                features['featurs_key'] = mass
            # все типы локации
                types = self.get_data(tag = 'div',class_='orgpage-categories-info-view')
                types = [i.text for i in types.find_all('span', {'class':'button__text'})]
            # координаты
                self.soup = self.soup.find('div',
                                        {'class':'card-feature-view _view_normal _size_large _interactive _no-side-padding card-share-view__coordinates'})
                coordinates = self.get_data(tag = 'div',class_='card-share-view__text').text.split(', ')
                self.loc_info = {'count_like':count_like, 'like': like, 'types':types, 'coordinates': [coordinates[1], coordinates[0]], 'id_yandex':id_yandex, 'features':features}
                if full_get_info:
                    self.get_location_rewiews_and_photos(loc_url=url)
                break

            except Exception as e:
                print(f'ошибка в get_loc_type_td, {e}')
                time.sleep(random.randrange(5,20))
                continue

    # ОТЗЫВЫ
    # делает словарь, где ключ это номер отзыва, а значение словарь, где ключ это либо like, либо text 
    def get_location_rewiews(self, url): 
        while True:
            try:
                self.soup = self.reviews_scrol(url_map = url+'reviews/', class_name='business-reviews-card-view__space', 
                                               click = True, check_none=[True, 'h2', 'tab-empty-view__title'])
                if self.soup != True:
                    self.soup = BeautifulSoup(self.soup, 'html.parser')
                    rewiews = self.get_data(tag = 'div', class_='business-reviews-card-view__review', all_data=True)
                    rewiews_filter = {}
                    i = 0
                    for rewiew in rewiews:
                        self.soup = rewiew
                        i +=1
                        rewiews_filter[i] = {}
                        like = len(self.get_data(tag = 'span', class_='inline-image _loaded icon business-rating-badge-view__star _full', all_data=True))
                        rewiews_filter[i]['like'] = like
                        rewiews_filter[i]['text'] = self.get_data(tag = 'span', class_='business-review-view__body-text').get_text()
                        rewiews_filter[i]['data'] = self.get_data(tag = 'meta', itemprop='datePublished').get('content').split('T')[0]
                    self.loc_rewiews = rewiews_filter 
                    break
                else:
                    rewiews_filter = {}
                    rewiews_filter[1] = {}
                    rewiews_filter[1]['like'] = 0
                    rewiews_filter[1]['text'] = 'None'
                    rewiews_filter[1]['data'] = 'None'
                    self.loc_rewiews = rewiews_filter
                    break
            except:
                print('ошибка в get_location_rewiews')
                time.sleep(random.randrange(5,20))
                self.driver.close()
                self.driver.quit()
                continue

    

    # ФОТО
    # Делаейт словарь где ключ номер фото, а значение его url
    def get_location_photos(self, url):
        while True:
            try:
                self.soup = self.reviews_scrol(url_map=url + 'gallery/', class_name='media-wrapper__media',
                                click=True, check_none=[True, 'h2', 'tab-empty-view__title'])
                if self.soup != True:
                    self.soup = BeautifulSoup(self.soup, 'html.parser')
                    photos_html = self.get_data(tag = 'img',class_='media-wrapper__media', all_data = True)
                    i = 0
                    dict_photos = {}
                    for photo in photos_html:
                        i += 1
                        dict_photos[i] = photo.get('src')
                    self.loc_photos = dict_photos
                    break
                else:
                    dict_photos = {}
                    dict_photos[1] = 'None'
                    self.loc_photos = dict_photos
                    break
            except:
                print('ошибка в get_location_photos')
                time.sleep(random.randrange(60,120))
                self.driver.close()
                self.driver.quit()
                continue

    # скролит сайты для прогрузки элементов, может сам заходить на страницы если передать url_map 
    # и может кликать на выбраный элемент чтобы явно показать за чем закреплен скролинг
    def reviews_scrol(self, class_name, check_none=[False, '', ''], url_map = '', click = False):
        # slov = {'class':By.CLASS_NAME, 'id':By.ID}
        while True:
            if url_map:
                # для случайных User-Agent  
                self.foxi_user()
                # Переход по ссылке
                self.driver.get(f'{url_map}')
                time.sleep(10)
                check_bot = self.click_bot()
                if check_bot:
                    self.driver.close()
                    self.driver.quit()
                    continue
                # если необходимо проверяет на отсутствие какого либо ряда элементов (нету отзывов например)
                # необходимо передать True и что искать и если есть то возвращает истина (т.е. да нету что парсить)
                if check_none[0]:
                    self.soup = self.driver.page_source
                    self.soup = BeautifulSoup(self.soup, 'html.parser')
                    none = self.get_data(tag = check_none[1], class_=check_none[2])
                    if none:
                        self.driver.close()
                        self.driver.quit()
                        return True
            # Использование WebDriverWait для ожидания появления элемента с отзывами
            try:
                first_review = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, f'{class_name}'))
                )

            except Exception as e:
                # print(f"Error locating first: {e}")
                print('Не найден нужный элемент, пробую повторно')
                self.driver.close()
                self.driver.quit()
                continue

            try:
                # Перемещение указателя мыши на первый отзыв и клик
                if click:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(first_review).click().perform()

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
                        else:
                            not_good = 0 
                            last_height = new_height
                    except Exception as e:
                        print(e)
                        not_good += 1
                time.sleep(5)
                page_source = self.driver.page_source
                return page_source
            
            finally:
                self.driver.close()
                self.driver.quit()


    def scroll_to_bottom(self, section):
        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", section)


        # работала когда была халява ключей
    # собирает все локации в конкретном городе
    # def get_locations_api(self, name_city, type_loc):
    #     all_api_key = ['547d8501-74fd-46af-930a-9ea2fff048bf']
    #     current_key = 0
    #     lang = 'ru_RU'
    #     client = Search(all_api_key[current_key])
    #     address = f"{name_city} {type_loc}"
    #     all_loc = 1000
    #     get_loc = 0
    #     try:
    #         while all_loc > get_loc:
    #             response = client.search(text = address,lang=lang,rspn=True,results=50, skip = get_loc)
    #             if 'error' in response and len(all_api_key) > current_key:
    #                 current_key += 1
    #                 print(f'\n\n {response}')
    #                 client = Search(all_api_key[current_key])
    #                 continue

    #             elif 'error' in response and len(all_api_key) == current_key:
    #                 print('Лимит парсинга')
    #                 break
                
    #             # общая информация (кол объектов надо)
    #             properties = response['properties']
    #             all_loc = properties['ResponseMetaData']['SearchResponse']['found']
    #             get_loc += 50
            
    #             # найденые объекты
    #             features = response['features']
    #             return features

    #     except Exception as e:
    #         print("Ошибка:", e)

    # работала когда была халява ключей
    # Получает  полный url До локации, название и количество отзывов
    # def get_location_rewiews_summary(self, _url):
    #     url = f'https://yandex.ru/maps-reviews-widget/{_url}?comments'
    #     url_map = self.get_data(url, tag ='a',
    #                              class_ = 'badge__more-reviews-link' )
    #     url_map = url_map.get('href')
    #     number = self.get_data(tag = 'p', class_='mini-badge__stars-count')
    #     number = float(number.text.replace(',','.'))
    #     count_ = self.get_data(tag = 'a', class_ = 'mini-badge__rating')
    #     count_ = count_.text.split(' ')
    #     count_ = {'отзывы': int(count_[0]), 'оценки':int(count_[3])}
    #     self.soup = None
    #     time.sleep(1)
    #     return {'url_map': url_map, 'number': number, 'count': count_}
                

    

    
    
