import asyncio
import logging
import html
import re
import uuid

from aiogram.filters.command import Command
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
with open('admins_list.txt', 'r') as file:
    adminsId = [int(line.strip()) for line in file if line.strip().isdigit()]
print(adminsId)

is_delete_ad = False
is_delete_bw = False


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Начало'),
        BotCommand(command='mode', description='Изменить режим работы'),
        BotCommand(command='whitelist', description='Добавить слово в белый список'),
        BotCommand(command='blacklist', description='Добавить слово в черный список'),
        BotCommand(command='add_admin', description='Добавить админа'),
        BotCommand(command='remove_admin', description='Добавить убрать админа'),
        ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def start_bot(bot: Bot):
    await set_commands(bot)


@dp.message(F.new_chat_members)
async def handle_channel_post(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@dp.message(F.left_chat_member)
async def handle_channel_post(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in adminsId:
        await bot.send_message(chat_id=message.from_user.id ,text="Привет")


@dp.message(Command("mode"))
async def change(message: types.Message):
    if message.from_user.id in adminsId:
        await send_control_message(message, message.from_user.id)


# Обработчик команды /addAdmin
@dp.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: types.Message):
    if message.from_user.id in adminsId:
        # Получаем аргументы после команды
        args = message.text.split()[1:]

        # Попытка добавить по ID
        try:
            user_id = int(args[0])  # Проверяем, что это действительно число
            user = await message.bot.get_chat(user_id)
            username = user.username or "без имени пользователя"
        except ValueError:
            await message.reply("Некорректный ID пользователя. Используйте число.")
            return
        except Exception:
            await message.reply(f"Не удалось найти пользователя с ID {args[0]}.")
            return

        if user_id not in adminsId:
            adminsId.append(user_id)
            with open("admins_list.txt", "a", encoding='utf-8') as f:
                f.write("\n" + user_id)
            await message.reply(f"Админ @{html.escape(username)} (ID: {user_id}) добавлен в админлист.")
        else:
            await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")


# Обработчик команды /removeAdmin
@dp.message(F.text, Command("remove_admin"))
async def remove_from_adminlist(message: types.Message):
    if message.from_user.id in adminsId:
        # Получаем аргументы после команды
        args = message.text.split()[1:]

        if not args:
            await message.reply("Использование: /removeAdmin @username или /removeAdmin user_id")
            return

        # Попытка удалить по ID
        try:
            user_id = (int(args[0]))  # Проверяем, что это действительно число
            user = await message.bot.get_chat(user_id)
            username = user.username or "без имени пользователя"
        except ValueError:
            await message.reply("Некорректный ID пользователя. Используйте число.")
            return
        except Exception:
            await message.reply(f"Не удалось найти пользователя с ID {args[0]}.")
            return

        if int(user_id) in adminsId:
            adminsId.remove(user_id)
            # Обновляем файл admins_list.txt
            with open("admins_list.txt", "w", encoding='utf-8') as f:
                f.write("\n".join(adminsId))
            await message.reply(f"Админ @{username} (ID: {user_id}) удален из админлиста.")
        else:
            await message.reply(f"Пользователь @{username} (ID: {user_id}) не является админом.")
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")


@dp.message(F.text, Command("my_id"))
async def id(message: types.Message):
    await message.answer(f"Ваш ID:\n```md\n{message.from_user.id}\n```", parse_mode="MarkdownV2")


# Обработчик команды /blacklist
@dp.message(F.text, Command("blacklist"))
async def add_to_blacklist(message: types.Message):
    if message.from_user.id in adminsId:
    # Получаем слово после команды
        word = message.text.split(' ')[-1]
        if word:
            bad_words.append(word)
            # Добавляем слово в bad_words.txt
            with open("bad_words.txt", "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в черный список.")
        else:
            await message.reply("Укажите слово для добавления в черный список.")


# Обработчик команды /whitelist
@dp.message(F.text, Command("whitelist"))
async def add_to_admin(message: types.Message):
    if message.from_user.id in adminsId:
    # Получаем слово после команды
        word = message.text.split(' ')[-1]
        if word:
            white_list.append(word)
            # Добавляем слово в white_list.txt
            with open("white_list.txt", "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в белый список.")
        else:
            await message.reply("Укажите слово для добавления в белый список.")


async def send_control_message(message: types.Message, admin):
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
    await bot.send_message(chat_id=admin, text="Режим работы", reply_markup=keyboard)


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
with open("bad_words.txt", "r", encoding='utf-8') as f:
    bad_words = f.readlines()
    bad_words = [word.replace("\n", "").strip() for word in bad_words]

white_list = []
with open("white_list.txt", "r", encoding='utf-8') as f:
    white_list = f.readlines()
    white_list = [word.replace("\n", "").strip() for word in white_list]

delete_list = []
with open("delete_list.txt", "r", encoding='utf-8') as f:
    delete_list = f.readlines()
    delete_list = [word.replace("\n", "").strip() for word in delete_list]


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
        'h': 'н',
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
        'u': 'у',
        'v': 'в',
        'w': 'в',
        'x': 'х',
        'y': 'й',
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
    message_text = message_text.replace('\n', ' ')

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
    ad_patterns = [
    re.compile(r'[iиu]щ[уy] лю[dд][еёe]й для [dд][oо]п за[рp][aа][бb6][oо]тк[aа]', re.IGNORECASE),
    re.compile(r'[нn]а [уy][dд]ал[еёe][нn][нn]ой о[cс][нn][оo][вb][еёe]', re.IGNORECASE),
    re.compile(r'[вb] [cс][вb][oо][бb6][oо][dд][нn][oо][еёe] [вb][рp][еёe][мm]я', re.IGNORECASE),
    re.compile(r'п[oо][dд][рp][оo][бb6][нn][oо][cс]т[iиu] [вb] л[iиu][ч4][нn]ы[еёe] [cс][oо][oо][бb6]щ[еёe][нn][iиu]я', re.IGNORECASE),
    re.compile(r'[уy][dд][aа]л[еёe][нn][нn][aа]я [рp][aа][бb6][oо]т[aа]', re.IGNORECASE),
    re.compile(r'кт[oо] [iиu]щ[еёe]т п[oо][dд][рp][aа][бb6][oо]тк[уy]', re.IGNORECASE),
    re.compile(r'[рp][aа][b6б][oо]т[aаеe] [нn][aа] [dд][oо][мm][уy]', re.IGNORECASE),
    re.compile(r'[dд]ля п[oо]л[уy][ч4][еёe][нn][iиu]я [dд][oо]п(?:\.?\s*|[oо]л[нn][iиu]т[еёe]ль[нn][oо]г[oо]\s+)[dд][oо]х[oо][dд][aа]', re.IGNORECASE),
    re.compile(r'[iиu]щ[уy] п[аa][рp]т[нn][ёеe][рp][оo][вb] [вb] к[оo][мm][аa][нn][дd][уy]', re.IGNORECASE),
    re.compile(r'[сc] (?:т[еe]л[еe]ф[оo][нn][аa]|к[оo][мm]п[ьb]ю?т[еe][рp][аa])', re.IGNORECASE),
    re.compile(r'[оo]т\s*1?[8\u0038\u0030\u03a3\u0417]\s*л[еe]т,?\s*[чч4][аa][сc]т[iиu][чч4][нn][аa]я\s*з[аa][нn]ят[оo][сc]т[ьb]', re.IGNORECASE),
    re.compile(r'х[оo][рp][оo]ш[иi]й\s*[дd][оo]п[оo]л[нn][иi]т[еe]л[ьb][нn]ый\s*з[аa][рp][аa][бb6][оo]т[оo]к', re.IGNORECASE),
    re.compile(r'[рp][aа][бb6][oо]т[aа] [нn][aа] [уy][dд][aа]л[еёe][нn][кk][еёe]', re.IGNORECASE),
    re.compile(r'[гg][иi][бb6][кk][иi]й [гg][рp][aа][фf][иi][кk]', re.IGNORECASE),
    re.compile(r'[сc][вb][oо][бb6][oо][dд][нn]ый [гg][рp][aа][фf][иi][кk]', re.IGNORECASE),
    re.compile(r'[dд][иi][сc]т[aа][нn]ц[иi][oо][нn][нn][aа]я [рp][aа][бb6][oо]т[aа]', re.IGNORECASE),
    re.compile(r'[рp][aа][бb6][oо]т[aа] [иi]з [dд][oо][мm][aа]', re.IGNORECASE),
    re.compile(r'[пn][оo][dд][рp][оo][бb6][нn][оo][сc]т[иi] [вb] л[иi][чч4][кk][уy]', re.IGNORECASE),
    re.compile(r'[пn][оo][dд][рp][оo][бb6][нn][оo][сc]т[иi] [вb] л[cс]', re.IGNORECASE),
    ]
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


@dp.message()
async def work(message: types.Message):
    global is_delete_bw, is_delete_ad

    # if message.content_type in [types.ContentType.NEW_CHAT_MEMBERS, types.ContentType.LEFT_CHAT_MEMBER]:
    #     await message.delete()
    #     return
    text_to_check = message.text or message.caption

    if text_to_check:
        if text_to_check in delete_list:
            try:
                # Удаляем сообщение
                await message.delete()
                # Баним пользователя
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

            with open("delete_list.txt", "a", encoding='utf-8') as f:
                f.write("\n" + message_text)
            del message_texts[text_id]

            await callback_query.answer("Сообщение удалено.")
        elif action in ['mute', 'ban']:
            if len(params) < 3:
                await callback_query.answer("Недостаточно данных для выполнения действия", show_alert=True)
                return
            user_id = int(params[2])

            if action == 'mute':
                await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False))
                await callback_query.answer("Пользователь замучен на 10 секунд.")

                # Запускаем задачу для автоматического размучивания через 10 секунд
                asyncio.create_task(unmute_user(chat_id, user_id, 10))
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


async def main(message='Бот запущен'):
    for admin in adminsId:
        await bot.send_message(chat_id=admin, text=message)
        await send_control_message(message, admin)

    dp.startup.register(start_bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
