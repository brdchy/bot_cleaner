import asyncio
import logging
from os import name
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.types import Message, ChatMemberUpdated

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token="TOKEN")
dp = Dispatcher()



async def listen_update (message: Message):
    chat_member_updated = message.chat_member_updated

    if chat_member_updated:  # Проверяем, является ли это системным сообщением о входе участника
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        

# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())