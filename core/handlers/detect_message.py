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
from core.utils.detect import check_ad, check_bw, AdClassifier
from aiogram.types import FSInputFile

import core.config as config
import core.utils.detect as detect
import core.utils.functions as fc 
from core import dependencies

router = Router()

admin_messages = {}
message_texts = {}
action_storage = {}


@router.message()
async def work(message: Message):
    global is_delete_bw
    global is_delete_ad

    try:
        chat_member = await dependencies.bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ["administrator", "creator"] or message.from_user.id in config.white_list_users:
            return
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")

    print(f"dependencies.is_delete_bw: {dependencies.is_delete_bw}")
    print(f"dependencies.is_delete_ad: {dependencies.is_delete_ad}")

    text_to_check = message.text or message.caption

    if text_to_check:
        text_to_check = " ".join(text_to_check.split())
        text_to_check = fc.extract_regular_chars(text_to_check.lower())
        text_to_check = fc.replace_english_letters(text_to_check)

        if text_to_check in config.delete_list:
            try:
                await message.delete()
                return
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
                return

        bad_words_found = check_bw(text_to_check)
        ad_patterns_found, is_ad = check_ad(text_to_check)

        # Отправляем текст на классификацию BERT
        dependencies.classify_queue.put(text_to_check)

        # Ожидаем результат от процесса классификации (можно добавить таймаут)
        try:
            bert_result, bert_confidence = await asyncio.get_running_loop().run_in_executor(None, dependencies.result_queue.get)
            is_ad_bert = (bert_result == "реклама")
            logging.info(f"BERT Classification: Text='{text_to_check[:50]}...', Result='{bert_result}', Confidence={bert_confidence:.4f}")
        except Exception as e:
            logging.error(f"Ошибка при получении результата от BERT: {e}")
            is_ad_bert = False # В случае ошибки считаем, что не реклама
            bert_confidence = 0.0 # Устанавливаем уверенность в 0

        if bad_words_found:
            if dependencies.is_delete_bw:
                with open(config.DELETED_BW_FILE, "a", encoding='utf-8') as f:
                    f.write(text_to_check + "\n")

                await fc.increment_violation_count(message.from_user.id, "bw", text_to_check)

                return await message.delete()
            else:
                return await notify_admins(message, "сообщение с плохим словом", text_to_check, bad_words_found)
        elif is_ad:
            if dependencies.is_delete_ad:
                await fc.write_ad_file(text_to_check)

                await fc.increment_violation_count(message.from_user.id, "ad", text_to_check)

                return await message.delete()
            else:
                return await notify_admins(message, "рекламное сообщение", text_to_check, ad_patterns_found)
        elif is_ad_bert:
            if bert_confidence >= config.BERT_CONFIDENCE_THRESHOLD:
                return await notify_admins(message, "рекламное сообщение", text_to_check, ad_patterns_found)


async def notify_admins(message: Message, reason: str, message_text, triggers): 
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

        sent_message = await dependencies.bot.send_message(admin, admin_message, reply_markup=keyboard.as_markup())
        admin_messages[message.message_id][admin] = sent_message.message_id


def increment_count_admin_action(admin_id: str) -> None:
    """
    Инкрементирует счетчик действий администратора в файле admin_action_counts.csv.
    Если администратора нет в файле, добавляет его с счетчиком 1.

    Args:
        admin_id: Идентификатор администратора, совершившего действие.
    """
    action_file = 'count_admin_action.csv'
    updated = False
    rows = []
    try:
        with open(action_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None) # Пропускаем заголовок, если есть
            if header is None:
                rows.append(['id', 'count']) # Если файл пустой, добавляем заголовок
            else:
                rows.append(header)
                for row in reader:
                    if row and int(row[0]) == admin_id:
                        row[1] = str(int(row[1]) + 1)
                        updated = True
                    rows.append(row)

        if not updated:
            rows.append([admin_id, '1'])

        with open(action_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

    except FileNotFoundError:
        with open(action_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['id', 'count'])
            writer.writerow([admin_id, '1'])
    except Exception as e:
        print(f"Ошибка при обновлении счетчика действий админа: {e}")
        

@router.callback_query(lambda c: c.data.startswith(('delete_', 'mute_', 'ban_', 'skip_'))) 
async def process_callback(callback_query: types.CallbackQuery):
    action, action_id = callback_query.data.split('_')

    action_data = action_storage[action_id]

    chat_id = action_data['chat_id']
    message_id = action_data['message_id']
    user_id = action_data['user_id']
    text_id = action_data['text_id']
    reason = action_data['reason']

    message_text = message_texts.get(text_id, "")

    increment_count_admin_action(callback_query.from_user.id)

    if action != 'skip':
        try:
            await dependencies.bot.delete_message(chat_id, message_id)

            if message_text in config.bad_words or message_text in config.delete_list:
                pass
            else:
                with open(config.DELETE_LIST_FILE, "a", newline='', encoding='utf-8') as f:
                    f.write(message_text + "\n")
                config.delete_list.append(message_text)

            await fc.increment_violation_count(user_id, reason, message_text)

            del message_texts[text_id]

            await fc.log_admin_action(callback_query.from_user.id, "delete message", f"Deleted message: '{message_text}'")
        except Exception as e:
            await callback_query.message.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)

    try:
        if action == 'delete':
            await callback_query.answer("Сообщение удалено.")
        elif action in ['mute', 'ban']:
            if action == 'mute':
                duration = 300
                await dependencies.bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False), until_date=duration)
                await callback_query.answer("Пользователь замучен на 300 секунд.")
                await fc.log_admin_action(callback_query.from_user.id, "mute user", f"Muted user: {user_id}")
            elif action == 'ban':
                # with open(config.BAN_LIST_FILE, "a", encoding='utf-8') as f:
                #     f.write(user_id + "\n")
                await dependencies.bot.ban_chat_member(chat_id, user_id)
                await callback_query.answer("Пользователь забанен.")

                try:
                    user = await dependencies.bot.get_chat(user_id)
                    username = user.username or "Unknown"
                except:
                    username = "Unknown"

                with open(config.BAN_LIST_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([user_id, username])

                await fc.log_admin_action(callback_query.from_user.id, "ban user", f"Banned user: {user_id}")
        elif action == 'skip':
            await callback_query.answer("Сообщение пропущено.")
            await fc.log_admin_action(callback_query.from_user.id, "skip message", f"Skipped message: '{message_text}'")

            del message_texts[text_id]
    except Exception as e:
        await callback_query.message.answer(f"Не удалось выполнить действие: {str(e)}", show_alert=True)

    if message_id in admin_messages:
        for admin, admin_message_id in admin_messages[message_id].items():
            try:
                await dependencies.bot.delete_message(admin, admin_message_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")
        del admin_messages[message_id]
