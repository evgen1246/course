import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.views import (get_card_spending, get_financial_data, get_greeting, get_top_transactions,
                       load_transactions_from_file)


def main(datetime_str: str, transactions: Optional[List[Dict]] = None, transactions_file: Optional[str] = None) -> str:
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
                    print("Транзакции не переданы и файл не найден, использую пустой список")
                    transactions = []
        datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # Приветствие
        greeting = get_greeting()

        cards = get_card_spending(transactions)

        top_transactions = get_top_transactions(transactions, limit=5)

        financial_data = get_financial_data()

        response = {
            "greeting": greeting,
            "cards": cards,
            "top_transactions": top_transactions,
            "currency_rates": financial_data.get("currency_rates", []),
            "stock_prices": financial_data.get("stock_prices", []),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError:

        error_response = {
            "error": f"Неверный формат даты. Ожидается YYYY-MM-DD HH:MM:SS, получено: {datetime_str}",
            "timestamp": datetime_str,
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
