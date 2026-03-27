#Тут основные функции для генерации JSON-ответов.
from datetime import datetime


def get_greeting() -> str:
    """Возврат приветствия в зависимости от времени"""

    current_hour = datetime.now().hour

    if 5 <= current_hour < 12:
        return 'Доброе утро'
    elif 12 <= current_hour < 18:
        return 'Добрый день'
    elif 18 <= current_hour < 23:
        return 'Добрый вечер'
    else: 'Добро ночи'