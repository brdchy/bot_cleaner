import asyncio
import logging
import html
import re
import uuid
import csv
from datetime import datetime, timedelta
import os

from aiogram.filters.command import Command, CommandObject
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rapidfuzz import fuzz
from difflib import SequenceMatcher

from settings import BOT_TOKEN

# --- Настройки ---
ADMINS_FILE = 'txts/admins_list.txt'
AD_PATTERNS_FILE = 'txts/ad_patterns.csv'
BAD_WORDS_FILE = 'txts/bad_words.txt'
WHITE_LIST_FILE = 'txts/white_list.txt'
DELETE_LIST_FILE = 'txts/delete_list.txt'
ADMIN_ACTIONS_FILE = 'txts/admin_actions.csv'
MATCH_THRESHOLD = 1
MESSAGE_TIMEOUT = 60  # seconds

# --- Глобальные переменные ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)

admin_messages = {}
temp_patterns = {}
user_data = {}
message_texts = {}

is_delete_ad = False
is_delete_bw = False
adminsId = []
bad_words = []
white_list = []
delete_list = []
ad_patterns = []


# --- Загрузка данных ---
def load_data():
    global adminsId, bad_words, white_list, delete_list, ad_patterns

    try:
        with open(ADMINS_FILE, 'r') as f:
            adminsId = [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        print(f"Файл {ADMINS_FILE} не найден. Создайте файл и добавьте ID админов.")
        adminsId = []
    except Exception as e:
        print(f"Ошибка при загрузке {ADMINS_FILE}: {e}")
        adminsId = []

    try:
        with open(BAD_WORDS_FILE, "r", encoding='utf-8') as f:
            bad_words = [word.replace("\n", "").strip() for word in f.readlines()]
    except FileNotFoundError:
        print(f"Файл {BAD_WORDS_FILE} не найден. Создайте файл и добавьте нежелательные слова.")
        bad_words = []
    except Exception as e:
        print(f"Ошибка при загрузке {BAD_WORDS_FILE}: {e}")
        bad_words = []

    try:
        with open(WHITE_LIST_FILE, "r", encoding='utf-8') as f:
            white_list = [word.replace("\n", "").strip() for word in f.readlines()]
    except FileNotFoundError:
        print(f"Файл {WHITE_LIST_FILE} не найден. Создайте файл и добавьте разрешенные слова.")
        white_list = []
    except Exception as e:
        print(f"Ошибка при загрузке {WHITE_LIST_FILE}: {e}")
        white_list = []

    try:
        with open(DELETE_LIST_FILE, "r", encoding='utf-8') as f:
            delete_list = [word.strip() for word in f.readlines() if word.strip()]
    except FileNotFoundError:
        print(f"Файл {DELETE_LIST_FILE} не найден. Создайте файл и добавьте слова для удаления.")
        delete_list = []
    except Exception as e:
        print(f"Ошибка при загрузке {DELETE_LIST_FILE}: {e}")
        delete_list = []

    try:
        with open(AD_PATTERNS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            ad_patterns = [re.compile(r'' + row[0], re.IGNORECASE) for row in reader if row]
    except FileNotFoundError:
        print(f"Файл {AD_PATTERNS_FILE} не найден. Создайте файл и добавьте паттерны рекламы.")
        ad_patterns = []
    except Exception as e:
        print(f"Ошибка при загрузке {AD_PATTERNS_FILE}: {e}")
        ad_patterns = []


# --- Утилиты ---
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


def is_bad_word(source: list, dist: str):
    if dist in white_list:
        return False
    for word in source:
        if word == dist or fuzz.ratio(dist, word) > 85:
            return True
    return False


def count_ad_matches(text):
    return sum(1 for pattern in ad_patterns if pattern.search(text))

# --- Обработчики команд ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Начало'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='mode', description='Изменить режим работы'),
        BotCommand(command='whitelist', description='Добавить слово в белый список'),
        BotCommand(command='blacklist', description='Добавить слово в черный список'),
        BotCommand(command='add_pattern', description='Добавить текст в список паттернов рекламы'),
        BotCommand(command='remove_pattern', description='Удалить паттерн рекламы из списка'),
        BotCommand(command='watch_patterns', description='Посмотреть список паттернов'),
        BotCommand(command='change_threshold', description='Изменить порог совпадений'),
        BotCommand(command='add_admin', description='Добавить пользователя в список админов'),
        BotCommand(command='remove_admin', description='Убрать админа из списка админов'),
        BotCommand(command='mute', description='Замутить пользователя'),
        BotCommand(command='unmute', description='Размутить пользователя'),
        BotCommand(command='ban', description='Забанить пользователя'),
        BotCommand(command='get_id', description='узнать user_id пользователя'),
        BotCommand(command='my_id', description='узнать свой user_id'),
        BotCommand(command='admin_actions', description='Просмотр последних действий админов'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def start_bot(bot: Bot):
    await set_commands(bot)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    await message.answer(text="Привет. Для информации о функционале бота напиши:\n/help")


@dp.message(Command("help"))
async def help(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    text = ("Команды:\n"
            "/mode - изменить режим работы\n"
            "/blacklist <слово> - добавить слово в черный список\n"
            "/whitelist <слово> - добавить слово в белый список\n"
            "/add_pattern <текст> - добавить текст рекламы в список паттернов\n"
            "/remove_pattern - удалить паттерн рекламы из списка\n"
            "/watch_patterns - посмотреть список паттернов\n"
            "/change_threshold - изменить порог совпадений для рекламы\n"
            "/my_id - узнать свой user_id\n"
            "/admin_actions - просмотр последних действий админов\n\n"

            "Команды, которы можно использовать ответом на сообщение:\n"
            "/add_admin <user_id> - добавить админа\n"
            "/remove_admin <user_id> - убрать админа\n"
            "/mute - замутить пользователя\n"
            "/unmute - размутить пользователя\n"
            "/ban <user_id> - забанить пользователя\n"
            "/get_id - узнать user_id пользователя\n")
    await message.answer(text=text)


@dp.message(F.text, Command("admin_actions"))
async def view_admin_actions(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    admin_actions = load_admin_actions()

    # Выберем последние 30 действий
    last_actions = admin_actions[-30:]

    response = "Последние действия админов:\n\n"
    for action in last_actions:
        response += f"{action['timestamp']} - {action['username']} - {action['action']}: {action['details']}\n"

    await message.reply(response)


@dp.message(Command("mode"))
async def change(message: types.Message):
    if message.from_user.id in adminsId:
        await send_control_message(message, message.from_user.id)


@dp.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "без имени пользователя"
    else:
        args = message.text.split()[1:]
        if not args:
            await message.reply("Использование: /add_admin <user_id> или ответьте на сообщение пользователя командой /add_admin")
            return

        try:
            user_id = int(args[0])
            user = await message.bot.get_chat(user_id)
            username = user.username or "без имени пользователя"
        except ValueError:
            await message.reply("Некорректный ID пользователя. Используйте число или ответьте на сообщение пользователя.")
            return
        except Exception:
            await message.reply(f"Не удалось найти пользователя с ID {args[0]}.")
            return

    if user_id not in adminsId:
        adminsId.append(user_id)
        with open(ADMINS_FILE, "a", encoding='utf-8') as f:
            f.write(f"\n{user_id}")
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) добавлен в список админов.")
        await log_admin_action(message.from_user.id, "add_admin", f"Added admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")


@dp.message(F.text, Command("remove_admin"))
async def remove_from_adminlist(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "без имени пользователя"
    else:
        args = message.text.split()[1:]
        if not args:
            await message.reply("Использование: /remove_admin <user_id> или ответьте на сообщение пользователя командой /remove_admin")
            return

        try:
            user_id = int(args[0])
            user = await message.bot.get_chat(user_id)
            username = user.username or "без имени пользователя"
        except ValueError:
            await message.reply("Некорректный ID пользователя. Используйте число или ответьте на сообщение пользователя.")
            return
        except Exception:
            await message.reply(f"Не удалось найти пользователя с ID {args[0]}.")
            return

    if user_id in adminsId:
        adminsId.remove(user_id)
        with open(ADMINS_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(map(str, adminsId)))
        await message.reply(f"Админ @{html.escape(username)} (ID: {user_id}) удален из списка админов.")
        await log_admin_action(message.from_user.id, "remove_admin", f"Removed admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) не является админом.")


@dp.message(F.text, Command("my_id"))
async def my_id(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    await message.answer(f"Ваш ID:\n```{message.from_user.id}```", parse_mode="MarkdownV2")


@dp.message(F.text, Command("get_id"))
async def get_user_id(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await message.reply(f"ID пользователя:\n```{user_id}```", parse_mode="MarkdownV2")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("mute"))
async def mute(message: types.Message, command: CommandObject):
    if message.from_user.id not in adminsId:
        return
    duration = 300
    if command.args:
        try:
            duration = int(command.args)
        except ValueError:
            await message.reply("Неверный формат. Используйте: /mute <количество_секунд>")
            return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user = await message.bot.get_chat(user_id)
        await bot.restrict_chat_member(message.chat.id, user_id, types.ChatPermissions(can_send_messages=False))
        await message.answer(f"Пользователь @{user.username} замучен на {duration} секунд.")
        await log_admin_action(message.from_user.id, "mute", f"Muted user: {user_id} (@{user.username}) for {duration} seconds")
        asyncio.create_task(unmute_user(message.chat.id, user_id, duration))
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("unmute"))
async def unmute(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user = await message.bot.get_chat(user_id)
        await bot.restrict_chat_member(
            message.chat.id,
            user_id,
            types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await message.answer(f"Пользователь @{user.username} размучен.")
        await log_admin_action(message.from_user.id, "unmute", f"Unmuted user: {user_id} (@{user.username})")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


async def unmute_user(chat_id: int, user_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        ))
        print(f"Пользователь {user_id} был автоматически размучен в чате {chat_id}")
    except Exception as e:
        print(f"Не удалось размутить пользователя {user_id} в чате {chat_id}: {str(e)}")


@dp.message(F.text, Command("ban"))
async def ban(message: types.Message, command: CommandObject):
    if message.from_user.id not in adminsId:
        return
    reason = "не указана"
    if command.args:
        reason = command.args
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user = await message.bot.get_chat(user_id)
        try:
            await bot.ban_chat_member(message.chat.id, user_id)
            await message.answer(f"Пользователь @{user.username} забанен.\nПричина: {reason}")
            log_admin_action(message.from_user.id, "ban", f"Banned user: {user_id} Reason: {reason}")
        except Exception as e:
            await message.reply(f"Не удалось забанить пользователя: {str(e)}")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("blacklist"))
async def add_to_blacklist(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите плохое слово после команды /blacklist.")
        return
    word = message_text[1]
    if word:
        if word in bad_words:
            await message.reply(f"Слово '{word}' уже есть в черном списке.")
        else:
            bad_words.append(word)
            with open(BAD_WORDS_FILE, "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в черный список.")
            await log_admin_action(message.from_user.id, "blacklist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в черный список.")


@dp.message(F.text, Command("whitelist"))
async def add_to_admin(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите слово после команды /whitelist.")
        return
    word = message_text[1]

    if word:
        if word in white_list:
            await message.reply(f"Слово '{word}' уже есть в белом списке.")
        else:
            white_list.append(word)
            with open(WHITE_LIST_FILE, "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в белый список.")
            await log_admin_action(message.from_user.id, "whitelist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в белый список.")


@dp.message(Command("watch_patterns"))
async def watch_patterns(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    with open(AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        patterns = [row[0] for row in reader if row and row[0].strip()]

    if not patterns:
        await message.reply("Список паттернов пуст.")
        return

    readable_patterns = [f"{i + 1}. {regex_to_readable(pattern)}" for i, pattern in enumerate(patterns)]

    chunk_size = 100
    pattern_chunks = [readable_patterns[i:i + chunk_size] for i in range(0, len(readable_patterns), chunk_size)]

    for chunk in pattern_chunks:
        patterns_text = "\n".join(chunk)
        await message.reply(f"Текущие паттерны:\n\n{patterns_text}")


@dp.message(F.text, Command("add_pattern"))
async def add_pattern(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    pattern_text = message.text.split(maxsplit=1)
    if len(pattern_text) < 2:
        await message.reply("Пожалуйста, укажите текст паттерна рекламы после команды /add_pattern.")
        return

    new_pattern = " ".join(pattern_text[1].strip().split())
    new_pattern = extract_regular_chars(new_pattern)
    regex_pattern = string_to_regex(new_pattern)

    with open(AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        existing_patterns = [row[0] for row in reader if row]

    if regex_pattern in existing_patterns:
        await message.reply(f"Паттерн '{new_pattern}' уже существует в базе.")
        return

    for existing_pattern in existing_patterns:
        if regex_pattern in existing_pattern or existing_pattern in regex_pattern:
            pattern_id = str(uuid.uuid4())[:8]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да, добавить", callback_data=f"add:{pattern_id}")],
                [InlineKeyboardButton(text="Нет, отменить", callback_data=f"cancel:{pattern_id}")]
            ])
            await message.reply("В базе существует похожий паттерн. Вы уверены, что хотите добавить новый паттерн?",
                                reply_markup=keyboard)
            temp_patterns[pattern_id] = (regex_pattern, new_pattern, message)
            return

    await add_pattern_to_database(message, new_pattern, regex_pattern)
    await log_admin_action(message.from_user.id, "add_pattern", f"Added pattern: '{new_pattern}'")


@dp.message(Command("remove_pattern"))
async def remove_pattern(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    with open(AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        existing_patterns = [row[0] for row in reader if row and row[0].strip()]

    if not existing_patterns:
        await message.reply("Список паттернов пуст.")
        return

    patterns_list = "\n".join([f"{i + 1}. {regex_to_readable(pattern)}" for i, pattern in enumerate(existing_patterns)])
    sent_message = await message.reply(f"Список паттернов:\n\n{patterns_list}\n\nВведите номер паттерна, который вы хотите удалить:")

    user_data[message.from_user.id] = {
        'existing_patterns': existing_patterns,
        'waiting_for_pattern_number': True,
        'timer': asyncio.create_task(clear_user_data(message.from_user.id, MESSAGE_TIMEOUT, sent_message)),
        'sent_message': sent_message
    }


@dp.message(F.text.regexp(r'^\d+$'))
async def process_pattern_number(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get('waiting_for_pattern_number'):
        return

    existing_patterns = user_data[user_id]['existing_patterns']
    pattern_number = int(message.text) - 1

    if 0 <= pattern_number < len(existing_patterns):
        user_data[user_id]['timer'].cancel()

        pattern_to_delete = existing_patterns[pattern_number]
        await delete_pattern_from_database(message, pattern_to_delete)
        await log_admin_action(user_id, "remove_pattern",
                               f"Removed pattern: '{regex_to_readable(pattern_to_delete)}'")

        try:
            await user_data[user_id]['sent_message'].delete()
        except:
            pass  # Игнорируем ошибки при удалении сообщения

        del user_data[user_id]
    else:
        await message.reply("Неверный номер паттерна. Пожалуйста, введите корректный номер паттерна:")


@dp.callback_query(lambda c: c.data.startswith(('add:', 'cancel:')))
async def process_pattern_callback(callback_query: types.CallbackQuery):
    action, pattern_id = callback_query.data.split(':', 1)

    if pattern_id not in temp_patterns:
        await callback_query.answer("Ошибка: паттерн не найден.")
        await callback_query.message.delete()
        return

    regex_pattern, new_pattern, original_message = temp_patterns[pattern_id]

    if action == 'add':
        await add_pattern_to_database(original_message, new_pattern, regex_pattern)
        await log_admin_action(callback_query.from_user.id, "add_pattern", f"Added pattern: '{new_pattern}'")
    else:  # cancel
        await log_admin_action(callback_query.from_user.id, "add_pattern",
                               f"Cancelled adding pattern: '{new_pattern}'")
        await original_message.reply("Добавление паттерна отменено.")

    del temp_patterns[pattern_id]
    await callback_query.message.delete()
    await callback_query.answer()


async def add_pattern_to_database(message: types.Message, new_pattern: str, regex_pattern: str):
    compiled_pattern = re.compile(r'' + regex_pattern, re.IGNORECASE)
    ad_patterns.append(compiled_pattern)
    with open(AD_PATTERNS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([regex_pattern])
    await message.reply(f"Добавлен новый паттерн: {new_pattern}\nРегулярное выражение: {regex_pattern}")


async def delete_pattern_from_database(message: types.Message, pattern_to_delete: str):
    with open(AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        patterns = list(reader)

    patterns = [pattern for pattern in patterns if pattern[0] != pattern_to_delete]

    with open(AD_PATTERNS_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(patterns)

    global ad_patterns
    ad_patterns = [re.compile(r'' + pattern[0], re.IGNORECASE) for pattern in patterns]

    await message.reply(f"Паттерн '{regex_to_readable(pattern_to_delete)}' успешно удален.")


async def send_control_message(message: types.Message, adminId):
    global is_delete_bw
    global is_delete_ad

    buttons = InlineKeyboardBuilder()
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"Autodelete bad words: {'ON' if is_delete_bw else 'OFF'}",
                callback_data="toggle_delete_bw"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=f"Autodelete AD: {'ON' if is_delete_ad else 'OFF'}",
                callback_data="toggle_delete_ad"
            ),
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id=adminId, text="Режим работы", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("toggle_delete_"))
async def toggle_delete(callback: CallbackQuery):
    global is_delete_bw, is_delete_ad

    feature = callback.data.split("_")[-1]
    if feature == "bw":
        is_delete_bw = not is_delete_bw
        state = "activated" if is_delete_bw else "deactivated"
        await callback.answer(text=f'Auto delete bad words {state}')
        await log_admin_action(callback.from_user.id, "toggle_delete_bw", f"Auto delete bad words {state}")
    elif feature == "ad":
        is_delete_ad = not is_delete_ad
        state = "activated" if is_delete_ad else "deactivated"
        await callback.answer(text=f'Auto delete ad {state}')
        await log_admin_action(callback.from_user.id, "toggle_delete_ad", f"Auto delete ad {state}")

    # Обновляем сообщение с новым состоянием кнопок
    buttons = InlineKeyboardBuilder()
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"Autodelete bad words: {'ON' if is_delete_bw else 'OFF'}",
                callback_data="toggle_delete_bw"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=f"Autodelete AD: {'ON' if is_delete_ad else 'OFF'}",
                callback_data="toggle_delete_ad"
            ),
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Режим работы", reply_markup=keyboard)


async def clear_user_data(user_id: int, delay: int, sent_message: types.Message):
    await asyncio.sleep(delay)
    if user_id in user_data:
        try:
            await sent_message.delete()
        except:
            pass  # Игнорируем ошибки при удалении сообщения
        del user_data[user_id]


def get_threshold_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="-1", callback_data="decrease"),
            InlineKeyboardButton(text=f"{MATCH_THRESHOLD}", callback_data="current"),
            InlineKeyboardButton(text="+1", callback_data="increase")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


@dp.message(F.text, Command("change_threshold"))
async def threshold_command(message: types.Message):
    await message.answer("Текущее значение порога совпадений",
                         reply_markup=get_threshold_keyboard())


@dp.callback_query(lambda c: c.data in ['decrease', 'current', 'increase'])
async def process_callback0(callback_query: types.CallbackQuery):
    global MATCH_THRESHOLD

    try:
        old_threshold = MATCH_THRESHOLD
        if callback_query.data == 'decrease':
            MATCH_THRESHOLD = max(1, MATCH_THRESHOLD - 1)
        elif callback_query.data == 'increase':
            MATCH_THRESHOLD += 1

        await callback_query.answer()
        await callback_query.message.edit_text(
            text="Текущее значение порога совпадений",
            reply_markup=get_threshold_keyboard()
        )

        await log_admin_action(callback_query.from_user.id, "change_threshold",
                               f"Changed from {old_threshold} to {MATCH_THRESHOLD}")
    except:
        pass


# --- Обработчики сообщений ---
@dp.message()
async def work(message: types.Message):
    global is_delete_bw, is_delete_ad

    text_to_check = message.text or message.caption

    if text_to_check:
        text_to_check = " ".join(text_to_check.strip().split())
        if text_to_check in delete_list:
            try:
                await message.delete()
                return
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
                return

        if check_bw(text_to_check):
            if is_delete_bw:
                return await message.delete()
            else:
                return await notify_admins(message, reason="сообщение с плохим словом", message_text=text_to_check)

        if check_ad(text_to_check):
            if is_delete_ad:
                return await message.delete()
            else:
                return await notify_admins(message, reason="рекламное сообщение", message_text=text_to_check)


# --- Вспомогательные функции ---
def check_bw(message):
    if message is None:
        return False
    message_text = extract_regular_chars(message.lower())
    for word in message_text.split(' '):
        if is_bad_word(bad_words, replace_english_letters(word)):
            return True
    return False


def check_ad(message):
    message = extract_regular_chars(message.lower())
    # print(f'\n{message}\n')
    # print(f'Количество совпадений: {count_ad_matches(message)}')
    return count_ad_matches(message) >= MATCH_THRESHOLD


async def notify_admins(message: types.Message, reason: str, message_text):
    global admin_messages
    admin_message = (f"Обнаружено {reason}:\n\n"
                     f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
                     f"Текст: {message.text or message.caption}\n\n"
                     "Выберите действие:")

    admin_messages[message.message_id] = {}
    text_id = str(uuid.uuid4())[:8]
    message_texts[text_id] = message_text

    for admin in adminsId:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Удалить", callback_data=f"delete_{message.chat.id}_{message.message_id}_{text_id}")
        keyboard.button(text="Замутить", callback_data=f"mute_{message.chat.id}_{message.message_id}_{text_id}_{message.from_user.id}")
        keyboard.button(text="Забанить", callback_data=f"ban_{message.chat.id}_{message.message_id}_{text_id}_{message.from_user.id}")
        keyboard.button(text="Пропустить", callback_data=f"skip_{message.chat.id}_{message.message_id}_{text_id}")
        keyboard.adjust(2)

        sent_message = await bot.send_message(admin, admin_message, reply_markup=keyboard.as_markup())
        admin_messages[message.message_id][admin] = sent_message.message_id


@dp.callback_query(lambda c: c.data.startswith(('delete_', 'mute_', 'ban_', 'skip_')))
async def process_callback(callback_query: types.CallbackQuery):
    action, *params = callback_query.data.split('_')

    if len(params) < 3:
        await callback_query.answer("Неверный формат данных", show_alert=True)
        return

    chat_id = int(params[0])
    message_id = int(params[1])

    if action != 'skip':
        try:
            await bot.delete_message(chat_id, message_id)

            # Извлекаем text_id только если он есть в params
            text_id = params[2] if len(params) > 2 else None
            message_text = message_texts.get(text_id, "")

            await log_admin_action(callback_query.from_user.id, "delete message", f"Deleted message: '{message_text}'")
        except Exception as e:
            await callback_query.message.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)

    try:
        if action == 'delete':
            text_id = params[2] if len(params) > 2 else None
            message_text = message_texts.get(text_id, "")

            if message_text in bad_words or message_text in delete_list:
                pass
            else:
                with open("txts/delete_list.txt", "a", encoding='utf-8') as f:
                    f.write("\n" + message_text)
                delete_list.append(message_text)

            del message_texts[text_id]

            await callback_query.answer("Сообщение удалено.")
        elif action in ['mute', 'ban']:
            if len(params) < 4:
                await callback_query.answer("Недостаточно данных для выполнения действия", show_alert=True)
                return
            user_id = int(params[3])

            if action == 'mute':
                await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False))
                await callback_query.answer("Пользователь замучен на 300 секунд.")
                await log_admin_action(callback_query.from_user.id, "mute user", f"Muted user: {user_id}")

                asyncio.create_task(unmute_user(chat_id, user_id, 300))
            elif action == 'ban':
                await bot.ban_chat_member(chat_id, user_id)
                await callback_query.answer("Пользователь забанен.")
                await log_admin_action(callback_query.from_user.id, "ban user", f"Banned user: {user_id}")
        elif action == 'skip':
            text_id = params[2] if len(params) > 2 else None
            message_text = message_texts.get(text_id, "")

            await callback_query.answer("Сообщение пропущено.")
            await log_admin_action(callback_query.from_user.id, "skip message", f"Skipped message: '{message_text}'")

            del message_texts[text_id]
    except Exception as e:
        await callback_query.message.answer(f"Не удалось выполнить действие: {str(e)}", show_alert=True)

    if message_id in admin_messages:
        for admin, admin_message_id in admin_messages[message_id].items():
            try:
                await bot.delete_message(admin, admin_message_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")
        del admin_messages[message_id]


# --- Функции для работы с файлами и логами ---
def load_admin_actions():
    actions = []
    if os.path.isfile(ADMIN_ACTIONS_FILE):
        with open(ADMIN_ACTIONS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                actions.append(row)
    return actions


async def log_admin_action(user_id, action, details=''):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        user = await bot.get_chat_member(user_id, user_id)
        username = user.user.username or "No username"
    except:
        username = "Unknown"
    with open(ADMIN_ACTIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, user_id, f"@{username}", action, details])


async def delete_old_records():
    one_day_ago = datetime.now() - timedelta(days=1)
    try:
        with open(ADMIN_ACTIONS_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            all_rows = list(reader)
        header = all_rows[0]
        filtered_rows = [row for row in all_rows[1:]
                         if datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > one_day_ago]
        with open(ADMIN_ACTIONS_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(filtered_rows)
        print(f"Old records deleted at {datetime.now()}")
    except Exception as e:
        print(f"Error during deleting old records: {e}")


# --- Задачи ---
async def schedule_delete_old_records():
    while True:
        await delete_old_records()
        await asyncio.sleep(24 * 60 * 60)


# --- Запуск бота ---
async def main(message='Бот запущен'):
    load_data()
    for admin in adminsId:
        try:
            await bot.send_message(chat_id=admin, text=message)
            await send_control_message(message, admin)
        except:
            pass    

    dp.startup.register(start_bot)
    asyncio.create_task(schedule_delete_old_records())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
