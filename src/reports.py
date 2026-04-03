import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from src.views import determine_category

logger = logging.getLogger(__name__)


def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает траты по заданной категории за последние три месяца.
    """
    logger.info(f"Получение трат по категории '{category}'")

    # Проверка на пустой DataFrame
    if transactions.empty:
        logger.warning("DataFrame с транзакциями пуст")
        return pd.DataFrame()

    # Парсим дату
    if date is None:
        end_date = datetime.now()
        logger.info(f"Дата не передана, используется текущая: {end_date.strftime('%Y-%m-%d')}")
    else:
        try:
            end_date = datetime.strptime(date, "%Y-%m-%d")
            logger.info(f"Используется переданная дата: {end_date.strftime('%Y-%m-%d')}")
        except ValueError as e:
            logger.error(f"Ошибка парсинга даты '{date}': {e}")
            return pd.DataFrame()

    # Вычисляем дату 3 месяца назад
    start_date = end_date - timedelta(days=90)  # примерно 3 месяца
    logger.debug(f"Период: с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}")

    # Копируем DataFrame, чтобы не изменять исходный
    df = transactions.copy()

    # Преобразуем даты в datetime, если они еще не в этом формате
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        try:
            df["date"] = pd.to_datetime(df["date"])
            logger.debug("Даты преобразованы в datetime формат")
        except Exception as e:
            logger.error(f"Ошибка преобразования дат: {e}")
            return pd.DataFrame()

    # Фильтруем по дате (только расходы, где сумма > 0)
    mask_date = (df["date"] >= start_date) & (df["date"] <= end_date)
    mask_expense = df["amount"] > 0  # только расходы (положительные суммы)

    # Фильтруем по категории
    if "category" in df.columns:
        mask_category = df["category"] == category
    else:
        # Если категории нет, пытаемся определить по описанию
        logger.warning("В DataFrame нет колонки 'category', пытаемся определить по описанию")
        mask_category = df["description"].apply(lambda x: determine_category(str(x)) == category)

    # Применяем все фильтры
    filtered_df = df[mask_date & mask_expense & mask_category]

    logger.info(f"Найдено {len(filtered_df)} транзакций по категории '{category}' за последние 3 месяца")

    return filtered_df


def spending_by_category_json(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> str:
    """
    Возвращает JSON-ответ с тратами по заданной категории за последние три месяца.
    """

    try:
        filtered_df = spending_by_category(transactions, category, date)

        if filtered_df.empty:
            return json.dumps(
                {
                    "category": category,
                    "message": f"Нет трат по категории '{category}' за последние 3 месяца",
                    "count": 0,
                    "transactions": [],
                },
                ensure_ascii=False,
                indent=2,
            )

        # Форматируем результат
        result = {
            "category": category,
            "period": {
                "start": (
                    (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
                    if date is None
                    else (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
                ),
                "end": datetime.now().strftime("%Y-%m-%d") if date is None else date,
            },
            "total_amount": round(filtered_df["amount"].sum(), 2),
            "count": len(filtered_df),
            "transactions": filtered_df[["date", "amount", "description", "category"]].to_dict("records"),
        }

        # Форматируем даты в нужный формат
        for transaction in result["transactions"]:
            if isinstance(transaction["date"], pd.Timestamp):
                transaction["date"] = transaction["date"].strftime("%d.%m.%Y")

        logger.info(f"Сформирован JSON-ответ для категории '{category}'")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при формировании JSON-ответа: {e}", exc_info=True)
        return json.dumps(
            {"error": str(e), "category": category, "message": "Ошибка при получении данных"},
            ensure_ascii=False,
            indent=2,
        )
