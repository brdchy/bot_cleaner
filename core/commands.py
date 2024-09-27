from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Начало'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='mode', description='Изменить режим работы'),
        BotCommand(command='whitelist', description='Добавить слово в белый список'),
        BotCommand(command='blacklist', description='Добавить слово в черный список'),
        BotCommand(command='add_pattern', description='Добавить текст в список паттернов рекламы'),
        BotCommand(command='remove_pattern', description='Удалить паттерн рекламы из списка'),
        BotCommand(command='watch_patterns', description='Посмотреть список паттернов'),
        BotCommand(command='change_threshold', description='Изменить порог совпадений'),
        BotCommand(command='add_admin', description='Добавить пользователя в список админов'),
        BotCommand(command='remove_admin', description='Убрать админа из списка админов'),
        BotCommand(command='mute', description='Замутить пользователя'),
        BotCommand(command='unmute', description='Размутить пользователя'),
        BotCommand(command='ban', description='Забанить пользователя'),
        BotCommand(command='unban', description='Разбанить пользователя'),
        BotCommand(command='get_id', description='узнать user_id пользователя'),
        BotCommand(command='my_id', description='узнать свой user_id'),
        BotCommand(command='admin_actions', description='Просмотр последних действий админов'),
        BotCommand(command='report', description='Отправить репорт админам'),
        BotCommand(command='file_give', description='Получить файлы'),
        
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
