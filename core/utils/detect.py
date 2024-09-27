from rapidfuzz import fuzz

import core.config as config
import core.utils.functions as fc


def is_bad_word(source: list, dist: str):
    if dist in config.white_list:
        return False
    for word in source:
        if word == dist or fuzz.ratio(dist, word) > 85:
            return True
    return False


def count_ad_matches(text):
    return sum(1 for pattern in config.ad_patterns if pattern.search(text))


def check_bw(message):
    if message is None:
        return []

    message_text = fc.extract_regular_chars(message.lower())
    found_words = set()

    # Проверка слов с пробелами
    words = message_text.split()
    for word in words:
        normalized_word = fc.replace_english_letters(word)
        if is_bad_word(config.bad_words, normalized_word):
            found_words.add(word)

    return list(found_words)


def check_ad(message):
    message = fc.extract_regular_chars(message.lower())
    matches = [fc.regex_to_readable(pattern.pattern) for pattern in config.ad_patterns if pattern.search(message)]
    # print(f'\n{message}\n')
    # print(f'Количество совпадений: {count_ad_matches(message)}')
    return matches, len(matches) >= config.MATCH_THRESHOLD
