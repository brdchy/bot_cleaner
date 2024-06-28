import asyncio
import logging
import html
import re
import uuid
import csv

from aiogram.filters.command import Command, CommandObject
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rapidfuzz import fuzz
from difflib import SequenceMatcher

from settings import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)

admin_messages = {}

adminsId = []
with open('txts/admins_list.txt', 'r') as file:
    adminsId = [int(line.strip()) for line in file if line.strip().isdigit()]
print(adminsId)

ad_patterns = []
with open('txts/ad_patterns.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    for row in reader:
        if row:
            pattern = row[0]
            ad_patterns.append(re.compile(r'' + pattern, re.IGNORECASE))

is_delete_ad = False
is_delete_bw = False


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Начало'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='mode', description='Изменить режим работы'),
        BotCommand(command='whitelist', description='Добавить слово в белый список'),
        BotCommand(command='blacklist', description='Добавить слово в черный список'),
        BotCommand(command='pattern', description='Добавить текст в список паттернов рекламы'),
        BotCommand(command='add_admin', description='Добавить админа'),
        BotCommand(command='remove_admin', description='Добавить убрать админа'),
        BotCommand(command='mute', description='Замутить пользователя'),
        BotCommand(command='unmute', description='Размутить пользователя'),
        BotCommand(command='ban', description='Забанить пользователя'),
        BotCommand(command='get_id', description='узнать user_id пользователя'),
        BotCommand(command='my_id', description='узнать свой user_id'),
        ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def start_bot(bot: Bot):
    await set_commands(bot)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    
    await message.answer(text="Привет. Если хочешь узнать функционал бота напиши:\n/help")


@dp.message(Command("help"))
async def help(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    
    text = "Команды:\n"
    text += "/mode - изменить режим работы, вам будет прислано сообщение с переключателями\n"
    text += "/blacklist <плохое слово> - добавить слово в черный список\n"
    text += "/whitelist <слово> - добавить слово в белый список\n"
    text += "/pattern <паттерн рекламы> - добавить текст в список паттернов рекламы\n"
    text += "/my_id - узнать свой user_id\n"

    text += "\nКоманды, которые можно использовать ответом на сообщение пользователя:\n"
    text += "/add_admin <user_id> - добавить пользователя в список админов\n"
    text += "/remove_admin <user_id> - убрать админа из списка админов\n"
    text += "/mute <user_id> - замутить пользователя\n"
    text += "/ban <user_id> - забанить пользователя\n"
    text += "/get_id - узнать user_id пользователя\n"
    
    await message.answer(text=text)


@dp.message(Command("mode"))
async def change(message: types.Message):
    if message.from_user.id in adminsId:
        await send_control_message(message, message.from_user.id)


@dp.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    # Проверяем, является ли сообщение ответом на другое сообщение
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "без имени пользователя"
    else:
        # Если сообщение не является ответом, пробуем получить ID из аргументов
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
        with open("txts/admins_list.txt", "a", encoding='utf-8') as f:
            f.write(f"\n{user_id}")
        await message.reply(f"Админ @{html.escape(username)} (ID: {user_id}) добавлен в админлист.")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")


@dp.message(F.text, Command("remove_admin"))
async def remove_from_adminlist(message: types.Message):
    if message.from_user.id not in adminsId:
        return

    # Проверяем, является ли сообщение ответом на другое сообщение
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "без имени пользователя"
    else:
        # Если сообщение не является ответом, пробуем получить ID из аргументов
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
        # Обновляем файл admins_list.txt
        with open("txts/admins_list.txt", "w", encoding='utf-8') as f:
            f.write("\n".join(map(str, adminsId)))
        await message.reply(f"Админ @{html.escape(username)} (ID: {user_id}) удален из админлиста.")
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

    duration = 300  # Значение по умолчанию, если не указано
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
        # Запускаем задачу для автоматического размучивания через 300 секунд
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
        
        # Снимаем ограничения с пользователя
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
            # Баним пользователя
            await bot.ban_chat_member(message.chat.id, user_id)
            
            # Отправляем сообщение о бане
            await message.answer(f"Пользователь @{user.username} забанен.\nПричина: {reason}")
        except Exception as e:
            await message.reply(f"Не удалось забанить пользователя: {str(e)}")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("blacklist"))
async def add_to_blacklist(message: types.Message):
    if message.from_user.id not in adminsId:
        return
        
    # Получаем слово после команды
    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите плохое слово после команды /blacklist.")
        return
    word = message_text[1]
    if word:
        if word in bad_words:
            await message.reply(f"Слово '{word}' уже есть в черном списке.")
            await asyncio.sleep(0.1)
        else:
            bad_words.append(word)
            # Добавляем слово в bad_words.txt
            with open("txts/bad_words.txt", "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в черный список.")
            await asyncio.sleep(0.1)
    else:
        await message.reply("Укажите слово для добавления в черный список.")
        await asyncio.sleep(0.1)


@dp.message(F.text, Command("whitelist"))
async def add_to_admin(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    
    # Получаем слово после команды
    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите слово после команды /whitelist.")
        return
    word = message_text[1]

    if word:
        if word in white_list:
            await message.reply(f"Слово '{word}' уже есть в белом списке.")
            await asyncio.sleep(0.1)
        else:
            white_list.append(word)
            # Добавляем слово в white_list.txt
            with open("txts/white_list.txt", "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в белый список.")
            await asyncio.sleep(0.1)
    else:
        await message.reply("Укажите слово для добавления в белый список.")
        await asyncio.sleep(0.1)


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
        'н': '[нhn]',
        'о': '[оo0]',
        'п': '[пn]',
        'р': '[pр]',
        'с': '[cс]',
        'т': '[тt]',
        'у': '[уy]',
        'ф': '[ф]',
        'х': '[xх]',
        'ц': '[ц]',
        'ч': '[ч4]',
        'ш': '[шw]',
        'щ': '[щ]',
        'ъ': '[ъ]',
        'ы': '[ы]',
        'ь': '[ь]',
        'э': '[э3]',
        'ю': '[ю]',
        'я': '[я]'
    }

    result = []
    for char in input_string.lower():
        if char == ' ':
            result.append(r'\s*')
        elif char in letter_to_regex:
            result.append(letter_to_regex[char])
        else:
            result.append(re.escape(char))
    
    regex_pattern = ''.join(result)
    return regex_pattern


@dp.message(F.text, Command("pattern"))
async def add_pattern(message: types.Message):
    if message.from_user.id not in adminsId:
        return
    
    # Получаем текст после команды
    pattern_text = message.text.split(maxsplit=1)
    if len(pattern_text) < 2:
        await message.reply("Пожалуйста, укажите текст паттерна после команды /pattern.")
        return
    new_pattern = pattern_text[1]
    regex_pattern = string_to_regex(new_pattern)

    # Проверка на наличие паттерна в файле
    with open('txts/ad_patterns.csv', 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        existing_patterns = [row[0] for row in reader]
    
    if regex_pattern in existing_patterns:
        await message.reply(f"Паттерн '{new_pattern}' уже существует в базе.")
        return

    compiled_pattern = re.compile(r'' + regex_pattern, re.IGNORECASE)
   
    ad_patterns.append(compiled_pattern)
    with open('txts/ad_patterns.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([regex_pattern])
   
    await message.reply(f"Добавлен новый паттерн: {new_pattern}\nРегулярное выражение: {regex_pattern}")


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
    elif feature == "ad":
        is_delete_ad = not is_delete_ad
        state = "activated" if is_delete_ad else "deactivated"

        await callback.answer(text=f'Auto delete ad {state}')

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


bad_words = []
with open("txts/bad_words.txt", "r", encoding='utf-8') as f:
    bad_words = f.readlines()
    bad_words = [word.replace("\n", "").strip() for word in bad_words]

white_list = []
with open("txts/white_list.txt", "r", encoding='utf-8') as f:
    white_list = f.readlines()
    white_list = [word.replace("\n", "").strip() for word in white_list]

delete_list = []
with open("txts/delete_list.txt", "r", encoding='utf-8') as f:
    delete_list = f.readlines()
    delete_list = [word.strip() for word in delete_list if word.strip()]


def extract_regular_chars(text):
    regular_chars = re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)
    return regular_chars


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
        'j': 'й',
        'k': 'к',
        'l': 'л',
        'm': 'м',
        'n': 'н',
        'o': 'о',
        'p': 'п',
        'q': 'к',
        'r': 'р',
        's': 'с',
        't': 'т',
        'u': 'и',
        'v': 'в',
        'w': 'в',
        'x': 'x',
        'y': 'y',
        'z': 'з'
    }

    # print("SRC", [ord(text[i]) for i in range(len(text))])
    for eng, rus in replacements.items():
        text = text.replace(eng, rus)
    # print("NEW", [ord(text[i]) for i in range(len(text))])
    return text


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_bad_word(source: list, dist: str):
    current_percent = 85

    if dist in white_list:
        return False

    for word in source:
        ratio = fuzz.ratio(dist, word)

        if word == dist:
            return True

        if ratio > current_percent:

            return True

    return False


def check_bw(message):
    if message is None:
        return False

    message_text = extract_regular_chars(message.lower())

    flag = False

    for word in message_text.split(' '):
        translit_word = replace_english_letters(word)

        is_bad = is_bad_word(bad_words, translit_word)

        # print("DEBUG:", word, translit_word, is_bad)

        if is_bad:
            flag = True
    return flag


def count_ad_matches(text, ad_patterns):
    return sum(1 for pattern in ad_patterns if pattern.search(text))


def check_ad(message):
    MATCH_THRESHOLD = 1

    message = extract_regular_chars(message)
    match_count = count_ad_matches(message, ad_patterns)

    if match_count >= MATCH_THRESHOLD:
        return True

    return False


message_texts = {}
async def notify_admins(message: types.Message, reason: str, message_text):
    global admin_messages

    admin_message = f"Обнаружено {reason}:\n\n"
    admin_message += f"От: {message.from_user.full_name} (@{message.from_user.username})\n"

    if message.text:
        admin_message += f"Текст: {message.text}\n\n"
    elif message.caption:
        admin_message += f"Подпись к файлу: {message.caption}\n\n"

    admin_message += "Выберите действие:"
    admin_messages[message.message_id] = {}

    text_id = str(uuid.uuid4())[:8]
    message_texts[text_id] = message_text

    admin_messages[message.message_id] = {}

    for admin in adminsId:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Удалить", callback_data=f"delete_{message.chat.id}_{message.message_id}_{text_id}")
        keyboard.button(text="Замутить", callback_data=f"mute_{message.chat.id}_{message.message_id}_{message.from_user.id}")
        keyboard.button(text="Забанить", callback_data=f"ban_{message.chat.id}_{message.message_id}_{message.from_user.id}")
        keyboard.button(text="Пропустить", callback_data=f"skip_{message.chat.id}_{message.message_id}")
        keyboard.adjust(2)  # Размещаем кнопки в два ряда

        sent_message = await bot.send_message(admin, admin_message, reply_markup=keyboard.as_markup())
        admin_messages[message.message_id][admin] = sent_message.message_id


@dp.message(F.new_chat_members)
async def handle_channel_post(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@dp.message(F.left_chat_member)
async def handle_channel_post1(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@dp.message()
async def work(message: types.Message):
    global is_delete_bw, is_delete_ad

    text_to_check = message.text or message.caption

    if text_to_check:
        text_to_check = " ".join(text_to_check.strip().split())
        if text_to_check in delete_list:
            try:
                await message.delete()

                # # Баним пользователя
                # await bot.ban_chat_member(message.chat.id, message.from_user.id)
                # print(f"Пользователь {message.from_user.id} забанен за сообщение из delete_list")
                return
            except Exception as e:
                print(f"Ошибка при удалении сообщения или бане пользователя: {e}")
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


@dp.callback_query(lambda c: c.data.startswith(('delete_', 'mute_', 'ban_', 'skip_')))
async def process_callback(callback_query: types.CallbackQuery):
    action, *params = callback_query.data.split('_')

    if len(params) < 2:
        await callback_query.answer("Неверный формат данных", show_alert=True)
        return

    chat_id, message_id = map(int, params[:2])

    # Удаляем исходное сообщение при нажатии любой кнопки, кроме "Пропустить"
    if action != 'skip':
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            await callback_query.message.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)

    try:
        if action == 'delete':
            text_id = params[2]
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
            if len(params) < 3:
                await callback_query.answer("Недостаточно данных для выполнения действия", show_alert=True)
                return
            user_id = int(params[2])

            if action == 'mute':
                await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False))
                await callback_query.answer("Пользователь замучен на 300 секунд.")

                # Запускаем задачу для автоматического размучивания через 300 секунд
                asyncio.create_task(unmute_user(chat_id, user_id, 300))
            elif action == 'ban':
                await bot.ban_chat_member(chat_id, user_id)
                await callback_query.answer("Пользователь забанен.")
        elif action == 'skip':
            await callback_query.answer("Сообщение пропущено.")
    except Exception as e:
        await callback_query.message.answer(f"Не удалось выполнить действие: {str(e)}", show_alert=True)

    # Удаляем сообщения с кнопками у всех админов
    if message_id in admin_messages:
        for admin, admin_message_id in admin_messages[message_id].items():
            try:
                await bot.delete_message(admin, admin_message_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")
        del admin_messages[message_id]


async def main(message='Бот запущен'):
    for admin in adminsId:
        await bot.send_message(chat_id=admin, text=message)
        await send_control_message(message, admin)

    dp.startup.register(start_bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
