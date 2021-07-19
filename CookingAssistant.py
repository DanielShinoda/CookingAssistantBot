import pandas as pd
import telebot
from random import randrange
from collections import defaultdict
from datetime import datetime, date, time

df = pd.read_csv('database.csv')


class SimilarMealFinder:

    def __init__(self, data: pd.DataFrame):
        self.data = data

    @staticmethod
    def from_csv_path(csv_path: str):
        return SimilarMealFinder(
            pd.read_csv(csv_path),
        )

    @staticmethod
    def from_excel_path(excel_path: str):
        return SimilarMealFinder(
            pd.read_excel(excel_path),
        )

    def __call__(self, meal_query: str) -> str:
        # Будем искать введённый ингредиент в составе блюд
        indexes_match_queries = self.data.apply(
            lambda row: meal_query in row['meal_ingredients'].lower(),
            axis=1,
        )
        if sum(indexes_match_queries) == 0:
            return []
        # Индексы совпадающих блюд
        data_sample = self.data[indexes_match_queries]
        # Подходящие блюда
        most_likely_cosine = data_sample.meal_cousine_names.mode().iloc[0]
        # Pick an arbitrary meal that matches the query.
        random_query_response = data_sample[
            data_sample['meal_cousine_names'] == most_likely_cosine
            ]
        return random_query_response


class ProductInfo:
    def __init__(self, name, date):
        self.name = name
        self.date_of_expire = date


similar_meal_finder = SimilarMealFinder.from_csv_path('database.csv')


# Токен бота
bot = telebot.TeleBot('__token__')

# В качестве структуры для холодильника возьмём defaultdict из библиотеки collections
# Вообще, изучаю способы подключения SQL базы данных
rg = defaultdict(list)


# Главное меню
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Доброго времени суток мастер-повар")
    keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    key_recipes = telebot.types.InlineKeyboardButton(text='Рецепты')
    key_refreg = telebot.types.InlineKeyboardButton(text='Управление холодильником')
    keyboard.add(key_recipes, key_refreg)
    msg = bot.send_message(message.chat.id, text="Время готовки или чистка холодильника?", reply_markup=keyboard)
    bot.register_next_step_handler(msg, step1)


# Функция для перехода (скорее всего бесполезная)
def step1(message):
    if message.text == 'Управление холодильником':
        refreg(message)
    elif message.text == 'Рецепты':
        bot.send_message(message.chat.id, 'Введите ингредиент')
        bot.register_next_step_handler(message, get_recipe)
    else:
        bot.register_next_step_handler(message, start)


# Меню холодильника
def refreg(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton(text='Показать содержимое холодильника'),
                 telebot.types.KeyboardButton(text='Добавить продукт'),
                 telebot.types.KeyboardButton(text='Удалить продукт'),
                 telebot.types.KeyboardButton(text='Проверить срок годности продуктов'),
                 telebot.types.KeyboardButton(text='Отмена'))
    msg = bot.send_message(message.chat.id, text="Что вы хотите сделать с продуктами?", reply_markup=keyboard)
    bot.register_next_step_handler(msg, switch)


# Функция для перехода по действиям в холодильнике
def switch(message):
    try:
        if message.text == 'Добавить продукт':
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add(telebot.types.KeyboardButton('Отмена'))
            msg = bot.send_message(message.chat.id, f'Введите название продукта',
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, add_pr)

        elif message.text == 'Проверить срок годности продуктов':
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            bt1 = telebot.types.KeyboardButton('Отмена')
            markup.add(bt1)
            check_date_of_expire(message)

        elif message.text == 'Удалить продукт':
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            bt1 = telebot.types.KeyboardButton('Отмена')
            markup.add(bt1)
            msg = bot.send_message(message.chat.id, f'Введите название продукта',
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, del_pr)

        elif message.text == 'Показать содержимое холодильника':
            if len(rg[message.chat.id]) == 0:
                bot.send_message(message.chat.id, 'Кажется, что Вам пора в магазин, так как холодильник пуст ):')
                start(message)
            else:
                temp = ""
                for i in range(len(rg[message.chat.id])):
                    temp = temp + '\n' + rg[message.chat.id][i].name + '\t:\t продукт годен до '\
                           + rg[message.chat.id][i].date_of_expire
                bot.send_message(message.chat.id, temp)
                refreg(message)
        else:
            markup = telebot.types.ReplyKeyboardRemove(selective=False)
            bot.send_message(message.chat.id, 'Отмена!', reply_markup=markup)
            start(message)

    except Exception as e:
        print(str(e))


# Добавление продукта в холодильник
def add_pr(message):
    try:
        cur = ProductInfo(message.text.lower(), '')
        rg[message.chat.id].append(cur)
        markup = telebot.types.ReplyKeyboardRemove(selective=False)
        if message.text != 'Отмена':
            bot.send_message(message.chat.id, f'Положил {message.text} в холодильник', reply_markup=markup)
            bot.send_message(message.chat.id, f'Введите срок годности продукта в формате yy-mm-dd', reply_markup=markup)
            bot.register_next_step_handler(message, add_date)
        else:
            bot.send_message(message.chat.id, 'Отмена!', reply_markup=markup)
            refreg(message)
    except Exception as e:
        print(str(e))


# Добавление даты, в который момент продукт будет просрочен
def add_date(message):
    try:
        # Добавляем окончание срока годности продукта
        rg[message.chat.id][-1].date_of_expire = message.text
        markup = telebot.types.ReplyKeyboardRemove(selective=False)
        if message.text != 'Отмена':
            bot.send_message(message.chat.id, f'Запомнил срок годности продукта', reply_markup=markup)
            refreg(message)
        else:
            bot.send_message(message.chat.id, 'Отмена!', reply_markup=markup)
            refreg(message)
    except Exception as e:
        print(str(e))


# Проверка срока годности продукта
def check_date_of_expire(message):
    try:
        markup = telebot.types.ReplyKeyboardRemove(selective=False)
        if message.text != 'Отмена':
            _ = datetime.now()
            products = list()
            temp = str(_.year) + '-' + str(_.month) + '-' + str(_.day)
            for i in range(len(rg[message.chat.id])):
                if rg[message.chat.id][i].date_of_expire < temp:
                    products.append(rg[message.chat.id][i].name)
            bot.send_message(message.chat.id,
                             f'Истёк срок годности следующих продуктов:\n',
                             reply_markup=markup)
            if len(products) == 0:
                bot.send_message(message.chat.id,
                                 'С Вашими продуктами всё в порядке!',
                                 reply_markup=markup)
            else:
                for i in products:
                    bot.send_message(message.chat.id,
                                     f'{i}\n',
                                     reply_markup=markup)
            refreg(message)
        else:
            bot.send_message(message.chat.id, 'Отмена!', reply_markup=markup)
            refreg(message)
    except Exception as e:
        print(str(e))


# Удаление продукта из холодильника
def del_pr(message):
    try:
        if message.text != 'Отмена':
            flag = 0
            for i in rg[message.chat.id]:
                if i.name == message.text.lower():
                    flag = 1
                    rg[message.chat.id].remove(i)
            if flag:
                bot.send_message(message.chat.id, f'Выкинул {message.text} из холодильника')
                refreg(message)
            else:
                bot.send_message(message.chat.id, f'В вашем холодильнике нет следующего продукта: {message.text} ')
                refreg(message)
        else:
            bot.send_message(message.chat.id, 'Отмена!')
            refreg(message)
    except Exception as e:
        print(str(e))


# Вывод до 3 случайных рецептов, содержащих выбранный ингредиент
# Рецепты берутся на основе
# dataframe, собранного с сайта eda.ru при помощи
# Библиотеки BeautifulSoup
def get_recipe(message):
    row = similar_meal_finder(message.text.strip().lower())
    if len(row) == 0:
        bot.send_message(message.chat.id, 'Нет такого ингредиента')
        start(message)
    else:
        for i in range(1, min(4, row.shape[0])):
            cur = row.sample(i)
            bot.send_message(message.chat.id, cur['meal_names'])
            modified_ingredients = cur.at[cur[cur.meal_ingredients == cur['meal_ingredients']].index.to_list()[0],
                                          'meal_ingredients'].replace(',', '\n')[1:-1]
            bot.send_message(message.chat.id, ' ' + modified_ingredients.replace("'", ''))
            bot.send_message(message.chat.id, cur['meal_urls'])
        bot.send_message(message.chat.id, 'Приятного аппетита!')
        start(message)


bot.polling()


# В планах:
# Рекомендовать покупку часто добавляемых продуктов
# Рекомендовать рецепты по имеющимся продуктам в холодильнике
# Прикрутить холодильник к базам данных,
# чтобы данные о холодильнике пользователей
# не терялись после каждого отключения сервера
