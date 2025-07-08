from typing import List, Dict, Any
from datetime import datetime
import uuid

# Предустановленные промпты
MOCK_PROMPTS = [
    {
        "id": "prompt_001",
        "name": "Анализ продаж",
        "description": "Анализирует данные продаж и создает сводную таблицу",
        "template": "Проанализируй данные продаж в таблице: {data}. Создай сводку с итогами по категориям.",
        "category": "Аналитика",
        "is_active": True
    },
    {
        "id": "prompt_002", 
        "name": "Генерация тестовых данных",
        "description": "Создает тестовые данные для таблиц",
        "template": "Создай тестовые данные с колонками: {columns}. Количество строк: {rows}",
        "category": "Генерация",
        "is_active": True
    },
    {
        "id": "prompt_003",
        "name": "Финансовый анализ", 
        "description": "Выполняет финансовый анализ данных",
        "template": "Выполни финансовый анализ данных: {data}. Рассчитай ключевые показатели.",
        "category": "Финансы",
        "is_active": True
    },
    {
        "id": "prompt_004",
        "name": "Сравнение конкурентов",
        "description": "Сравнительный анализ конкурентов",
        "template": "Сравни данные конкурентов: {data}. Создай сравнительную таблицу.",
        "category": "Маркетинг", 
        "is_active": True
    },
    {
        "id": "prompt_005",
        "name": "Прогноз продаж",
        "description": "Прогнозирование продаж на основе исторических данных",
        "template": "На основе исторических данных {data} создай прогноз продаж на следующий период.",
        "category": "Прогнозирование",
        "is_active": True
    }
]

# Мок-данные для различных сценариев
MOCK_RESPONSES = {
    "sales_analysis": [
        ["Категория", "Продажи Q1", "Продажи Q2", "Рост %"],
        ["Электроника", 125000, 145000, "16%"],
        ["Одежда", 89000, 95000, "6.7%"], 
        ["Книги", 34000, 29000, "-14.7%"],
        ["Спорт", 67000, 78000, "16.4%"],
        ["ИТОГО", 315000, 347000, "10.2%"]
    ],
    
    "financial_data": [
        ["Показатель", "Q1 2024", "Q2 2024", "Изменение"],
        ["Выручка", 2500000, 2750000, "+10%"],
        ["Себестоимость", 1500000, 1600000, "+6.7%"],
        ["Валовая прибыль", 1000000, 1150000, "+15%"],
        ["Операционные расходы", 600000, 650000, "+8.3%"],
        ["Чистая прибыль", 400000, 500000, "+25%"]
    ],
    
    "test_customers": [
        ["ID", "Имя", "Email", "Статус", "Сумма покупок"],
        [1, "Иванов Иван", "ivanov@example.com", "VIP", 150000],
        [2, "Петрова Мария", "petrova@example.com", "Regular", 75000],
        [3, "Сидоров Петр", "sidorov@example.com", "New", 25000],
        [4, "Козлова Анна", "kozlova@example.com", "VIP", 200000],
        [5, "Федоров Олег", "fedorov@example.com", "Regular", 95000]
    ],
    
    "market_research": [
        ["Компания", "Доля рынка", "Выручка млн", "Рост YoY"],
        ["Компания А", "25%", 1250, "+12%"],
        ["Компания Б", "20%", 1000, "+8%"], 
        ["Компания В", "15%", 750, "-2%"],
        ["Наша компания", "12%", 600, "+15%"],
        ["Прочие", "28%", 1400, "+5%"]
    ]
}

def get_mock_user() -> Dict[str, Any]:
    """Возвращает данные тестового пользователя"""
    return {
        "user_id": "user_12345",
        "username": "test_user",
        "email": "test@gigaoffice.com", 
        "role": "analyst"
    }

def generate_request_id() -> str:
    """Генерирует уникальный ID запроса"""
    return f"req_{uuid.uuid4().hex[:12]}"

def get_processing_result(query_text: str, input_data: List[Dict[str, Any]] = None) -> List[List[Any]]:
    """Возвращает мок-результат на основе текста запроса"""
    query_lower = query_text.lower()
    
    if any(word in query_lower for word in ["продажи", "sales", "анализ продаж"]):
        return MOCK_RESPONSES["sales_analysis"]
    elif any(word in query_lower for word in ["финанс", "прибыль", "выручка"]):
        return MOCK_RESPONSES["financial_data"] 
    elif any(word in query_lower for word in ["клиент", "покупател", "customer"]):
        return MOCK_RESPONSES["test_customers"]
    elif any(word in query_lower for word in ["конкурент", "рынок", "доля"]):
        return MOCK_RESPONSES["market_research"]
    elif input_data:
        # Если есть исходные данные, создаем простую обработку
        if len(input_data) > 0:
            headers = input_data[0] if input_data[0] else ["Колонка 1", "Колонка 2"]
            processed_data = [headers + ["Результат анализа"]]
            for i, row in enumerate(input_data[1:], 1):
                processed_row = row + [f"Обработано ИИ (строка {i})"]
                processed_data.append(processed_row)
            return processed_data
    
    # Базовый ответ по умолчанию
    return [
        ["Параметр", "Значение"],
        ["Статус обработки", "Успешно"],
        ["Время выполнения", "0.5 сек"],
        ["Результат ИИ", "Данные обработаны"]
    ]
