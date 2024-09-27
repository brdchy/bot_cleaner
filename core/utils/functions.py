import re
from difflib import SequenceMatcher


def extract_regular_chars(text):
    return re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)


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
        'j': 'ж',
        'k': 'к',
        'l': 'л',
        'm': 'м',
        'n': 'н',
        'o': 'о',
        'p': 'п',
        'q': 'к',
        'r': 'г',
        's': 'с',
        't': 'т',
        'u': 'и',
        'v': 'в',
        'w': 'ш',
        'x': 'х',
        'y': 'у',
        'z': 'з'
    }
    for eng, rus in replacements.items():
        text = text.replace(eng, rus)
    return text


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


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
        'н': '[н]',
        'о': '[оo0]',
        'п': '[пnh]',
        'р': '[pр]',
        'с': '[cс]',
        'т': '[тt]',
        'у': '[уy]',
        'ф': '[ф]',
        'х': '[xх]',
        'ц': '[ц]',
        'ч': '[ч4]',
        'ш': '[шwщ]',
        'щ': '[шwщ]',
        'ъ': '[ъ]',
        'ы': '[ы]',
        'ь': '[ь]',
        'э': '[зz3э]',
        'ю': '[ю]',
        'я': '[я]',

        'a': '[aа@]',
        'b': '[bб6]',
        'c': '[cс]',
        'd': '[дd]',
        'e': '[eе3]',
        'g': '[жg]',
        'h': '[пnh]',
        'u': '[иeеu]',
        'o': '[оo0]',
        'w': '[шwщ]',
        'k': '[кk]',
        't': '[тt]',
        'm': '[мm]',
        'v': '[вbv]',
        'y': '[уy]',
        'r': '[гr]',
        'x': '[xх]',
        'n': '[н]',
        'p': '[pр]',
        '6': '[bб6]',
        '3': '[зz3э]',
        '0': '[оo0]',
        '4': '[ч4]'
    }
    return ''.join(letter_to_regex.get(char, re.escape(char)) if char != ' ' else r'\s*'
                   for char in input_string.lower())


def regex_to_readable(regex_pattern):
    readable_dict = {
        '[aа@]': 'а',
        '[bб6]': 'б',
        '[вbv]': 'в',
        '[гr]': 'г',
        '[дd]': 'д',
        '[eе3]': 'е',
        '[ёeе]': 'ё',
        '[жg]': 'ж',
        '[зz3э]': 'з',
        '[иeеu]': 'и',
        '[йuи]': 'й',
        '[кk]': 'к',
        '[лl]': 'л',
        '[мm]': 'м',
        '[пnh]': 'п',
        '[н]': 'н',
        '[оo0]': 'о',
        '[pр]': 'р',
        '[cс]': 'с',
        '[тt]': 'т',
        '[уy]': 'у',
        '[ф]': 'ф',
        '[xх]': 'х',
        '[ц]': 'ц',
        '[ч4]': 'ч',
        '[шwщ]': 'ш',
        '[ъ]': 'ъ',
        '[ы]': 'ы',
        '[ь]': 'ь',
        '[ю]': 'ю',
        '[я]': 'я', r'\s*': ' '
    }
    for regex, char in readable_dict.items():
        regex_pattern = regex_pattern.replace(regex, char)
    return regex_pattern
