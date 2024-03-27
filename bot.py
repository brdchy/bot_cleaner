import asyncio
import logging
from os import name
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, ChatMemberUpdated

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token="token")
dp = Dispatcher(bot=bot)

@dp.message()
async def listen_update (message: Message):
    if message.content_type == types.ContentType.NEW_CHAT_MEMBERS:
        await message.delete()
    if message.content_type == types.ContentType.LEFT_CHAT_MEMBER:
        await message.delete()

    
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

