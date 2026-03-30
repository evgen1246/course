import pytest
import json
from unittest.mock import Mock, patch, mock_open
from src.views import (
    transaction_convert,
    get_greeting,
    get_card_spending,
    determine_category,
    get_top_transactions,
    get_financial_data,
    load_transactions_from_file
)

"""Тесты для функции конвертации валют"""


def test_convert_rub_to_rub(sample_transaction_rub):
    """Тест: конвертация рублей в рубли (без запроса)"""
    result = transaction_convert(sample_transaction_rub)
    assert result == 1000.50


@patch('src.views.requests.get')
def test_convert_usd_to_rub_success(mock_get, sample_transaction_usd, mock_convert_api_success):
    """Тест: успешная конвертация USD в RUB"""
    mock_get.return_value = mock_convert_api_success

    result = transaction_convert(sample_transaction_usd)

    assert result == 9250.00
    mock_get.assert_called_once()


@patch('src.views.requests.get')
def test_convert_usd_to_rub_failed(mock_get, sample_transaction_usd, mock_convert_api_failure):
    """Тест: ошибка при конвертации (возврат исходной суммы)"""
    mock_get.return_value = mock_convert_api_failure

    result = transaction_convert(sample_transaction_usd)

    assert result == 100.00

"""Тесты для функции приветствия"""


def test_greeting_morning(mock_datetime_morning):
    """Тест: утреннее приветствие"""
    result = get_greeting()
    assert result == "Доброе утро"

def test_greeting_afternoon(mock_datetime_afternoon):
    """Тест: дневное приветствие"""
    result = get_greeting()
    assert result == "Добрый день"


def test_greeting_evening(mock_datetime_evening):
    """Тест: вечернее приветствие"""
    result = get_greeting()
    assert result == "Добрый вечер"


def test_greeting_night(mock_datetime_night):
    """Тест: ночное приветствие"""
    result = get_greeting()
    assert result == "Доброй ночи"

@pytest.mark.parametrize("hour,expected", [
    (5, "Доброе утро"),
    (11, "Доброе утро"),
    (12, "Добрый день"),
    (17, "Добрый день"),
    (18, "Добрый вечер"),
    (22, "Добрый вечер"),
    (23, "Доброй ночи"),
    (4, "Доброй ночи"),
])
@patch('src.views.datetime')
def test_greeting_parametrized(mock_datetime, hour, expected):
    """Параметризованный тест приветствий"""
    mock_now = Mock()
    mock_now.hour = hour
    mock_datetime.now.return_value = mock_now

    result = get_greeting()
    assert result == expected


"""Тесты для определения категории транзакций"""


@pytest.mark.parametrize("description,expected_category", [
    ("Пятерочка", "Супермаркеты"),
    ("Макдоналдс", "Фастфуд"),
    ("АЗС Лукойл", "Топливо"),
    ("Кинотеатр", "Развлечения"),
    ("Аптека", "Медицина"),
    ("Перевод другу", "Переводы"),
    ("ЖКУ Квартира", "ЖКХ"),
    ("Ozon.ru", "Различные товары"),
    ("Кэшбэк", "Бонусы"),
    ("Снятие наличных", "Наличные"),
    ("МТС", "Связь"),
    ("Яндекс Такси", "Транспорт"),
    ("Неизвестная операция", "Прочее"),
    ("", "Прочее"),
])
def test_determine_category_parametrized(description, expected_category):
    """Параметризованный тест категорий"""
    result = determine_category(description)
    assert result == expected_category


def test_determine_category_with_category_data(category_test_data):
    """Тест с использованием фикстуры category_test_data"""
    for description, expected in category_test_data:
        result = determine_category(description)
        assert result == expected


"""Тесты для расчета статистики по картам"""


@patch('src.views.transaction_convert')
def test_card_spending_single_card(mock_convert, sample_transactions_list):
    """Тест: расходы по одной карте"""
    mock_convert.side_effect = [1500.00, 4625.00, 2000.00, -500.00, 800.00]

    result = get_card_spending(sample_transactions_list)

    assert len(result) == 1
    assert result[0]["last_digits"] == "5814"
    assert result[0]["total_spent"] == 6925.00  # 1500 + 4625 + 800
    assert result[0]["cashback"] == 69.25

@patch('src.views.transaction_convert')
def test_card_spending_negative_amount(mock_convert, sample_transaction_negative):
    """Тест: пропуск отрицательных сумм"""
    mock_convert.return_value = -500

    result = get_card_spending([sample_transaction_negative])

    assert result == []


@patch('src.views.transaction_convert')
@patch('src.views.determine_category')
def test_top_transactions_limit(mock_category, mock_convert):
    """Тест: ограничение количества транзакций"""
    transactions = [
        {"date": "2024-01-15 10:00:00", "description": f"Транзакция {i}"}
        for i in range(10)
    ]
    mock_convert.side_effect = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]
    mock_category.return_value = "Тест"

    result = get_top_transactions(transactions, limit=3)

    assert len(result) == 3
    assert result[0]["amount"] == 1000
    assert result[1]["amount"] == 900
    assert result[2]["amount"] == 800


@patch('src.views.transaction_convert')
@patch('src.views.determine_category')
def test_top_transactions_sorting(mock_category, mock_convert):
    """Тест: правильная сортировка транзакций"""
    transactions = [
        {"date": "2024-01-15 10:00:00", "description": "Small"},
        {"date": "2024-01-16 10:00:00", "description": "Large"},
        {"date": "2024-01-17 10:00:00", "description": "Medium"},
    ]
    mock_convert.side_effect = [100, 1000, 500]
    mock_category.return_value = "Тест"

    result = get_top_transactions(transactions, limit=3)

    assert result[0]["amount"] == 1000
    assert result[1]["amount"] == 500
    assert result[2]["amount"] == 100

@patch('src.views.transaction_convert')
@patch('src.views.determine_category')
def test_top_transactions_with_negative(mock_category, mock_convert):
    """Тест: учет абсолютных значений для отрицательных сумм"""
    transactions = [
        {"date": "2024-01-15 10:00:00", "description": "Negative"},
        {"date": "2024-01-16 10:00:00", "description": "Positive"},
    ]
    mock_convert.side_effect = [-1000, 500]
    mock_category.return_value = "Тест"

    result = get_top_transactions(transactions, limit=2)

    assert result[0]["amount"] == -1000
    assert result[1]["amount"] == 500

"""Тесты для загрузки транзакций из файла"""


@patch("builtins.open", new_callable=mock_open, read_data='[{"id": 1, "amount": 100}]')
def test_load_success(mock_file):
    """Тест: успешная загрузка файла"""
    result = load_transactions_from_file("test.json")
    assert len(result) == 1
    assert result[0]["id"] == 1


@patch("builtins.open", side_effect=FileNotFoundError())
def test_load_file_not_found(mock_file):
    """Тест: файл не найден"""
    result = load_transactions_from_file("not_exist.json")
    assert result == []

@patch("builtins.open", new_callable=mock_open, read_data='invalid json')
def test_load_invalid_json(mock_file):
    """Тест: невалидный JSON"""
    result = load_transactions_from_file("invalid.json")
    assert result == []
    mock_file.assert_called_once_with("invalid.json", "r", encoding="utf-8")

@patch("builtins.open", side_effect=PermissionError())
def test_load_permission_error(mock_file):
    """Тест: ошибка доступа к файлу"""
    result = load_transactions_from_file("protected.json")
    assert result == []
    mock_file.assert_called_once_with("protected.json", "r", encoding="utf-8")


    """Тест для получения финансовых данных"""

@patch('src.views.requests.get')
@patch('src.views.os.getenv')
def test_get_financial_data_success(mock_getenv, mock_get,
                                    mock_currency_api_success,
                                    mock_stock_api_success,
                                    temp_settings_file):

    """Тест: успешное получение данных"""
    mock_getenv.return_value = "test_api_key"
    mock_get.side_effect = [mock_currency_api_success, mock_stock_api_success]

    with patch('src.views.Path') as mock_path:
        mock_path.return_value = temp_settings_file
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL"]
        }))):
            result = get_financial_data()

    assert "currency_rates" in result
    assert "stock_prices" in result
    assert len(result["currency_rates"]) == 2
    assert len(result["stock_prices"]) == 1


