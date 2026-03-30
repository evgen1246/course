import re
import json
import logging
from datetime import datetime
from src.views import determine_category, transaction_convert
from typing import Dict, List


logging.basicConfig(level = logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('app.log', encoding='utf8'),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)


def format_transaction_date(date_str: str) -> str:
    """
    Форматирует дату транзакции в формат DD.MM.YYYY
    """
    if not date_str:
        return ""

    try:
        # ISO формат с T: 2024-01-15T14:30:00Z
        if 'T' in date_str:
            # Удаляем Z и временную зону для корректного парсинга
            clean_date = date_str.replace('Z', '+00:00')
            date_object = datetime.fromisoformat(clean_date)
            return date_object.strftime('%d.%m.%Y')

        # Формат с пробелом: 2024-01-15 14:30:00
        elif ' ' in date_str and '-' in date_str:
            date_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return date_object.strftime('%d.%m.%Y')

        # Формат только даты: 2024-01-15
        elif '-' in date_str and len(date_str) == 10:
            date_object = datetime.strptime(date_str, '%Y-%m-%d')
            return date_object.strftime('%d.%m.%Y')

        # Если формат не распознан
        else:
            logger.warning(f"Неизвестный формат даты: '{date_str}'")
            return date_str

    except (ValueError, AttributeError) as e:
        logger.warning(f"Ошибка парсинга даты '{date_str}': {e}")
        return date_str


def get_transfers_to_individuals(transactions: List[Dict]) -> List[Dict]:
    """
    Возвращает список транзакций, которые относятся к переводам физическим лицам.
    """
    if not transactions:
        logger.info("Список транзакций пуст")
        return []

    logger.info(f"Поиск переводов физическим лицам среди {len(transactions)} транзакций")

    # Регулярное выражение для поиска имени и первой буквы фамилии с точкой
    # Паттерн: русское имя с заглавной буквы, пробел, заглавная буква, точка
    pattern = r'[А-Я][а-я]+\s[А-Я]\.'

    transfers = []

    for transaction in transactions:
        # Получаем категорию транзакции
        category = transaction.get('category', '')
        if not category:
            # Если категория не указана, определяем её
            description = transaction.get('description', '')
            category = determine_category(description)

        # Проверяем, что категория - "Переводы"
        if category != "Переводы":
            continue

        # Получаем описание транзакции
        description = transaction.get('description', '')

        # Ищем в описании имя и фамилию с точкой
        match = re.search(pattern, description)

        if match:
            # Форматируем дату
            date_str = transaction.get('date', '')
            formatted_date = format_transaction_date(date_str)

            # Извлекаем имя получателя
            recipient_name = match.group()

            transfers.append({
                'date': formatted_date,
                'amount': transaction_convert(transaction),
                'category': category,
                'description': description,
                'recipient': recipient_name
            })
            logger.debug(f"Найден перевод физическому лицу: {recipient_name}")

    logger.info(f"Найдено {len(transfers)} переводов физическим лицам")
    return transfers


def get_transfers_to_individuals_json(transactions: List[Dict]) -> str:
    """
    Возвращает JSON-ответ со всеми переводами физическим лицам.
    """

    try:
        transfers = get_transfers_to_individuals(transactions)

        response = {
            "count": len(transfers),
            "transfers": transfers
        }

        logger.info(f"Сформирован JSON-ответ с {len(transfers)} переводами")
        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при формировании JSON-ответа: {e}", exc_info=True)
        error_response = {
            "error": str(e),
            "count": 0,
            "transfers": []
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)