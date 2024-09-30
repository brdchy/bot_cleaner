import asyncio
import logging
import html
import re
import uuid
import csv
from datetime import datetime, timedelta
import os

from aiogram.filters.command import Command, CommandObject
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

from core.settings import BOT_TOKEN
import core.config as config
import core.utils.detect as detect
import core.utils.functions as fc 
from core.commands import set_commands

# --- Глобальные переменные ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)

admin_messages = {}
temp_patterns = {}
user_data = {}
message_texts = {}
action_storage = {}

is_delete_ad = False
is_delete_bw = False


# --- Обработчики команд ---
async def start_bot(bot: Bot):
    await set_commands(bot)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return
    await message.answer(text="Привет. Для информации о функционале бота напиши:\n/help")


@dp.message(Command("help"))
async def help(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return
    text = ("Команды:\n"
            "/mode - изменить режим работы\n"
            "/blacklist <слово> - добавить слово в черный список\n"
            "/whitelist <слово> - добавить слово в белый список\n\n"
            "/add_pattern <текст> - добавить текст рекламы в список паттернов\n\nне стоит добавлять в паттерны целое сообщение с рекламой, лучше по частям\n\nнапример, если текст: 'Кому интересен хороший дополнительный заработок в свободное время - пишите в лс. От 18 лет, частичная занятость'\nто добавляем такие паттерны: 'Кому интересен хороший дополнительный заработок', 'заработок в свободное время', 'пишите в лс', 'От 18 лет, частичная занятость'\n\n"
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
            "/ban <причина> - забанить пользователя\n"
            "/unban <user_id> - разбанить пользователя\n"
            "/get_id - узнать user_id пользователя\n"
            "/report - отправить репорт админам\n"
            "/file_give - получить файл\n")
    await message.answer(text=text)


@dp.message(F.text, Command("admin_actions"))
async def view_admin_actions(message: types.Message):
    if message.from_user.id not in config.adminsId:
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
    if message.from_user.id in config.adminsId:
        await send_control_message(message, message.from_user.id)


@dp.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: types.Message):
    if message.from_user.id not in config.adminsId:
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

    if user_id not in config.adminsId:
        config.adminsId.append(user_id)
        with open(config.ADMINS_FILE, "a", encoding='utf-8') as f:
            f.write(f"\n{user_id}")
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) добавлен в список админов.")
        await log_admin_action(message.from_user.id, "add_admin", f"Added admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")


@dp.message(F.text, Command("remove_admin"))
async def remove_from_adminlist(message: types.Message):
    if message.from_user.id not in config.adminsId:
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

    if user_id in config.adminsId:
        config.adminsId.remove(user_id)
        with open(config.ADMINS_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(map(str, config.adminsId)))
        await message.reply(f"Админ @{html.escape(username)} (ID: {user_id}) удален из списка админов.")
        await log_admin_action(message.from_user.id, "remove_admin", f"Removed admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) не является админом.")


@dp.message(F.text, Command("my_id"))
async def my_id(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return
    await message.answer(f"Ваш ID:\n```{message.from_user.id}```", parse_mode="MarkdownV2")


@dp.message(F.text, Command("get_id"))
async def get_user_id(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await message.reply(f"ID пользователя:\n```{user_id}```", parse_mode="MarkdownV2")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("mute"))
async def mute(message: types.Message, command: CommandObject):
    if message.from_user.id not in config.adminsId:
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
        await bot.restrict_chat_member(message.chat.id, user_id, types.ChatPermissions(can_send_messages=False), until_date=duration)
        await message.answer(f"Пользователь @{user.username} замучен на {duration} секунд.")
        await log_admin_action(message.from_user.id, "mute", f"Muted user: {user_id} (@{user.username}) for {duration} seconds")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(F.text, Command("unmute"))
async def unmute(message: types.Message):
    if message.from_user.id not in config.adminsId:
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

@dp.message(F.text, Command("ban"))
async def ban(message: types.Message, command: CommandObject):
    if message.from_user.id not in config.adminsId:
        return
    reason = "не указана"
    if command.args:
        reason = command.args
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id

        try:
            user = await bot.get_chat(user_id)
            username = user.username or "Unknown"   
        except:
            username = "Unknown"
        try:
            await bot.ban_chat_member(message.chat.id, user_id)
            await message.answer(f"Пользователь @{username} забанен.\nПричина: {reason}")

            with open(config.BAN_LIST_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([user_id, username])

            await log_admin_action(message.from_user.id, "ban", f"Banned user: {user_id} Reason: {reason}")
        except Exception as e:
            await message.reply(f"Не удалось забанить пользователя: {str(e)}")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@dp.message(Command('unban'))
async def unban_user(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return
    
    # Получаем user_id для разбана
    if message.reply_to_message:
        # Если команда отправлена в ответ на сообщение
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        # Если user_id указан после команды
        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("Неверный формат user_id. Используйте числовой ID.")
            return
    else:
        await message.reply("Укажите user_id после команды или ответьте на сообщение пользователя.")
        return

    try:
        # Пытаемся разбанить пользователя
        await bot.unban_chat_member(message.chat.id, user_id)
        await message.reply(f"Пользователь с ID {user_id} разбанен.")
        await log_admin_action(message.from_user.id, "unban", f"Unbanned user: {user_id}")
    except Exception as e:
        await message.reply(f"Не удалось разбанить пользователя. Ошибка: {str(e)}")


@dp.message(F.text, Command("blacklist"))
async def add_to_blacklist(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return

    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите плохое слово после команды /blacklist.")
        return
    word = message_text[1]
    if word:
        if word in config.bad_words:
            await message.reply(f"Слово '{word}' уже есть в черном списке.")
        else:
            config.bad_words.append(word)
            with open(config.BAD_WORDS_FILE, "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в черный список.")
            await log_admin_action(message.from_user.id, "blacklist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в черный список.")


@dp.message(F.text, Command("whitelist"))
async def add_to_admin(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return

    message_text = message.text.split(maxsplit=1)
    if len(message_text) < 2:
        await message.reply("Пожалуйста, укажите слово после команды /whitelist.")
        return
    word = message_text[1]

    if word:
        if word in config.white_list:
            await message.reply(f"Слово '{word}' уже есть в белом списке.")
        else:
            config.white_list.append(word)
            with open(config.WHITE_LIST_FILE, "a", encoding='utf-8') as f:
                f.write("\n" + word)
            await message.reply(f"Слово '{word}' добавлено в белый список.")
            await log_admin_action(message.from_user.id, "whitelist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в белый список.")


@dp.message(Command("watch_patterns"))
async def watch_patterns(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return

    with open(config.AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        patterns = [row[0] for row in reader if row and row[0].strip()]

    if not patterns:
        await message.reply("Список паттернов пуст.")
        return

    readable_patterns = [f"{i + 1}. {fc.regex_to_readable(pattern)}" for i, pattern in enumerate(patterns)]

    chunk_size = 100
    pattern_chunks = [readable_patterns[i:i + chunk_size] for i in range(0, len(readable_patterns), chunk_size)]

    for chunk in pattern_chunks:
        patterns_text = "\n".join(chunk)
        await message.reply(f"Текущие паттерны:\n\n{patterns_text}")


@dp.message(F.text, Command("add_pattern"))
async def add_pattern(message: types.Message):
    if message.from_user.id not in config.adminsId:
        return

    pattern_text = message.text.split(maxsplit=1)
    if len(pattern_text) < 2:
        await message.reply("Пожалуйста, укажите текст паттерна рекламы после команды /add_pattern.")
        return

    new_pattern = " ".join(pattern_text[1].strip().split())
    new_pattern = fc.extract_regular_chars(new_pattern)
    regex_pattern = fc.string_to_regex(new_pattern)

    with open(config.AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
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
    if message.from_user.id not in config.adminsId:
        return

    with open(config.AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        existing_patterns = [row[0] for row in reader if row and row[0].strip()]

    if not existing_patterns:
        await message.reply("Список паттернов пуст.")
        return

    patterns_list = "\n".join([f"{i + 1}. {fc.regex_to_readable(pattern)}" for i, pattern in enumerate(existing_patterns)])
    sent_message = await message.reply(f"Список паттернов:\n\n{patterns_list}\n\nВведите номер паттерна, который вы хотите удалить:")

    user_data[message.from_user.id] = {
        'existing_patterns': existing_patterns,
        'waiting_for_pattern_number': True,
        'timer': asyncio.create_task(clear_user_data(message.from_user.id, config.MESSAGE_TIMEOUT, sent_message)),
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
                               f"Removed pattern: '{fc.regex_to_readable(pattern_to_delete)}'")

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
    config.ad_patterns.append(compiled_pattern)
    with open(config.AD_PATTERNS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([regex_pattern])
    await message.reply(f"Добавлен новый паттерн: {new_pattern}\nРегулярное выражение: {regex_pattern}")


async def delete_pattern_from_database(message: types.Message, pattern_to_delete: str):
    with open(config.AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        patterns = list(reader)

    patterns = [pattern for pattern in patterns if pattern[0] != pattern_to_delete]

    with open(config.AD_PATTERNS_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(patterns)

    config.ad_patterns = [re.compile(r'' + pattern[0], re.IGNORECASE) for pattern in patterns]

    await message.reply(f"Паттерн '{fc.regex_to_readable(pattern_to_delete)}' успешно удален.")


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
            InlineKeyboardButton(text=f"{config.MATCH_THRESHOLD}", callback_data="current"),
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

    try:
        old_threshold = config.MATCH_THRESHOLD
        if callback_query.data == 'decrease':
            config.MATCH_THRESHOLD = max(1, config.MATCH_THRESHOLD - 1)
        elif callback_query.data == 'increase':
            config.MATCH_THRESHOLD += 1

        await callback_query.answer()
        await callback_query.message.edit_text(
            text="Текущее значение порога совпадений",
            reply_markup=get_threshold_keyboard()
        )

        await log_admin_action(callback_query.from_user.id, "change_threshold",
                               f"Changed from {old_threshold} to {config.MATCH_THRESHOLD}")
    except:
        pass


@dp.message(Command("file_give")) 
async def cmd_give_file(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Удаленная реклама", callback_data=f"file_{config.DELETED_AD_FILE}")
    keyboard.button(text="Удаленные плохие слова", callback_data=f"file_{config.DELETED_BW_FILE}")
    keyboard.button(text="Бан лист", callback_data=f"file_{config.BAN_LIST_FILE}")
    keyboard.adjust(2)

    await message.reply("Выберите нужный файл:", reply_markup=keyboard.as_markup())


@dp.callback_query(lambda c: c.data.startswith('file_'))
async def process_file_choice(callback_query: types.CallbackQuery):
    file_name = callback_query.data.split("_", 1)[-1]

    if not os.path.exists(file_name):
        await callback_query.answer(f"Файл '{file_name}' не найден.", show_alert=True)
        return
    
    if os.path.getsize(file_name) == 0:
        await callback_query.answer(f"Файл '{file_name}' пуст и не может быть отправлен.", show_alert=True)
        return

    try:
        file = FSInputFile(file_name)
        await callback_query.message.reply_document(file)
        await callback_query.answer()
    except Exception as e:
        error_message = str(e)
        if len(error_message) > 200:
            error_message = error_message[:197] + "..."
        print(error_message)
        await callback_query.answer(f"Ошибка при отправке файла: {error_message}", show_alert=True)


@dp.message(Command("get_username"))
async def get_username(message: types.Message):
    # Проверяем, является ли сообщение ответом на другое сообщение
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        username = user.username or f"{user.first_name} {user.last_name}"
        await message.reply(f"Имя пользователя: @{username}")
    else:
        # Если сообщение не является ответом, ищем user_id в аргументах команды
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            user_id = int(args[1])
            try:
                user = await bot.get_chat_member(message.chat.id, user_id)
                username = user.user.username or f"{user.user.first_name} {user.user.last_name}"
                await message.reply(f"Имя пользователя: @{username}")
            except Exception as e:
                await message.reply(f"Ошибка: {str(e)}")
        else:
            await message.reply("Пожалуйста, ответьте на сообщение пользователя или укажите user_id.")


@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    if message.reply_to_message:
        text_id = str(uuid.uuid4())[:8]
        message_text = message.reply_to_message.text or message.reply_to_message.caption
        message_texts[text_id] = message_text

        # Отправляем репорт админам и сохраняем ID сообщения с подтверждением
        await send_report_to_admins(message.reply_to_message, message, text_id)

        confirmation_message = await message.reply("Спасибо за ваш репорт. Администраторы рассмотрят его в ближайшее время.")

        # Сохраняем ID сообщения с подтверждением
        admin_messages[message.reply_to_message.message_id]['confirmation_message_id'] = confirmation_message.message_id
    else:
        await message.reply("Пожалуйста, используйте эту команду в ответ на сообщение, которое вы хотите зарепортить.")


async def send_report_to_admins(reported_message: types.Message, reporter_message: types.Message, text_id: str): 
    text_to_check = reported_message.text or reported_message.caption
    text_to_check = " ".join(text_to_check.strip().split())

    report_text = (f"Новый репорт:\n\n"
                   f"От: {reporter_message.from_user.full_name} (@{reporter_message.from_user.username})\n\n"
                   f"Репортируемое сообщение:\n"
                   f"От: {reported_message.from_user.full_name} (@{reported_message.from_user.username})\n"
                   f"Текст: {text_to_check}\n\n"
                   f"Сообщение с плохим словом или рекламой?")
    
    action_id = str(uuid.uuid4())[:8]  # Генерируем короткий уникальный идентификатор
    action_data = {
        "chat_id": reported_message.chat.id,
        "message_id": reported_message.message_id,
        "text_id": text_id,
        "user_id": reported_message.from_user.id,
        "reason": ""
    }
    # Сохраняем данные в словарь или базу данных
    action_storage[action_id] = action_data

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="С рекламой", callback_data=f"report-type_ad_{action_id}")
    keyboard.button(text="С плохим словом", callback_data=f"report-type_bw_{action_id}")
    keyboard.button(text="Нет", callback_data=f"report-type_none_{action_id}")
    keyboard.adjust(2)

    admin_messages[reported_message.message_id] = {
        'admins': {},
        'reporter_message_id': reporter_message.message_id
    }

    for admin in config.adminsId:
        try:
            sent_message = await bot.send_message(admin, report_text, reply_markup=keyboard.as_markup())
            admin_messages[reported_message.message_id]['admins'][admin] = sent_message.message_id
        except Exception as e:
            print(f"Не удалось отправить репорт админу {admin}: {str(e)}")


@dp.callback_query(lambda c: c.data.startswith('report-type_')) 
async def process_report_type_callback(callback_query: types.CallbackQuery):
    _, report_type, action_id = callback_query.data.split('_')
    action_data = action_storage[action_id]
    chat_id = action_data['chat_id']
    message_id = action_data['message_id']
    user_id = action_data['user_id']
    text_id = action_data['text_id']

    if report_type == 'none':
        await callback_query.answer("Репорт отклонен.")

        message_text = message_texts.get(text_id, "")
        await log_admin_action(callback_query.from_user.id, "skip reported message", f"Skipped message: '{message_text}'")
        if text_id:
            del message_texts[text_id]
        
        # Удаление сообщений с репортом у всех админов
        if message_id in admin_messages:
            for admin, admin_message_id in admin_messages[message_id]['admins'].items():
                try:
                    await bot.delete_message(admin, admin_message_id)
                except Exception as e:
                    print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")

        # Удаление сообщения с репортом
        try:
            reporter_message_id = admin_messages[message_id]['reporter_message_id']
            await bot.delete_message(chat_id, reporter_message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение с репортом: {str(e)}")

        # Удаление ответа бота
        try:
            confirmation_message_id = admin_messages[message_id]['confirmation_message_id']
            await bot.delete_message(chat_id, confirmation_message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение с подтверждением репорта: {str(e)}")

        del admin_messages[message_id]
        return

    # Создаем новую клавиатуру для действий
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Удалить", callback_data=f"report-delete_{report_type}_{action_id}")
    keyboard.button(text="Замутить", callback_data=f"report-mute_{report_type}_{action_id}")
    keyboard.button(text="Забанить", callback_data=f"report-ban_{report_type}_{action_id}")
    keyboard.adjust(2)

    await callback_query.message.edit_text(
        f"{callback_query.message.text}\n\nТип репорта: {'Реклама' if report_type == 'ad' else 'Плохое слово'}\n\nВыберите действие:",
        reply_markup=keyboard.as_markup()
    )


@dp.callback_query(lambda c: c.data.startswith(('report-delete_', 'report-mute_', 'report-ban_', 'report-skip_')))
async def process_report_callback(callback_query: types.CallbackQuery):
    action, reason, action_id = callback_query.data.split('_')

    report_data = action_storage[action_id]
    chat_id = report_data['chat_id']
    message_id = report_data['message_id']
    user_id = report_data['user_id']
    text_id = report_data['text_id']

    try:
        await bot.delete_message(chat_id, message_id)

        message_text = message_texts.get(text_id, "")
        await log_admin_action(callback_query.from_user.id, f"delete reported {reason}_message ", f"Deleted message: '{message_text}'")
    except TelegramBadRequest as e:
        if "message to delete not found" in str(e):
            await callback_query.answer("Сообщение уже было удалено", show_alert=True)
        else:
            await callback_query.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)
    
    await increment_violation_count(user_id, reason, message_text)

    try:
        if action == 'report-delete':
            message_text = message_texts.get(text_id, "")

            if message_text and message_text not in config.bad_words and message_text not in config.delete_list:
                with open(config.DELETE_LIST_FILE, "a", newline='', encoding='utf-8') as f:
                    f.write(message_text + "\n")
                config.delete_list.append(message_text)
            if text_id:
                del message_texts[text_id]
            await callback_query.answer("Сообщение удалено.")
        elif action in ['report-mute', 'report-ban']:
            if action == 'report-mute':
                duration = 300

                await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False), until_date=duration)
                await callback_query.answer("Пользователь замучен на 300 секунд.")
                await log_admin_action(callback_query.from_user.id, "mute reported user", f"Muted user: {user_id}")
            elif action == 'report-ban':
                await bot.ban_chat_member(chat_id, user_id)
                await callback_query.answer("Пользователь забанен.")

                try:
                    user = await bot.get_chat(user_id)
                    username = user.username or "Unknown"
                except:
                    username = "Unknown"

                with open(config.BAN_LIST_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([user_id, username])

                await log_admin_action(callback_query.from_user.id, "ban reported user", f"Banned user: {user_id}")
    except Exception as e:
        await callback_query.message.answer(f"Не удалось выполнить действие: {str(e)}", show_alert=True)

    # Удаление сообщений с репортом у всех админов
    if message_id in admin_messages:
        for admin, admin_message_id in admin_messages[message_id]['admins'].items():
            try:
                await bot.delete_message(admin, admin_message_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")

        # Удаление сообщения с репортом
        try:
            reporter_message_id = admin_messages[message_id]['reporter_message_id']
            await bot.delete_message(chat_id, reporter_message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение с репортом: {str(e)}")

        # Удаление ответа бота
        try:
            confirmation_message_id = admin_messages[message_id]['confirmation_message_id']
            await bot.delete_message(chat_id, confirmation_message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение с подтверждением репорта: {str(e)}")

        del admin_messages[message_id]


# --- Обработчики сообщений ---
@dp.message()
async def work(message: types.Message):
    global is_delete_bw, is_delete_ad

    text_to_check = message.text or message.caption

    if text_to_check:
        text_to_check = " ".join(text_to_check.strip().split())
        if text_to_check in config.delete_list:
            try:
                await message.delete()
                return
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
                return

        bad_words_found = detect.check_bw(text_to_check)
        ad_patterns_found, is_ad = detect.check_ad(text_to_check)

        if bad_words_found:
            if is_delete_bw:
                with open(config.DELETED_BW_FILE, "a", encoding='utf-8') as f:
                    f.write(text_to_check + "\n")

                await increment_violation_count(message.from_user.id, "bw", text_to_check)

                return await message.delete()
            else:
                return await notify_admins(message, "сообщение с плохим словом", text_to_check, bad_words_found)
        elif is_ad:
            if is_delete_ad:
                with open(config.DELETED_AD_FILE, "a", encoding='utf-8') as f:
                    f.write(text_to_check + "\n")

                await increment_violation_count(message.from_user.id, "ad", text_to_check)

                return await message.delete()
            else:
                return await notify_admins(message, "рекламное сообщение", text_to_check, ad_patterns_found)


# --- Вспомогательные функции ---
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


async def notify_admins(message: types.Message, reason: str, message_text, triggers): 
    global admin_messages

    trigger_text = ", ".join(triggers) if triggers else "Не определено"

    admin_message = (f"Обнаружено {reason}:\n\n"
                     f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
                     f"Триггер: {trigger_text}\n"
                     f"Сообщение: {message.text or message.caption}\n\n"
                     "Выберите действие:")

    admin_messages[message.message_id] = {}
    text_id = str(uuid.uuid4())[:8]
    message_texts[text_id] = message_text

    action_id = str(uuid.uuid4())[:8]  # Генерируем короткий уникальный идентификатор
    action_data = {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "text_id": text_id,
        "user_id": message.from_user.id,
        "reason": reason
    }
    # Сохраняем данные в словарь или базу данных
    action_storage[action_id] = action_data

    if reason == "сообщение с плохим словом":
        reason = "bw"
    else:
        reason = "ad"

    for admin in config.adminsId:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Удалить", callback_data=f"delete_{action_id}")
        keyboard.button(text="Замутить", callback_data=f"mute_{action_id}")
        keyboard.button(text="Забанить", callback_data=f"ban_{action_id}")
        keyboard.button(text="Пропустить", callback_data=f"skip_{action_id}")
        keyboard.adjust(2)

        sent_message = await bot.send_message(admin, admin_message, reply_markup=keyboard.as_markup())
        admin_messages[message.message_id][admin] = sent_message.message_id


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


@dp.callback_query(lambda c: c.data.startswith(('delete_', 'mute_', 'ban_', 'skip_'))) 
async def process_callback(callback_query: types.CallbackQuery):
    action, action_id = callback_query.data.split('_')

    action_data = action_storage[action_id]

    chat_id = action_data['chat_id']
    message_id = action_data['message_id']
    user_id = action_data['user_id']
    text_id = action_data['text_id']
    reason = action_data['reason']

    message_text = message_texts.get(text_id, "")

    if action != 'skip':
        try:
            await bot.delete_message(chat_id, message_id)

            if message_text in config.bad_words or message_text in config.delete_list:
                pass
            else:
                with open(config.DELETE_LIST_FILE, "a", newline='', encoding='utf-8') as f:
                    f.write(message_text + "\n")
                config.delete_list.append(message_text)

            await increment_violation_count(user_id, reason, message_text)

            del message_texts[text_id]

            await log_admin_action(callback_query.from_user.id, "delete message", f"Deleted message: '{message_text}'")
        except Exception as e:
            await callback_query.message.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)

    try:
        if action == 'delete':
            await callback_query.answer("Сообщение удалено.")
        elif action in ['mute', 'ban']:
            if action == 'mute':
                duration = 300
                await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False), until_date=duration)
                await callback_query.answer("Пользователь замучен на 300 секунд.")
                await log_admin_action(callback_query.from_user.id, "mute user", f"Muted user: {user_id}")
            elif action == 'ban':
                # with open(config.BAN_LIST_FILE, "a", encoding='utf-8') as f:
                #     f.write(user_id + "\n")
                await bot.ban_chat_member(chat_id, user_id)
                await callback_query.answer("Пользователь забанен.")

                try:
                    user = await bot.get_chat(user_id)
                    username = user.username or "Unknown"
                except:
                    username = "Unknown"

                with open(config.BAN_LIST_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([user_id, username])

                await log_admin_action(callback_query.from_user.id, "ban user", f"Banned user: {user_id}")
        elif action == 'skip':
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
    if os.path.isfile(config.ADMIN_ACTIONS_FILE):
        with open(config.ADMIN_ACTIONS_FILE, 'r', newline='', encoding='utf-8') as f:
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
    with open(config.ADMIN_ACTIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, user_id, f"@{username}", action, details])


async def delete_old_records():
    one_day_ago = datetime.now() - timedelta(days=1)
    try:
        with open(config.ADMIN_ACTIONS_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            all_rows = list(reader)
        header = all_rows[0]
        filtered_rows = [row for row in all_rows[1:]
                         if datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > one_day_ago]
        with open(config.ADMIN_ACTIONS_FILE, 'w', newline='', encoding='utf-8') as file:
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
    for admin in config.adminsId:
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
