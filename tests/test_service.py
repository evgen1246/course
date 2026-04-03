from unittest.mock import patch

import pytest

from src.services import format_transaction_date, get_transfers_to_individuals


@pytest.mark.parametrize(
    "date_input,expected_output",
    [
        ("2024-01-15 14:30:00", "15.01.2024"),
        ("2024-01-15T14:30:00Z", "15.01.2024"),
        ("2024-01-15T14:30:00+00:00", "15.01.2024"),
        ("2024-12-25 10:00:00", "25.12.2024"),
        ("2024-01-15", "15.01.2024"),
        ("", ""),
        ("invalid date", "invalid date"),  # fallback
        ("2024-13-45", "2024-13-45"),  # некорректная дата, возвращаем как есть
    ],
)
def test_format_transaction_date(date_input, expected_output):
    """Параметризованный тест форматирования даты"""
    result = format_transaction_date(date_input)
    assert result == expected_output


@patch("src.views.transaction_convert")
def test_get_transfers_to_individuals(mock_convert, sample_transfers_transactions):
    """Тест: получение переводов физическим лицам"""
    mock_convert.side_effect = [5000.00, 3000.00, 7000.00, 2000.00, 4500.00, 15000.00]

    result = get_transfers_to_individuals(sample_transfers_transactions)

    # Должны найтись переводы с именами: Валерий А., Сергей З., Артем П., Дмитрий К.
    assert len(result) == 4
    assert result[0]["recipient"] == "Валерий А."
    assert result[1]["recipient"] == "Сергей З."
    assert result[2]["recipient"] == "Артем П."
    assert result[3]["recipient"] == "Дмитрий К."


@patch("src.views.transaction_convert")
def test_get_transfers_to_individuals_amounts(mock_convert, sample_transfers_transactions):
    """Тест: проверка сумм переводов"""
    mock_convert.side_effect = [5000.00, 3000.00, 7000.00, 2000.00, 4500.00, 15000.00]

    result = get_transfers_to_individuals(sample_transfers_transactions)

    assert result[0]["amount"] == 5000.00
    assert result[1]["amount"] == 3000.00
    assert result[2]["amount"] == 7000.00
    assert result[3]["amount"] == 15000.00


@patch("src.views.transaction_convert")
def test_get_transfers_to_individuals_dates(mock_convert, sample_transfers_transactions):
    """Тест: проверка форматирования дат"""
    mock_convert.side_effect = [5000.00, 3000.00, 7000.00, 2000.00, 4500.00, 15000.00]

    result = get_transfers_to_individuals(sample_transfers_transactions)

    assert result[0]["date"] == "15.01.2024"
    assert result[1]["date"] == "16.01.2024"
    assert result[2]["date"] == "17.01.2024"
    assert result[3]["date"] == "20.01.2024"
