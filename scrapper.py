import urllib.request
from tqdm.notebook import tqdm
import six
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

cousine_code = 'italyanskaya-kuhnya'
page_num = 200  # Максимальное число обрабатываемых страниц
url = f'https://eda.ru/recepty/{cousine_code}?page={page_num}'

response = requests.get(url)

soup = BeautifulSoup(response.content, 'html.parser')

cousines_html_block = soup.find_all('div', 'select-suggest js-select-suggest')[1]

cousines = cousines_html_block.find_all('li')[2:] # Обрезаем любую и популярные кухни
cousine_names = [cousine.text.strip() for cousine in cousines]
cousine_codes = [cousine['data-select-suggest-value'] for cousine in cousines]
cousine_code_to_name = dict(zip(cousine_codes, cousine_names))

cousine_codes = list(set(cousine_codes) - {'all'})

meal_names = []  # название блюда
meal_tags = []  # тэги блюда
meal_urls = []  # ссылка на рецепт
meal_cousine_names = []  # название кухни
meal_images = []  # ссылка на изображение блюда
meal_ingredients = []  # ингредиенты блюда
MAX_NUM_PAGES = 200
GOOD_RESPONSE_STATUS = 200
for cousine_code in tqdm(cousine_codes):
    print(cousine_code)
    for page_num in range(1, MAX_NUM_PAGES):
        url = f'https://eda.ru/recepty/{cousine_code}?page={page_num}'
        response = requests.get(url, timeout=20)
        if response.status_code != GOOD_RESPONSE_STATUS:
            break
        soup = BeautifulSoup(response.content, 'html.parser')
        meal_soups = soup('div', 'horizontal-tile__content')
        # Чтобы быстро работало важно дописать это:
        if len(meal_soups) == 0:
            break

        image_links = [
            image.get('xlink:href')
            for image in soup('image')
        ]
        assert len(image_links) == len(meal_soups)

        meal_images += image_links
        for meal_soup in meal_soups:
            tags = [tag.text for tag in meal_soup('li')]  # Тэги блюда
            name = meal_soup.h3.text.strip().replace('\xa0', ' ')  # Название блюда
            url = f'https://eda.ru{meal_soup.h3.a["href"]}'  # Ссылка на блюдо
            ingredients = [ingr.text.strip() for ingr in
                           meal_soup('span', 'js-tooltip js-tooltip-ingredient')]  # Ингредиенты к блюду
            proportions = [prop.text.strip() for prop in meal_soup('span',
                                                                   'content-item__measure js-ingredient-measure-amount')
                           ]  # Количество ингредиентов
            ing = dict(zip(ingredients, proportions))  # Названия игредиентов и их количество
            meal_ingredients.append(ing)
            meal_tags.append(tags)
            meal_urls.append(url)
            meal_names.append(name)
            meal_cousine_names.append(
                cousine_code_to_name[cousine_code]
            )

# Датафрейм для бота: содержит колонки с информацией об имени,
# ингредиентах, тэгах, ссылке, названии кухни, ссылке на изображение блюда
df = pd.DataFrame(
    {
        'meal_names': meal_names,
        'meal_ingredients': meal_ingredients,
        'meal_tags': meal_tags,
        'meal_urls': meal_urls,
        'meal_cousine_names': meal_cousine_names,
        'meal_images': meal_images
    }
)
df.drop_duplicates(subset=['meal_urls'], inplace=True)

df.to_csv('database.csv', encoding='utf-8', index=False)
