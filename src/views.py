# Тут основные функции для генерации JSON-ответов.
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from collections import defaultdict
from dotenv import load_dotenv


logging.basicConfig(level = logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('app.log', encoding='utf8'),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)
load_dotenv()


def transaction_convert(transaction: Dict) -> float:
    """Конвертирует сумму транзакции в рубли"""
    try:
        amount = float(transaction.get("operationAmount", {}).get("amount", 0))
        currency = transaction.get("operationAmount", {}).get("currency", {}).get("code", "RUB")

        logger.debug(f"Конвертация: {amount} {currency}")

        if currency == "RUB":
            logger.debug(f"Сумма уже в рублях: {amount}")
            return amount
        else:
            url = f"https://api.apilayer.com/exchangerates_data/convert?to=RUB&from={currency}&amount={amount}"
            headers = {"apikey": os.getenv("TOKEN")}

            logger.info(f"Запрос конвертации {amount} {currency} в RUB")
            currency_response = requests.get(url, headers=headers)

            if currency_response.status_code == 200:
                result = float(currency_response.json()["result"])
                logger.info(f"Успешная конвертация: {amount} {currency} = {result} RUB")
                return result
            else:
                logger.warning(f"Ошибка конвертации, статус {currency_response.status_code}. Возвращаю исходную сумму")
                return amount
    except Exception as e:
        logger.error(f"Ошибка при конвертации транзакции: {e}", exc_info=True)
        return 0.0


def get_greeting() -> str:
    """Возврат приветствия в зависимости от времени"""
    current_hour = datetime.now().hour
    logger.debug(f"Текущий час: {current_hour}")

    if 5 <= current_hour < 12:
        greeting = 'Доброе утро'
    elif 12 <= current_hour < 18:
        greeting = 'Добрый день'
    elif 18 <= current_hour < 23:
        greeting = 'Добрый вечер'
    else:
        greeting = 'Доброй ночи'

    logger.info(f"Приветствие: {greeting}")
    return greeting


def get_card_spending(transactions: List[Dict]) -> List[Dict]:
    """
    Принимает список словарей, возвращает:
    -последние 4 цифры карты,
    -общую сумму расходов,
    -кешбэк (1 рубль на каждые 100 рублей)
    """
    logger.info(f"Начало расчета статистики по картам. Всего транзакций: {len(transactions)}")

    card_stat = defaultdict(lambda: {"total_spent": 0.0, "last_digits": ""})
    processed_count = 0
    skipped_count = 0

    for transaction in transactions:
        try:
            amount_rub = transaction_convert(transaction)
            if amount_rub < 0:
                logger.debug(f"Пропущена транзакция с отрицательной суммой: {amount_rub}")
                skipped_count += 1
                continue

            # Получаем информацию о карте из поля 'from'
            card_info = transaction.get("from", "")

            if "Счет" in card_info:
                logger.debug("Пропущена транзакция со счета")
                skipped_count += 1
                continue

            card_numbers = re.findall(r"\d+", card_info)

            if card_numbers:
                card_number = card_numbers[-1]
                if len(card_number) >= 4:
                    last_digits = card_number[-4:]
                else:
                    last_digits = card_number
            else:
                logger.debug("Не удалось извлечь номер карты")
                skipped_count += 1
                continue

            if not card_stat[last_digits]["last_digits"]:
                card_stat[last_digits]["last_digits"] = last_digits

            card_stat[last_digits]["total_spent"] += amount_rub
            processed_count += 1
            logger.debug(f"Добавлено {amount_rub} RUB к карте ****{last_digits}")

        except Exception as e:
            logger.error(f"Ошибка обработки транзакции: {e}", exc_info=True)
            skipped_count += 1
            continue

    logger.info(f"Обработано карт: {len(card_stat)}, транзакций: {processed_count}, пропущено: {skipped_count}")

    # Результаты:
    result = []
    for last_digits, stats in card_stat.items():
        total_spent = stats['total_spent']
        cashback = round(total_spent / 100, 2)
        result.append({
            'last_digits': last_digits,
            'total_spent': round(total_spent, 2),
            'cashback': cashback
        })
        logger.info(f"Карта ****{last_digits}: потрачено {total_spent:.2f} RUB, кэшбэк {cashback:.2f} RUB")

    return result


# Категории:
def determine_category(description: str) -> str:
    """Определяет категорию транзакции на основе описания"""
    if not description:
        logger.debug("Пустое описание транзакции")
        return "Прочее"

    description_lower = description.lower()
    logger.debug(f"Определение категории для: {description[:50]}")

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
                logger.debug(f"Категория для '{description[:30]}': {category}")
                return category

    logger.debug(f"Категория для '{description[:30]}': Прочее")
    return "Прочее"


# Топ 5 транзакций:
def get_top_transactions(transactions: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Возвращает топ транзакций по сумме, по умолчанию 5.
    """
    logger.info(f"Поиск топ-{limit} транзакций. Всего транзакций: {len(transactions)}")

    expenditure_transactions = []
    error_count = 0

    for transaction in transactions:
        try:
            amount_rub = transaction_convert(transaction)

            category = transaction.get("category", "")
            if not category:
                category = determine_category(transaction.get('description', ''))

            # Формат дат
            date_str = transaction.get('date', '')
            try:
                if 'T' in date_str:
                    date_object = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    formatted_date = date_object.strftime('%d.%m.%Y')
                else:
                    date_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    formatted_date = date_object.strftime('%d.%m.%Y')
            except ValueError as e:
                logger.warning(f"Ошибка парсинга даты '{date_str}': {e}")
                formatted_date = date_str[:10].replace('-', '.')

            expenditure_transactions.append({
                "date": formatted_date,
                "amount": round(amount_rub, 2),
                "category": category,
                "description": transaction.get("description", ""),
                "original_amount": amount_rub,
            })
            logger.debug(f"Добавлена транзакция: {formatted_date} - {amount_rub:.2f} RUB - {category}")

        except Exception as e:
            logger.error(f"Ошибка обработки транзакции для топа: {e}", exc_info=True)
            error_count += 1
            continue

    logger.info(f"Успешно обработано транзакций: {len(expenditure_transactions)}, ошибок: {error_count}")

    # Сортировка:
    sorted_transactions = sorted(expenditure_transactions, key=lambda x: abs(x["original_amount"]), reverse=True)

    # Возврат топа:
    top_transactions = []
    for i, transaction in enumerate(sorted_transactions[:limit], 1):
        top_transactions.append({
            "date": transaction["date"],
            "amount": transaction["amount"],
            "category": transaction["category"],
            "description": transaction["description"],
        })
        logger.info(f"Топ-{i}: {transaction['description'][:50]} - {transaction['amount']:.2f} RUB")

    logger.info(f"Возвращено {len(top_transactions)} транзакций")
    return top_transactions


# Получение курса валют ЦБ:
def get_financial_data() -> Dict:
    """
    Получает курсы валют и цены акций на основе настроек пользователя
    Возвращает: словарь с курсами валют и ценами акций
    """
    logger.info("Начало получения финансовых данных")

    settings_file = Path("user_settings.json")

    # Проверяем, существует ли файл настроек
    if not settings_file.exists():
        logger.info(f"Файл {settings_file} не найден, создаю с настройками по умолчанию")
        default_settings = {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)
        settings = default_settings
        logger.info(f"Создан файл {settings_file} с настройками по умолчанию")
    else:
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        logger.info(f"Загружены настройки из {settings_file}")

    # Получаем списки валют и акций из настроек
    user_currencies = settings.get("user_currencies", ["USD", "EUR"])
    user_stocks = settings.get("user_stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])

    logger.info(f"Валюты для загрузки: {user_currencies}")
    logger.info(f"Акции для загрузки: {user_stocks}")

    # Получение курсов валют
    logger.info("Получение курсов валют через API ЦБ РФ")
    currency_rates = []

    try:
        url = 'https://www.cbr-xml-daily.ru/daily_json.js'
        currency_response = requests.get(url, timeout=10)
        currency_response.raise_for_status()
        data = currency_response.json()
        logger.info("Успешный запрос к API ЦБ РФ")

        fallback_rates = {"USD": 92.50, "EUR": 100.20, "GBP": 115.30, "CNY": 12.80}

        for currency in user_currencies:
            if currency in data.get("Valute", {}):
                rate = data["Valute"][currency]["Value"]
                currency_rates.append({"currency": currency, "rate": round(rate, 2)})
                logger.info(f"{currency}: {rate:.2f} RUB")
            else:
                logger.warning(f"Валюта {currency} не найдена в API, использую fallback курс")
                rate = fallback_rates.get(currency, 100.0)
                currency_rates.append({"currency": currency, "rate": rate})

    except requests.Timeout:
        logger.error("Таймаут при запросе к API ЦБ РФ")
        fallback_rates = {"USD": 92.50, "EUR": 100.20}
        for currency in user_currencies:
            rate = fallback_rates.get(currency, 100.0)
            currency_rates.append({"currency": currency, "rate": rate})
            logger.warning(f"Использую fallback курс для {currency}: {rate:.2f} RUB")

    except Exception as e:
        logger.error(f"Ошибка получения курсов валют: {e}", exc_info=True)
        fallback_rates = {"USD": 92.50, "EUR": 100.20}
        for currency in user_currencies:
            rate = fallback_rates.get(currency, 100.0)
            currency_rates.append({"currency": currency, "rate": rate})
            logger.warning(f"Использую fallback курс для {currency}: {rate:.2f} RUB")

    # Получение цен акций
    logger.info("Получение цен акций через Alpha Vantage API")
    stock_prices = []
    api_key = os.getenv("API_KEY_STOCKS")

    if not api_key:
        logger.warning("API ключ для акций не найден в .env файле")
        logger.warning("Получите бесплатный ключ на https://www.alphavantage.co/support/#api-key")

        fallback_prices = {
            "AAPL": 150.12, "AMZN": 3173.18, "GOOGL": 2742.39,
            "MSFT": 296.71, "TSLA": 1007.08, "META": 310.20,
        }

        for symbol in user_stocks:
            price = fallback_prices.get(symbol, 100.0)
            stock_prices.append({"stock": symbol, "price": price})
            logger.info(f"{symbol}: Использую fallback цену ${price:.2f}")
    else:
        logger.info(f"Используется API ключ: {api_key[:5]}...")

        for symbol in user_stocks:
            try:
                logger.info(f"Загрузка {symbol}...")

                url = "https://www.alphavantage.co/query"
                params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "apikey": api_key}

                currency_response = requests.get(url, params=params, timeout=10)
                currency_response.raise_for_status()
                data = currency_response.json()

                # Проверяем на ошибки API
                if "Error Message" in data:
                    logger.error(f"Ошибка API для {symbol}: {data['Error Message']}")
                    price = 100.0

                elif "Information" in data:
                    logger.warning(f"Информация API для {symbol}: {data['Information'][:80]}...")
                    price = 100.0

                elif "Time Series (Daily)" in data:
                    time_series = data['Time Series (Daily)']

                    if time_series:
                        latest_date = max(time_series.keys())
                        latest_data = time_series[latest_date]
                        price = float(latest_data.get('4. close', 0))

                        if price > 0:
                            logger.info(f"{symbol}: ${price:.2f} ({latest_date})")
                        else:
                            logger.warning(f"{symbol}: Цена не получена, использую fallback")
                            price = 100.0
                    else:
                        logger.warning(f"{symbol}: Нет данных, использую fallback")
                        price = 100.0
                else:
                    logger.warning(f"{symbol}: Неожиданный формат ответа")
                    price = 100.0

                stock_prices.append({"stock": symbol, "price": round(price, 2) if price != 100.0 else price})

            except requests.Timeout:
                logger.error(f"{symbol}: Таймаут при запросе")
                stock_prices.append({"stock": symbol, "price": 100.0})

            except Exception as e:
                logger.error(f"{symbol}: Ошибка: {e}", exc_info=True)
                stock_prices.append({"stock": symbol, "price": 100.0})

    result = {'currency_rates': currency_rates, 'stock_prices': stock_prices}
    logger.info(f"Финансовые данные получены: {len(currency_rates)} валют, {len(stock_prices)} акций")

    return result

def load_transactions_from_file(file_path: str) -> List[Dict]:
    """Загружает транзакции из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            transactions = json.load(f)

        return transactions
    except FileNotFoundError:

        return []
    except json.JSONDecodeError as e:

        return []
    except Exception as e:

        return []

if __name__ == "__main__":
    test_transactions = [
        {
            "date": "2021-12-21 10:30:00",
            "description": "Перевод Кредитная карта. ТП 10.2 RUR",
            "from": "Карта 1234 5678 9012 5814",
            "operationAmount": {"amount": "1198.23", "currency": {"code": "RUB"}}
        },
        {
            "date": "2021-12-20 14:20:00",
            "description": "Лента",
            "from": "Карта 1234 5678 9012 5814",
            "operationAmount": {"amount": "829.00", "currency": {"code": "RUB"}}
        }
    ]

    # Формируем полный ответ
    response = {
        "greeting": get_greeting(),
        "cards": get_card_spending(test_transactions),
        "top_transactions": get_top_transactions(test_transactions),
        "currency_rates": get_financial_data()["currency_rates"],
        "stock_prices": get_financial_data()["stock_prices"]
    }

    # Выводим JSON
    print("\n" + "=" * 50)
    print("ИТОГОВЫЙ JSON:")
    print("=" * 50)
    print(json.dumps(response, ensure_ascii=False, indent=2))
