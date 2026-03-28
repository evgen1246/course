# Тут основные функции для генерации JSON-ответов.
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from black.trans import defaultdict
from dotenv import load_dotenv

load_dotenv()


def transaction_convert(transaction: Dict) -> float:
    """Конвертирует сумму транзакции в рубли"""
    amount = float(transaction.get("operationAmount", {}).get("amount", 0))
    currency = transaction.get("operationAmount", {}).get("currency", {}).get("code" "RUB")

    if currency == "RUB":
        return amount
    else:
        url = f"https://api.apilayer.com/exchangerates_data/convert?to=RUB&from={currency}&amount={amount}"
        headers = {"apikey": os.getenv("TOKEN")}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return float(response.json()["result"])
        else:
            return amount


def get_greeting() -> str:
    """Возврат приветствия в зависимости от времени"""

    current_hour = datetime.now().hour

    if 5 <= current_hour < 12:
        return "Доброе утро"
    elif 12 <= current_hour < 18:
        return "Добрый день"
    elif 18 <= current_hour < 23:
        return "Добрый вечер"
    else:
        "Добро ночи"


def get_card_spending(transactions: List[Dict]) -> List[Dict]:
    """
    Принимает список словарей, возвращает:
    -последние 4 цифры карты,
    -общую сумму расходов,
    -кешбэк (1 рубль на каждые 100 рублей)
    """

    card_stat = defaultdict(lambda: {"total_spend": 0.0, "last_digits": ""})
    for transaction in transactions:
        amount_rub = transaction_convert(transaction)
        if amount_rub < 0:
            continue
        # Получаем информацию о карте из поля 'from'
        card_info = transaction.get("from", "")

        if "Счет" in card_info:
            continue

        card_numbers = re.findall(r"\d+", card_info)

        if card_numbers:
            card_number = card_numbers[-1]
            if len(card_number) >= 4:
                last_digits = card_number[-4:]
            else:
                last_digits = card_number
        else:
            continue

        if not card_stat[last_digits]["last_digits"]:
            card_stat[last_digits]["last_digits"] = last_digits

        card_stat[last_digits]["total_spent"] += amount_rub

    #   Результаты:

    result = []
    for last_digits, stats in card_stat.items():
        total_spend = stats["total_spent"]

        result.append({"last_digits": last_digits, "total_spend": total_spend, "cashback": (total_spend / 100, 2)})
    return result


# Категории:


def determine_category(description: str) -> str:
    """Определяет категорию транзакции на основе описания"""
    description_lower = description.lower()

    categories = {
        "Супермаркеты": ["пятерочка", "перекресток", "магнит", "лента", "супермаркет", "магазин"],
        "Фастфуд": ["макдоналдс", "kfc", "бургер", "фастфуд"],
        "Топливо": ["азс", "заправка", "топливо", "лукойл", "газпром"],
        "Развлечения": ["кино", "театр", "кафе", "ресторан"],
        "Медицина": ["аптека", "лекарство", "врач", "клиника"],
        "Переводы": ["перевод", "перевести"],
        "ЖКХ": ["жку", "квартплата", "коммунальные", "жкх"],
        "Различные товары": ["ozon", "wildberries", "яндекс маркет", "интернет-магазин"],
        "Бонусы": ["кэшбэк", "кешбэк", "бонус", "cashback"],
        "Наличные": ["наличные", "снятие"],
        "Связь": ["мтс", "билайн", "мегафон", "теле2", "интернет"],
        "Транспорт": ["такси", "метро", "автобус", "uber", "яндекс такси"],
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category

    return "Прочее"


# Топ 5 транзакций:


def get_top_transactions(transactions: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Возвращает топ транзакций по сумме, по умолчанию 5.
    """

    expenditure_transactions = []
    for transaction in transactions:
        amount_rub = transaction_convert(transaction)

        category = transaction.get("category", "")
        if not category:
            category = determine_category(transaction.get("category", ""))
        # Формат дат
        date_str = transaction.get("date", "")
        try:
            if "T" in date_str:
                date_object = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                formatted_date = date_object.strftime("%d.%m.%Y")
            else:
                date_object = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                formatted_date = date_object.strftime("%d.%m.%Y")

        except ValueError:
            formatted_date = date_str[:10].replace("-", ".")

        expenditure_transactions.append(
            {
                "date": formatted_date,
                "amount": round(amount_rub, 2),
                "category": category,
                "description": transaction.get("description", ""),
                "original_amount": amount_rub,
            }
        )

    # Сортировка:

    sorted_transactions = sorted(expenditure_transactions, key=lambda x: abs(x["original_amount"]), reverse=True)

    # Возврат топа:
    top_transactions = []
    for transaction in sorted_transactions[:limit]:
        top_transactions.append(
            {
                "date": transaction["date"],
                "amount": transaction["amount"],
                "category": transaction["category"],
                "description": transaction["description"],
            }
        )

    return top_transactions


# Получение курса валют ЦБ:
def get_financial_data() -> Dict:
    """
    Получает курсы валют и цены акций на основе настроек пользователя
    Возвращает: словарь с курсами валют и ценами акций
    """
    settings_file = Path("user_settings.json")

    # Проверяем, существует ли файл настроек
    if not settings_file.exists():
        # Если файла нет, создаем с настройками по умолчанию
        default_settings = {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)
        print(f"Создан файл {settings_file} с настройками по умолчанию")
        settings = default_settings
    else:
        # Загружаем существующий файл
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        print(f"Загружены настройки из {settings_file}")

    # Получаем списки валют и акций из настроек
    user_currencies = settings.get("user_currencies", ["USD", "EUR"])
    user_stocks = settings.get("user_stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])

    print(f"Валюты для загрузки: {user_currencies}")
    print(f"Акции для загрузки: {user_stocks}")
    print("💰 Получение курсов валют...")

    currency_rates = []
    try:
        # Используем API Центрального Банка России
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Курсы на случай ошибки API
        fallback_rates = {"USD": 92.50, "EUR": 100.20, "GBP": 115.30, "CNY": 12.80}

        for currency in user_currencies:
            if currency in data.get("Valute", {}):
                rate = data["Valute"][currency]["Value"]
                currency_rates.append({"currency": currency, "rate": round(rate, 2)})
                print(f"{currency}: {rate:.2f} RUB")
            else:
                # Если валюта не найдена в API, используем fallback_rates
                print(f"Валюта {currency} не найдена в API, использую fallback курс")
                rate = fallback_rates.get(currency, 100.0)
                currency_rates.append({"currency": currency, "rate": rate})

    except Exception as e:
        print(f"Ошибка получения курсов валют: {e}")
        # Используем fallback_rates курсы
        fallback_rates = {"USD": 92.50, "EUR": 100.20}
        for currency in user_currencies:
            rate = fallback_rates.get(currency, 100.0)
            currency_rates.append({"currency": currency, "rate": rate})
            print(f"Использую fallback курс для {currency}: {rate:.2f} RUB")

    print("📈 Получение цен акций...")

    stock_prices = []

    # Получаем API ключ из переменных окружения
    api_key = os.getenv("API_KEY_STOCKS")

    if not api_key:
        print("API ключ для акций не найден в .env файле")
        print("Получите бесплатный ключ на https://www.alphavantage.co/support/#api-key")
        print("Создайте файл .env с содержимым: API_KEY_STOCKS=ваш_ключ")

        # Используем fallback цены
        fallback_prices = {
            "AAPL": 150.12,
            "AMZN": 3173.18,
            "GOOGL": 2742.39,
            "MSFT": 296.71,
            "TSLA": 1007.08,
            "META": 310.20,
        }

        for symbol in user_stocks:
            price = fallback_prices.get(symbol, 100.0)
            stock_prices.append({"stock": symbol, "price": price})
            print(f"⚠️ {symbol}: Использую fallback цену ${price:.2f}")
    else:
        # Получаем цены через API
        for symbol in user_stocks:
            try:
                print(f"  Загрузка {symbol}...", end=" ")

                url = "https://www.alphavantage.co/query"
                params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "apikey": api_key}

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                # Проверяем на ошибки API
                if "Error Message" in data:
                    print(f'Ошибка: {data["Error Message"]}')
                    # Используем fallback цену
                    fallback_prices = {
                        "AAPL": 150.12,
                        "AMZN": 3173.18,
                        "GOOGL": 2742.39,
                        "MSFT": 296.71,
                        "TSLA": 1007.08,
                    }
                    price = fallback_prices.get(symbol, 100.0)
                    stock_prices.append({"stock": symbol, "price": price})
                    continue

                if "Information" in data:
                    print(f'{data["Information"][:80]}...')
                    fallback_prices = {
                        "AAPL": 150.12,
                        "AMZN": 3173.18,
                        "GOOGL": 2742.39,
                        "MSFT": 296.71,
                        "TSLA": 1007.08,
                    }
                    price = fallback_prices.get(symbol, 100.0)
                    stock_prices.append({"stock": symbol, "price": price})
                    continue

                # Извлекаем цену
                if "Time Series (Daily)" in data:
                    time_series = data["Time Series (Daily)"]

                    if time_series:
                        # Берем самый свежий день
                        latest_date = max(time_series.keys())
                        latest_data = time_series[latest_date]
                        price = float(latest_data.get("4. close", 0))

                        if price > 0:
                            stock_prices.append({"stock": symbol, "price": round(price, 2)})
                            print(f"${price:.2f} ({latest_date})")
                        else:
                            print('Цена не получена, использую fallback')
                            fallback_prices = {
                                "AAPL": 150.12,
                                "AMZN": 3173.18,
                                "GOOGL": 2742.39,
                                "MSFT": 296.71,
                                "TSLA": 1007.08,
                            }
                            price = fallback_prices.get(symbol, 100.0)
                            stock_prices.append({"stock": symbol, "price": price})
                    else:
                        print('Нет данных, использую fallback')
                        fallback_prices = {
                            "AAPL": 150.12,
                            "AMZN": 3173.18,
                            "GOOGL": 2742.39,
                            "MSFT": 296.71,
                            "TSLA": 1007.08,
                        }
                        price = fallback_prices.get(symbol, 100.0)
                        stock_prices.append({"stock": symbol, "price": price})
                else:
                    print('Неожиданный формат, использую fallback')
                    fallback_prices = {
                        "AAPL": 150.12,
                        "AMZN": 3173.18,
                        "GOOGL": 2742.39,
                        "MSFT": 296.71,
                        "TSLA": 1007.08,
                    }
                    price = fallback_prices.get(symbol, 100.0)
                    stock_prices.append({"stock": symbol, "price": price})

            except requests.Timeout:
                print('Таймаут, использую fallback цену')
                fallback_prices = {"AAPL": 150.12, "AMZN": 3173.18, "GOOGL": 2742.39, "MSFT": 296.71, "TSLA": 1007.08}
                price = fallback_prices.get(symbol, 100.0)
                stock_prices.append({"stock": symbol, "price": price})

            except Exception as e:
                print(f"Ошибка: {e}")
                fallback_prices = {"AAPL": 150.12, "AMZN": 3173.18, "GOOGL": 2742.39, "MSFT": 296.71, "TSLA": 1007.08}
                price = fallback_prices.get(symbol, 100.0)
                stock_prices.append({"stock": symbol, "price": price})

    result = {"currency_rates": currency_rates, "stock_prices": stock_prices}

    return result


if __name__ == "__main__":
    financial_data = get_financial_data()
