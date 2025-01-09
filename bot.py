import asyncio
import logging
import html
import re
import uuid
import csv
from datetime import datetime, timedelta
from multiprocessing import Process, Queue
import os

from aiogram.filters.command import Command, CommandObject
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

from core.handlers import admin, detect_message
from core.settings import BOT_TOKEN
import core.config as config
from core.utils.detect import check_ad, check_bw, AdClassifier
from core import dependencies
import core.utils.functions as fc 
from core.commands import set_commands

logging.basicConfig(level=logging.INFO)
dependencies.bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=dependencies.bot)
dp.include_routers(admin.router, detect_message.router)

admin_messages = {}
# temp_patterns = {}
# user_data = {}
message_texts = {}
action_storage = {}


async def start_bot(bot: Bot):
    await set_commands(bot)


def increment_count_report(user_id: str) -> None:
    """
    Инкрементирует счетчик репортов для определенного пользователя в файле report_counts.csv.
    Если пользователя нет в файле, добавляет его с счетчиком 1.

    Args:
        user_id: Идентификатор пользователя, оставившего репорт.
    """
    report_file = 'count_report.csv'
    updated = False
    rows = []
    try:
        with open(report_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # Пропускаем заголовок, если есть
            if header is None:
                rows.append(['id', 'count']) # Если файл пустой, добавляем заголовок
            else:
                rows.append(header)
                for row in reader:
                    if row and row[0] == user_id:
                        row[1] = str(int(row[1]) + 1)
                        updated = True
                    rows.append(row)

        if not updated:
            rows.append([user_id, '1'])

        with open(report_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

    except FileNotFoundError:
        with open(report_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['id', 'count'])
            writer.writerow([user_id, '1'])
    except Exception as e:
        print(f"Ошибка при обновлении счетчика репортов: {e}")


@dp.message(Command("report"))
async def cmd_report(message: Message):
    if not message.reply_to_message:
        error_message = await message.reply("Пожалуйста, используйте эту команду в ответ на сообщение, которое вы хотите зарепортить.")
        await asyncio.sleep(8)
        await message.delete()
        await error_message.delete()

    increment_count_report(message.from_user.id)

    text_id = str(uuid.uuid4())[:8]
    message_text = message.reply_to_message.text or message.reply_to_message.caption
    message_texts[text_id] = message_text

    # Отправляем репорт админам и сохраняем ID сообщения с подтверждением
    await send_report_to_admins(dependencies.bot, message.reply_to_message, message, text_id)

    confirmation_message = await message.reply("Спасибо за ваш репорт. Администраторы рассмотрят его в ближайшее время.")

    # Удаляем сообщение с командой /report
    await asyncio.sleep(8)
    await message.delete()
    await confirmation_message.delete()


async def send_report_to_admins(bot: Bot, reported_message: Message, reporter_message: Message, text_id: str): 
    text_to_check = reported_message.text or reported_message.caption
    text_to_check = " ".join(text_to_check.split())
    text_to_check = fc.extract_regular_chars(text_to_check.lower())
    text_to_check = fc.replace_english_letters(text_to_check)

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

        increment_count_admin_action(callback_query.from_user.id)

        message_text = message_texts.get(text_id, "")
        await fc.log_admin_action(callback_query.from_user.id, "skip reported message", f"Skipped message: '{message_text}'")
        if text_id:
            del message_texts[text_id]
        
        # Удаление сообщений с репортом у всех админов
        if message_id in admin_messages:
            for admin, admin_message_id in admin_messages[message_id]['admins'].items():
                try:
                    await dependencies.bot.delete_message(admin, admin_message_id)
                except Exception as e:
                    print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")

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
                    if row and row[0] == admin_id:
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


@dp.callback_query(lambda c: c.data.startswith(('report-delete_', 'report-mute_', 'report-ban_')))
async def process_report_callback(callback_query: types.CallbackQuery):
    action, reason, action_id = callback_query.data.split('_')

    report_data = action_storage[action_id]
    chat_id = report_data['chat_id']
    message_id = report_data['message_id']
    user_id = report_data['user_id']
    text_id = report_data['text_id']

    increment_count_admin_action(callback_query.from_user.id)

    try:
        await dependencies.bot.delete_message(chat_id, message_id)

        message_text = message_texts.get(text_id, "")
        await fc.log_admin_action(callback_query.from_user.id, f"delete reported {reason}_message ", f"Deleted message: '{message_text}'")
    except TelegramBadRequest as e:
        if "message to delete not found" in str(e):
            await callback_query.answer("Сообщение уже было удалено", show_alert=True)
        else:
            await callback_query.answer(f"Не удалось удалить исходное сообщение: {str(e)}", show_alert=True)
    
    try:
        await fc.write_ad_file(message_text)
    except:
        pass
    
    await fc.increment_violation_count(user_id, reason, message_text)

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

                await dependencies.bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False), until_date=duration)
                await callback_query.answer("Пользователь замучен на 300 секунд.")
                await fc.log_admin_action(callback_query.from_user.id, "mute reported user", f"Muted user: {user_id}")
            elif action == 'report-ban':
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

                await fc.log_admin_action(callback_query.from_user.id, "ban reported user", f"Banned user: {user_id}")
    except Exception as e:
        await callback_query.message.answer(f"Не удалось выполнить действие: {str(e)}", show_alert=True)

    # Удаление сообщений с репортом у всех админов
    if message_id in admin_messages:
        for admin, admin_message_id in admin_messages[message_id]['admins'].items():
            try:
                await dependencies.bot.delete_message(admin, admin_message_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение у админа {admin}: {str(e)}")


# Функция для запуска процесса классификации
def classify_process(model_path, input_queue, output_queue):
    classifier = AdClassifier(model_path)
    while True:
        text = input_queue.get()
        if text is None:
            pass
        result, confidence = classifier.classify(text)
        output_queue.put((result, confidence))


# # Функция для остановки процесса классификации при остановке бота
# async def on_shutdown(dispatcher: Dispatcher):
#     classify_queue.put(None)  # Отправляем сигнал завершения процессу
#     classify_process_instance.join()
#     for admin in config.adminsId:
#         try:
#             await bot.send_message(chat_id=admin, text='Бот остановлен')
#         except:
#             pass


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


async def schedule_delete_old_records():
    while True:
        await delete_old_records()
        await asyncio.sleep(24 * 60 * 60)


async def main(bot: Bot):
    global classify_process_instance
    model_path = "models/ruBERT-large-finetuned"
    classify_process_instance = Process(target=classify_process, args=(model_path, dependencies.classify_queue, dependencies.result_queue), daemon=True)
    classify_process_instance.start()

    for admin in config.adminsId:
        try:
            await bot.send_message(chat_id=admin, text='Бот запущен')
        except:
            pass

    asyncio.create_task(schedule_delete_old_records())
    dp.startup.register(start_bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main(dependencies.bot))
