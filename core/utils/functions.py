import re
from difflib import SequenceMatcher
import core.config as config

import csv
from datetime import datetime, timedelta
import os

from aiogram import F, Bot, Dispatcher, types


def extract_regular_chars(text):
    return re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)


def replace_english_letters(text):
    replacements = {
        'ch': 'ч',
        'a': 'а',
        'b': 'б',
        'c': 'с',
        'd': 'д',
        'e': 'е',
        'f': 'ф',
        'g': 'г',
        'h': 'х',
        'i': 'и',
        'j': 'ж',
        'k': 'к',
        'l': 'л',
        'm': 'м',
        'n': 'н',
        'o': 'о',
        'p': 'п',
        'q': 'к',
        'r': 'г',
        's': 'с',
        't': 'т',
        'u': 'и',
        'v': 'в',
        'w': 'ш',
        'x': 'х',
        'y': 'у',
        'z': 'з'
    }
    for eng, rus in replacements.items():
        text = text.replace(eng, rus)
    return text


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def string_to_regex(input_string):
    letter_to_regex = {
        'а': '[aа@]',
        'б': '[bб6]',
        'в': '[вbv]',
        'г': '[гr]',
        'д': '[дd]',
        'е': '[eе3]',
        'ё': '[ёeе]',
        'ж': '[жg]',
        'з': '[зz3э]',
        'и': '[иeеu]',
        'й': '[йuи]',
        'к': '[кk]',
        'л': '[лl]',
        'м': '[мm]',
        'н': '[н]',
        'о': '[оo0]',
        'п': '[пnh]',
        'р': '[pр]',
        'с': '[cс]',
        'т': '[тt]',
        'у': '[уy]',
        'ф': '[ф]',
        'х': '[xх]',
        'ц': '[ц]',
        'ч': '[ч4]',
        'ш': '[шwщ]',
        'щ': '[шwщ]',
        'ъ': '[ъ]',
        'ы': '[ы]',
        'ь': '[ь]',
        'э': '[зz3э]',
        'ю': '[ю]',
        'я': '[я]',

        'a': '[aа@]',
        'b': '[bб6]',
        'c': '[cс]',
        'd': '[дd]',
        'e': '[eе3]',
        'g': '[жg]',
        'h': '[пnh]',
        'u': '[иeеu]',
        'o': '[оo0]',
        'w': '[шwщ]',
        'k': '[кk]',
        't': '[тt]',
        'm': '[мm]',
        'v': '[вbv]',
        'y': '[уy]',
        'r': '[гr]',
        'x': '[xх]',
        'n': '[н]',
        'p': '[pр]',
        '6': '[bб6]',
        '3': '[зz3э]',
        '0': '[оo0]',
        '4': '[ч4]'
    }
    return ''.join(letter_to_regex.get(char, re.escape(char)) if char != ' ' else r'\s*'
                   for char in input_string.lower())


def regex_to_readable(regex_pattern):
    readable_dict = {
        '[aа@]': 'а',
        '[bб6]': 'б',
        '[вbv]': 'в',
        '[гr]': 'г',
        '[дd]': 'д',
        '[eе3]': 'е',
        '[ёeе]': 'ё',
        '[жg]': 'ж',
        '[зz3э]': 'з',
        '[иeеu]': 'и',
        '[йuи]': 'й',
        '[кk]': 'к',
        '[лl]': 'л',
        '[мm]': 'м',
        '[пnh]': 'п',
        '[н]': 'н',
        '[оo0]': 'о',
        '[pр]': 'р',
        '[cс]': 'с',
        '[тt]': 'т',
        '[уy]': 'у',
        '[ф]': 'ф',
        '[xх]': 'х',
        '[ц]': 'ц',
        '[ч4]': 'ч',
        '[шwщ]': 'ш',
        '[ъ]': 'ъ',
        '[ы]': 'ы',
        '[ь]': 'ь',
        '[ю]': 'ю',
        '[я]': 'я', r'\s*': ' '
    }
    for regex, char in readable_dict.items():
        regex_pattern = regex_pattern.replace(regex, char)
    return regex_pattern


async def write_ad_file(text_to_check):
    unique_messages = set()

    unique_messages.add(text_to_check)

    # Открываем файл и считываем все строки
    with open(config.DELETED_AD_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if line:
                line = extract_regular_chars(line.lower())
                line = replace_english_letters(line)
                unique_messages.add(line)

    # Преобразуем список сообщений в множество для удаления дубликатов
    unique_messages_list = list(unique_messages)

    # Сохраняем уникальные сообщения в новый файл
    with open(config.DELETED_AD_FILE, "w", encoding="utf-8") as output_file:
        output_file.writelines(unique_messages_list)


def read_csv(file_path):
    result = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Пропускаем заголовок
        for row in reader:
            result.append(row)
    return result


def get_user_data(csv_file, user_id):
    csv_data = read_csv(csv_file)

    for row in csv_data:
        if int(row[0]) == user_id:
            return int(row[1]), int(row[2])
    return int(0), int(0)


def load_admin_actions():
    actions = []
    if os.path.isfile(config.ADMIN_ACTIONS_FILE):
        with open(config.ADMIN_ACTIONS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                actions.append(row)
    return actions


async def log_admin_action(bot: Bot, user_id, action, details=''):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        user = await bot.get_chat_member(user_id, user_id)
        username = user.user.username or "No username"
    except:
        username = "Unknown"
    with open(config.ADMIN_ACTIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, user_id, f"@{username}", action, details])


async def increment_violation_count(user_id, reason, message_text):
    count_deleted_bw, count_deleted_ad = get_user_data(config.BAN_CANDIDATES_FILE, user_id)

    if reason == "ad":
        with open(config.DELETED_AD_FILE, "a", newline='', encoding='utf-8') as f:
            f.write(message_text + "\n")
        count_deleted_ad += 1
    else:
        with open(config.DELETED_BW_FILE, "a", newline='', encoding='utf-8') as f:
            f.write(message_text+ "\n")
        count_deleted_bw += 1

    # Читаем все существующие данные
    all_data = []
    with open(config.BAN_CANDIDATES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)

        for row in reader:
            if row[1]:
                all_data.append(row)

    users_id = list(int(row[0]) for row in all_data)

    if user_id in users_id:
        # Обновляем данные для нужного пользователя
        updated_data = []
        for row in all_data:
            if int(row[0]) == int(user_id):
                # Увеличиваем счетчики и добавляем новую запись
                updated_data.append([int(user_id), int(count_deleted_bw), int(count_deleted_ad)])
            else:
                updated_data.append(row)

        # Записываем все обновленные данные обратно в файл
        with open(config.BAN_CANDIDATES_FILE, 'w', newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for row in updated_data:
                writer.writerow(row)
    else:
        with open(config.BAN_CANDIDATES_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([int(user_id), int(count_deleted_bw), int(count_deleted_ad)])
