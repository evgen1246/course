import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from src.views import get_greeting, get_card_spending, get_top_transactions, get_financial_data, \
    load_transactions_from_file


def main(datetime_str: str, transactions: List[Dict] = None, transactions_file: str = None) -> str:
    """
    Главная функция, принимающая строку с датой и временем в формате YYYY-MM-DD HH:MM:SS
    и возвращающая JSON-ответ с данными для виджета."""

    try:
        if transactions is None:
            if transactions_file:
                transactions = load_transactions_from_file(transactions_file)
            else:
                # Пробуем загрузить из папки data
                data_file = Path("data/operations.json")
                if data_file.exists():
                    transactions = load_transactions_from_file(str(data_file))
                else:
                    print('Транзакции не переданы и файл не найден, использую пустой список')
                    transactions = []
        input_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        # logger.debug(f"Успешный парсинг даты: {input_datetime}")

        # Приветствие
        greeting = get_greeting()
        # logger.info(f"Приветствие: {greeting}")

        cards = get_card_spending(transactions)
        # logger.info(f"Получена статистика по {len(cards)} картам")

        top_transactions = get_top_transactions(transactions, limit=5)
        # logger.info(f"Получено топ-{len(top_transactions)} транзакций")

        financial_data = get_financial_data()
        #  logger.info("Получены финансовые данные")

        response = {'greeting': greeting,
                    'cards': cards,
                    'top_transactions': top_transactions,
                    'currency_rates': financial_data.get('currency_rates', []),
                    'stock_prices': financial_data.get('stock_prices', [])
                    }
        # logger.info("JSON-ответ успешно сформирован")
        return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError as e:
        # logger.error(f"Ошибка парсинга даты '{datetime_str}': {e}")
        error_response = {
            'error': f'Неверный формат даты. Ожидается YYYY-MM-DD HH:MM:SS, получено: {datetime_str}',
            'timestamp': datetime_str
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


