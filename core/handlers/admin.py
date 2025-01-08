import asyncio
import logging
import html
import re
import uuid
import csv
from datetime import datetime, timedelta
import os

from aiogram import Router
from aiogram.filters.command import Command, CommandObject
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

import core.config as config
import core.utils.detect as detect
import core.utils.functions as fc 

from core import dependencies

router = Router()

# admin_messages = {}
temp_patterns = {}
user_data = {}
# message_texts = {}
# action_storage = {}


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in config.adminsId:
        return
    await message.answer(text="Привет. Для информации о функционале бота напиши:\n/help")


@router.message(Command("help"))
async def help(message: Message):
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


@router.message(F.text, Command("admin_actions"))
async def view_admin_actions(message: Message):
    if message.from_user.id not in config.adminsId:
        return

    admin_actions = fc.load_admin_actions()

    # Выберем последние 30 действий
    last_actions = admin_actions[-30:]

    response = "Последние действия админов:\n\n"
    for action in last_actions:
        response += f"{action['timestamp']} - {action['username']} - {action['action']}: {action['details']}\n"

    await message.reply(response)


@router.message(Command("mode"))
async def change(message: Message):
    if message.from_user.id in config.adminsId:
        await send_control_message(message, message.from_user.id)


async def send_control_message(message: Message, adminId):
    global is_delete_bw
    global is_delete_ad

    buttons = InlineKeyboardBuilder()
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"Autodelete bad words: {'ON' if dependencies.is_delete_bw else 'OFF'}",
                callback_data="toggle_delete_bw"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=f"Autodelete AD: {'ON' if dependencies.is_delete_ad else 'OFF'}",
                callback_data="toggle_delete_ad"
            ),
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text="Режим работы", reply_markup=keyboard)


@router.callback_query(F.data.startswith("toggle_delete_"))
async def toggle_delete(callback: CallbackQuery):
    global is_delete_bw, is_delete_ad

    feature = callback.data.split("_")[-1]
    if feature == "bw":
        dependencies.is_delete_bw = not dependencies.is_delete_bw
        state = "activated" if dependencies.is_delete_bw else "deactivated"
        await callback.answer(text=f'Auto delete bad words {state}')
        await fc.log_admin_action(callback.from_user.id, "toggle_delete_bw", f"Auto delete bad words {state}")
    elif feature == "ad":
        is_delete_ad = not is_delete_ad
        state = "activated" if is_delete_ad else "deactivated"
        await callback.answer(text=f'Auto delete ad {state}')
        await fc.log_admin_action(callback.from_user.id, "toggle_delete_ad", f"Auto delete ad {state}")

    # Обновляем сообщение с новым состоянием кнопок
    buttons = InlineKeyboardBuilder()
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"Autodelete bad words: {'ON' if dependencies.is_delete_bw else 'OFF'}",
                callback_data="toggle_delete_bw"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=f"Autodelete AD: {'ON' if dependencies.is_delete_ad else 'OFF'}",
                callback_data="toggle_delete_ad"
            ),
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Режим работы", reply_markup=keyboard)


@router.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: Message):
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
        await fc.log_admin_action(message.from_user.id, "add_admin", f"Added admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")


@router.message(F.text, Command("remove_admin"))
async def remove_from_adminlist(message: Message):
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
        await fc.log_admin_action(message.from_user.id, "remove_admin", f"Removed admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) не является админом.")


@router.message(F.text, Command("my_id"))
async def my_id(message: Message):
    if message.from_user.id not in config.adminsId:
        return
    await message.answer(f"Ваш ID:\n```{message.from_user.id}```", parse_mode="MarkdownV2")


@router.message(F.text, Command("get_id"))
async def get_user_id(message: Message):
    if message.from_user.id not in config.adminsId:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await message.reply(f"ID пользователя:\n```{user_id}```", parse_mode="MarkdownV2")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@router.message(Command("get_username"))
async def get_username(message: Message, bot: Bot):
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


@router.message(F.text, Command("mute"))
async def mute(bot: Bot, message: Message, command: CommandObject):
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
        await fc.log_admin_action(message.from_user.id, "mute", f"Muted user: {user_id} (@{user.username}) for {duration} seconds")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@router.message(F.text, Command("unmute"))
async def unmute(bot: Bot, message: Message):
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
        await fc.log_admin_action(message.from_user.id, "unmute", f"Unmuted user: {user_id} (@{user.username})")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@router.message(F.text, Command("ban"))
async def ban(bot: Bot, message: Message, command: CommandObject):
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

            await fc.log_admin_action(message.from_user.id, "ban", f"Banned user: {user_id} Reason: {reason}")
        except Exception as e:
            await message.reply(f"Не удалось забанить пользователя: {str(e)}")
    else:
        await message.reply("Эта команда должна быть использована в ответ на сообщение пользователя.")


@router.message(Command('unban'))
async def unban_user(bot: Bot, message: Message):
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
        await fc.log_admin_action(message.from_user.id, "unban", f"Unbanned user: {user_id}")
    except Exception as e:
        await message.reply(f"Не удалось разбанить пользователя. Ошибка: {str(e)}")


@router.message(F.text, Command("blacklist"))
async def add_to_blacklist(message: Message):
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
            await fc.log_admin_action(message.from_user.id, "blacklist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в черный список.")


@router.message(F.text, Command("whitelist"))
async def add_to_admin(message: Message):
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
            await fc.log_admin_action(message.from_user.id, "whitelist", f"Added word: '{word}'")
    else:
        await message.reply("Укажите слово для добавления в белый список.")


@router.message(Command("watch_patterns"))
async def watch_patterns(message: Message):
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


@router.message(F.text, Command("add_pattern"))
async def add_pattern(message: Message):
    if message.from_user.id not in config.adminsId:
        return

    pattern_text = message.text.split(maxsplit=1)
    if len(pattern_text) < 2:
        await message.reply("Пожалуйста, укажите текст паттерна рекламы после команды /add_pattern.")
        return

    new_pattern = " ".join(pattern_text[1].strip().split())
    new_pattern = fc.extract_regular_chars(new_pattern)
          
    if not new_pattern or new_pattern.isspace():
        await message.reply("Паттерн не может быть пустым или состоять только из пробелов.")
        return

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
    await fc.log_admin_action(message.from_user.id, "add_pattern", f"Added pattern: '{new_pattern}'")


@router.message(Command("remove_pattern"))
async def remove_pattern(message: Message):
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


async def clear_user_data(user_id: int, delay: int, sent_message: Message):
    await asyncio.sleep(delay)
    if user_id in user_data:
        try:
            await sent_message.delete()
        except:
            pass  # Игнорируем ошибки при удалении сообщения
        del user_data[user_id]


@router.message(F.text.regexp(r'^\d+$'))
async def process_pattern_number(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id].get('waiting_for_pattern_number'):
        return

    existing_patterns = user_data[user_id]['existing_patterns']
    pattern_number = int(message.text) - 1

    if 0 <= pattern_number < len(existing_patterns):
        user_data[user_id]['timer'].cancel()

        pattern_to_delete = existing_patterns[pattern_number]
        await delete_pattern_from_database(message, pattern_to_delete)
        await fc.log_admin_action(user_id, "remove_pattern",
                               f"Removed pattern: '{fc.regex_to_readable(pattern_to_delete)}'")

        try:
            await user_data[user_id]['sent_message'].delete()
        except:
            pass  # Игнорируем ошибки при удалении сообщения

        del user_data[user_id]
    else:
        await message.reply("Неверный номер паттерна. Пожалуйста, введите корректный номер паттерна:")


@router.callback_query(lambda c: c.data.startswith(('add:', 'cancel:')))
async def process_pattern_callback(callback_query: types.CallbackQuery):
    action, pattern_id = callback_query.data.split(':', 1)

    if pattern_id not in temp_patterns:
        await callback_query.answer("Ошибка: паттерн не найден.")
        await callback_query.message.delete()
        return

    regex_pattern, new_pattern, original_message = temp_patterns[pattern_id]

    if action == 'add':
        await add_pattern_to_database(original_message, new_pattern, regex_pattern)
        await fc.log_admin_action(callback_query.from_user.id, "add_pattern", f"Added pattern: '{new_pattern}'")
    else:  # cancel
        await fc.log_admin_action(callback_query.from_user.id, "add_pattern",
                               f"Cancelled adding pattern: '{new_pattern}'")
        await original_message.reply("Добавление паттерна отменено.")

    del temp_patterns[pattern_id]
    await callback_query.message.delete()
    await callback_query.answer()


async def add_pattern_to_database(message: Message, new_pattern: str, regex_pattern: str):
    compiled_pattern = re.compile(r'' + regex_pattern, re.IGNORECASE)
    config.ad_patterns.append(compiled_pattern)
    with open(config.AD_PATTERNS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([regex_pattern])
    await message.reply(f"Добавлен новый паттерн: {new_pattern}\nРегулярное выражение: {regex_pattern}")


async def delete_pattern_from_database(message: Message, pattern_to_delete: str):
    with open(config.AD_PATTERNS_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        patterns = list(reader)

    patterns = [pattern for pattern in patterns if pattern[0] != pattern_to_delete]

    with open(config.AD_PATTERNS_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(patterns)

    config.ad_patterns = [re.compile(r'' + pattern[0], re.IGNORECASE) for pattern in patterns]

    await message.reply(f"Паттерн '{fc.regex_to_readable(pattern_to_delete)}' успешно удален.")


@router.message(F.text, Command("change_threshold"))
async def threshold_command(message: Message):
    await message.answer("Текущее значение порога совпадений", reply_markup=get_threshold_keyboard())


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


@router.callback_query(lambda c: c.data in ['decrease', 'current', 'increase'])
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

        await fc.log_admin_action(callback_query.from_user.id, "change_threshold",
                               f"Changed from {old_threshold} to {config.MATCH_THRESHOLD}")
    except:
        pass


@router.message(Command("file_give")) 
async def cmd_give_file(message: Message):
    if message.from_user.id not in config.adminsId:
        return
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Удаленная реклама", callback_data=f"file_{config.DELETED_AD_FILE}")
    keyboard.button(text="Удаленные плохие слова", callback_data=f"file_{config.DELETED_BW_FILE}")
    keyboard.button(text="Бан лист", callback_data=f"file_{config.BAN_LIST_FILE}")
    keyboard.adjust(2)

    await message.reply("Выберите нужный файл:", reply_markup=keyboard.as_markup())


@router.callback_query(lambda c: c.data.startswith('file_'))
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
