import asyncio
import logging
from os import name

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram import F

from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

import re

from settings import BOT_TOKEN


async def main():
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO)

    # Объект бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot=bot)

    @dp.message(F.new_chat_members)
    async def handle_channel_post(message: types.Message):
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    @dp.message(F.left_chat_member)
    async def handle_channel_post(message: types.Message):
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    bad_words = []

    with open("bad_words.txt", "r", encoding='utf-8') as f:
        bad_words = f.readlines()
        bad_words = [word.replace("\n", "").strip() for word in bad_words]


    def replace_english_letters(text):
        replacements = {
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
    
    def replace_english_two_char(text):
        replacements = {
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
        'z': 'з',
        'ch': 'ч'
        }

        # print("SRC", [ord(text[i]) for i in range(len(text))])

        for eng, rus in replacements.items():
            text = text.replace(eng, rus)

        # print("NEW", [ord(text[i]) for i in range(len(text))])

        return text


    def is_bad_word(source: list, dist: str):
        current_percent = 85

        for word in source:
            ratio = fuzz.ratio(dist, word)

            if word == dist:
                return True
            
            if ratio > current_percent:
                
                return True
            
        return False


    def extract_regular_chars(text):
        regular_chars = re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)

        return regular_chars


    def check_message(message):
        message_text = extract_regular_chars(message.lower())
            # replace_english_letters(message_text)
        message_text = message_text.replace('\n', ' ')
        # print("hello")

        flag = False

        for word in message_text.split(' '):
            translit_word = replace_english_letters(word)

            is_bad = is_bad_word(bad_words, translit_word)

            #print("DEBUG:", word, translit_word, is_bad)
            
            if is_bad:
                flag = True
        return flag
    
    @dp.message(F.text)
    async def delete_bad_words(message: types.Message):
        if check_message(message.text):
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    try:
        await dp.start_polling(bot)

    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())