from rapidfuzz import fuzz
import torch
from transformers import BertTokenizer, BertConfig, BertForSequenceClassification
import logging
from safetensors.torch import load_file

import core.config as config
import core.utils.functions as fc

logging.basicConfig(level=logging.INFO)


class AdClassifier:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"Используемое устройство: {self.device}")

        try:
            # Пути к файлам
            config_path = f"{model_path}/config.json"
            model_weights_path = f"{model_path}/model.safetensors"
            vocab_path = f"{model_path}/vocab.txt"
            special_tokens_map_path = f"{model_path}/special_tokens_map.json"
            tokenizer_config_path = f"{model_path}/tokenizer_config.json"

            # Загрузка конфигурации модели
            self.config = BertConfig.from_json_file(config_path)
            logging.info(f"Конфигурация модели загружена из {config_path}")

            # Загрузка токенизатора с явным указанием файлов
            self.tokenizer = BertTokenizer(
                vocab_file=vocab_path,
                special_tokens_map_file=special_tokens_map_path,
                tokenizer_config_file=tokenizer_config_path
            )
            logging.info(f"Токенизатор загружен из {vocab_path}, {special_tokens_map_path}, {tokenizer_config_path}")

            # Создание модели
            self.model = BertForSequenceClassification(self.config).to(self.device)

            # Загрузка весов с использованием map_location
            state_dict = load_file(model_weights_path, device=self.device.type)
            self.model.load_state_dict(state_dict)
            logging.info(f"Модель загружена из {model_weights_path}")

        except Exception as e:
            logging.error(f"Ошибка загрузки модели: {e}")
            raise

    def classify(self, text):
        try:
            # Токенизация входного текста
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)

            # Предсказание
            with torch.no_grad():
                outputs = self.model(**inputs)

            probabilities = torch.nn.functional.softmax(outputs.logits, dim=1)
            predicted_class_id = torch.argmax(probabilities).item()
            confidence = probabilities[0][predicted_class_id].item()

            result = "реклама" if predicted_class_id == 1 else "нереклама"
            return result, confidence
        except Exception as e:
            logging.error(f"Ошибка классификации: {e}")
            return None, None
        

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
