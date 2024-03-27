import asyncio
import logging
from os import name
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, ChatMemberUpdated
from rapidfuzz.distance.DamerauLevenshtein import normalized_similarity
from difflib import SequenceMatcher

import re

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token="6787628808:AAGjwFLcNnoWiJJJUmz3kUUwFkWDKrHpQuo")
dp = Dispatcher(bot=bot)

@dp.message()
async def listen_update (message: Message):

    print(message.text)
    try:
        if message.content_type == types.ContentType.NEW_CHAT_MEMBERS:
            await message.delete()
        elif message.content_type == types.ContentType.LEFT_CHAT_MEMBER:
            await message.delete()
        else:
            if check_message(message.text):
                await message.delete()
    except Exception as e:
        print(e)
    

bad_words = []

with open("bad_words.txt", "r", encoding='utf-8') as f:
    bad_words = f.readlines()
    bad_words = [word.replace("\n", "").strip() for word in bad_words]


def replace_english_letters(text):
    replacements = {
        'a': 'а',
        'b': 'в',
        'e': 'е',
        'k': 'к',
        'm': 'м',
        'h': 'н',
        'o': 'о',
        'p': 'р',
        'c': 'с',
        't': 'т',
        'y': 'у',
        'x': 'х'
    }

    print("SRC", [ord(text[i]) for i in range(len(text))])

    for eng, rus in replacements.items():
        text = text.replace(eng, rus)

    print("NEW", [ord(text[i]) for i in range(len(text))])

    return text


def similar(a, b):    
    return SequenceMatcher(None, a, b).ratio()

def is_bad_word(source: list, dist: str):
    current_percent = 85

    for word in source:
        #ratio = similar(dist, word)
        if word == dist:
            return True
    return False


def extract_regular_chars(text):
    regular_chars = re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)

    return regular_chars


def check_message(message):
    message_text = extract_regular_chars(message.lower())

    print("hello")

    flag = False

    for word in message_text.split(' '):
        translit_word = replace_english_letters(word)

        is_bad = is_bad_word(bad_words, translit_word)

        print("DEBUG:", word, translit_word, is_bad)
        
        if is_bad:
            flag = True
    return flag

    


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())




