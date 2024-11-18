import random
import time
import logging
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


from ymaps import Search

from app.data.parsing import Parse, ParseError

logger = logging.getLogger(__name__)


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