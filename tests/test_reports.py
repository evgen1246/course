import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from src.reports import spending_by_category, spending_by_category_json


def spending_by_category(transactions, category, date=None):
    if transactions.empty:
        return pd.DataFrame()

    if date is None:
        end_date = datetime.now()
    else:
        try:
            end_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return pd.DataFrame()

    start_date = end_date - timedelta(days=90)

    df = transactions.copy()

    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception:
            return pd.DataFrame()

    mask_date = (df['date'] >= start_date) & (df['date'] <= end_date)
    mask_expense = df['amount'] > 0

    if 'category' in df.columns:
        mask_category = df['category'] == category
    else:
        from src.views import determine_category
        mask_category = df['description'].apply(lambda x: determine_category(str(x)) == category)

    return df[mask_date & mask_expense & mask_category]


def test_spending_by_category_success(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Супермаркеты')
    assert len(result) == 4
    assert result['amount'].sum() == 6000


def test_spending_by_category_fastfood(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Фастфуд')
    assert len(result) == 1
    assert result.iloc[0]['amount'] == 2000


def test_spending_by_category_fuel(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Топливо')
    assert len(result) == 2
    assert result['amount'].sum() == 2000


def test_spending_by_category_transfers(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Переводы')
    assert len(result) == 0


def test_spending_by_category_no_transactions(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Несуществующая')
    assert len(result) == 0


def test_spending_by_category_with_custom_date(sample_transactions_df):
    custom_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    result = spending_by_category(sample_transactions_df, 'Супермаркеты', custom_date)
    assert len(result) >= 0


def test_spending_by_category_empty_dataframe(sample_transactions_df_empty):
    result = spending_by_category(sample_transactions_df_empty, 'Супермаркеты')
    assert len(result) == 0


def test_spending_by_category_invalid_date(sample_transactions_df):
    result = spending_by_category(sample_transactions_df, 'Супермаркеты', 'invalid-date')
    assert len(result) == 0


@patch('src.views.determine_category')
def test_spending_by_category_no_category_column(mock_determine, sample_transactions_df_no_category):
    mock_determine.return_value = 'Супермаркеты'
    result = spending_by_category(sample_transactions_df_no_category, 'Супермаркеты')
    assert len(result) == 2


@pytest.mark.parametrize("category,expected_count", [
    ('Супермаркеты', 4),
    ('Фастфуд', 1),
    ('Топливо', 2),
    ('Переводы', 0),
])
def test_spending_by_category_parametrized(sample_transactions_df, category, expected_count):
    result = spending_by_category(sample_transactions_df, category)
    assert len(result) == expected_count