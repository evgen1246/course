from datetime import datetime, timedelta
import pandas as pd
import pytest
import json
from unittest.mock import Mock, patch



# Транзакции

@pytest.fixture
def sample_transaction_rub():
    """Фикстура: транзакция в рублях"""
    return {
        "operationAmount": {"amount": "1000.50", "currency": {"code": "RUB"}},
        "from": "Карта 1234 5678 9012 5814",
        "description": "Покупка в магазине",
        "date": "2024-01-15 14:30:00"
    }


@pytest.fixture
def sample_transaction_usd():
    """Фикстура: транзакция в долларах"""
    return {
        "operationAmount": {"amount": "100.00", "currency": {"code": "USD"}},
        "from": "Карта 1234 5678 9012 5814",
        "description": "Покупка в США",
        "date": "2024-01-15 14:30:00"
    }


@pytest.fixture
def sample_transaction_negative():
    """Фикстура: транзакция с отрицательной суммой"""
    return {
        "operationAmount": {"amount": "-500.00", "currency": {"code": "RUB"}},
        "from": "Карта 1234 5678 9012 5814",
        "description": "Возврат",
        "date": "2024-01-15 14:30:00"
    }


@pytest.fixture
def sample_transaction_from_account():
    """Фикстура: транзакция со счета"""
    return {
        "operationAmount": {"amount": "1000.00", "currency": {"code": "RUB"}},
        "from": "Счет 1234567890",
        "description": "Перевод со счета",
        "date": "2024-01-15 14:30:00"
    }


@pytest.fixture
def sample_transactions_list():
    """Фикстура: список транзакций"""
    return [
        {
            "operationAmount": {"amount": "1500.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 5814",
            "description": "Лента",
            "date": "2024-01-15 14:30:00"
        },
        {
            "operationAmount": {"amount": "50.00", "currency": {"code": "USD"}},
            "from": "Карта 1234 5678 9012 5814",
            "description": "Amazon",
            "date": "2024-01-16 10:00:00"
        },
        {
            "operationAmount": {"amount": "2000.00", "currency": {"code": "RUB"}},
            "from": "Счет 1234567890",
            "description": "Перевод",
            "date": "2024-01-17 09:00:00"
        },
        {
            "operationAmount": {"amount": "-500.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 7512",
            "description": "Возврат",
            "date": "2024-01-18 16:00:00"
        },
        {
            "operationAmount": {"amount": "800.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 5814",
            "description": "Пятерочка",
            "date": "2024-01-19 12:00:00"
        }
    ]


@pytest.fixture
def sample_transactions_multi_card():
    """Фикстура: транзакции с разными картами"""
    return [
        {
            "operationAmount": {"amount": "1000.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 5814",
            "description": "Покупка 1",
            "date": "2024-01-15 10:00:00"
        },
        {
            "operationAmount": {"amount": "2000.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 7512",
            "description": "Покупка 2",
            "date": "2024-01-16 11:00:00"
        },
        {
            "operationAmount": {"amount": "500.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 5814",
            "description": "Покупка 3",
            "date": "2024-01-17 12:00:00"
        },
        {
            "operationAmount": {"amount": "3000.00", "currency": {"code": "RUB"}},
            "from": "Карта 1234 5678 9012 7512",
            "description": "Покупка 4",
            "date": "2024-01-18 13:00:00"
        }
    ]


# ==================== ФИКСТУРЫ ДЛЯ API МОКОВ ====================

@pytest.fixture
def mock_convert_api_success():
    """Фикстура: успешный ответ API конвертации"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": 9250.00}
    return mock_response


@pytest.fixture
def mock_convert_api_failure():
    """Фикстура: ошибка API конвертации"""
    mock_response = Mock()
    mock_response.status_code = 400
    return mock_response


@pytest.fixture
def mock_currency_api_success():
    """Фикстура: успешный ответ API курсов валют"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Valute": {
            "USD": {"Value": 92.50},
            "EUR": {"Value": 100.20}
        }
    }
    return mock_response


@pytest.fixture
def mock_stock_api_success():
    """Фикстура: успешный ответ API акций"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Time Series (Daily)": {
            "2024-01-15": {"4. close": "150.12"}
        }
    }
    return mock_response


# Дата и время

@pytest.fixture
def mock_datetime_morning():
    """Фикстура: мок времени для утра (8:00)"""
    with patch('src.views.datetime') as mock_datetime:
        mock_now = Mock()
        mock_now.hour = 8
        mock_datetime.now.return_value = mock_now
        yield mock_datetime


@pytest.fixture
def mock_datetime_afternoon():
    """Фикстура: мок времени для дня (14:00)"""
    with patch('src.views.datetime') as mock_datetime:
        mock_now = Mock()
        mock_now.hour = 14
        mock_datetime.now.return_value = mock_now
        yield mock_datetime


@pytest.fixture
def mock_datetime_evening():
    """Фикстура: мок времени для вечера (20:00)"""
    with patch('src.views.datetime') as mock_datetime:
        mock_now = Mock()
        mock_now.hour = 20
        mock_datetime.now.return_value = mock_now
        yield mock_datetime


@pytest.fixture
def mock_datetime_night():
    """Фикстура: мок времени для ночи (2:00)"""
    with patch('src.views.datetime') as mock_datetime:
        mock_now = Mock()
        mock_now.hour = 2
        mock_datetime.now.return_value = mock_now
        yield mock_datetime


# Категории

@pytest.fixture
def category_test_data():
    """Фикстура: тестовые данные для категорий"""
    return [
        ("Пятерочка", "Супермаркеты"),
        ("Макдоналдс", "Фастфуд"),
        ("АЗС", "Топливо"),
        ("Кинотеатр", "Развлечения"),
        ("Аптека", "Медицина"),
        ("Перевод", "Переводы"),
        ("ЖКХ", "ЖКХ"),
        ("Ozon", "Различные товары"),
        ("Кэшбэк", "Бонусы"),
        ("Наличные", "Наличные"),
        ("МТС", "Связь"),
        ("Такси", "Транспорт"),
        ("Неизвестно", "Прочее"),
        ("", "Прочее"),
    ]


# Файлы

@pytest.fixture
def temp_settings_file(tmp_path):
    """Фикстура: временный файл настроек пользователя"""
    settings = {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "GOOGL"]
    }
    settings_file = tmp_path / "user_settings.json"
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f)
    return settings_file


@pytest.fixture
def temp_transactions_file(tmp_path):
    """Фикстура: временный файл с транзакциями"""
    transactions = [{"id": 1, "amount": 100}]
    transactions_file = tmp_path / "transactions.json"
    with open(transactions_file, "w", encoding="utf-8") as f:
        json.dump(transactions, f)
    return transactions_file


#Окуржение

@pytest.fixture
def mock_env_without_api_key():
    """Фикстура: мок без API ключа для акций"""
    with patch.dict('os.environ', {}, clear=True):
        yield

#Поиск по переводам

@pytest.fixture
def sample_transfers_transactions():
    """Фикстура: транзакции для тестирования переводов"""
    return [
        {
            "date": "2024-01-15 10:30:00",
            "description": "Перевод Валерий А.",
            "category": "Переводы",
            "operationAmount": {"amount": "5000.00", "currency": {"code": "RUB"}}
        },
        {
            "date": "2024-01-16 14:20:00",
            "description": "Перевод Сергей З.",
            "category": "Переводы",
            "operationAmount": {"amount": "3000.00", "currency": {"code": "RUB"}}
        },
        {
            "date": "2024-01-17 09:15:00",
            "description": "Перевод Артем П.",
            "category": "Переводы",
            "operationAmount": {"amount": "7000.00", "currency": {"code": "RUB"}}
        },
        {
            "date": "2024-01-18 18:00:00",
            "description": "Перевод на карту 1234",
            "category": "Переводы",
            "operationAmount": {"amount": "2000.00", "currency": {"code": "RUB"}}
        },
        {
            "date": "2024-01-19 11:45:00",
            "description": "Оплата ЖКХ",
            "category": "ЖКХ",
            "operationAmount": {"amount": "4500.00", "currency": {"code": "RUB"}}
        },
        {
            "date": "2024-01-20 15:30:00",
            "description": "Перевод Дмитрий К.",
            "category": "Переводы",
            "operationAmount": {"amount": "15000.00", "currency": {"code": "RUB"}}
        }
    ]
# DataFrame
@pytest.fixture
def sample_transactions_df():
    today = datetime.now()
    data = {
        'date': [
            today - timedelta(days=30),
            today - timedelta(days=60),
            today - timedelta(days=85),  # Топливо 1
            today - timedelta(days=45),
            today - timedelta(days=15),
            today - timedelta(days=5),
            today - timedelta(days=120),
            today - timedelta(days=40),  # Топливо 2
        ],
        'amount': [1500, 2000, 800, 3000, 1000, 500, 1000, 1200],
        'description': [
            'Покупка в Пятерочке', 'Макдоналдс', 'АЗС Лукойл',
            'Лента', 'Перекресток', 'Пятерочка', 'Перевод другу', 'Газпромнефть'
        ],
        'category': [
            'Супермаркеты', 'Фастфуд', 'Топливо',
            'Супермаркеты', 'Супермаркеты', 'Супермаркеты', 'Переводы', 'Топливо'
        ]
    }
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


@pytest.fixture
def sample_transactions_df_no_category():
    today = datetime.now()
    data = {
        'date': [
            today - timedelta(days=30),
            today - timedelta(days=60),
            today - timedelta(days=90),
        ],
        'amount': [1500, 2000, 800],
        'description': [
            'Покупка в Пятерочке',
            'Макдоналдс',
            'АЗС Лукойл',
        ],
    }
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


@pytest.fixture
def sample_transactions_df_empty():
    return pd.DataFrame()