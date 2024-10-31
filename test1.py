import core.config as config
import core.utils.functions as fc 

unique_messages = set()

# Открываем файл и считываем все строки
with open(config.DELETED_AD_FILE, "r", encoding="utf-8") as file:
    for line in file:
        if line:
            line = fc.extract_regular_chars(line.lower())
            line = fc.replace_english_letters(line)
            unique_messages.add(line)

# Преобразуем список сообщений в множество для удаления дубликатов
unique_messages_list = list(unique_messages)

# Сохраняем уникальные сообщения в новый файл
with open(config.DELETED_AD_FILE, "w", encoding="utf-8") as output_file:
    output_file.writelines(unique_messages_list)
