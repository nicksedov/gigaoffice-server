import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

# Словари для генерации имён и городов
MALE_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Иван", "Михаил", "Николай", "Владимир"
]
FEMALE_NAMES = [
    "Анна", "Екатерина", "Мария", "Ольга", "Наталья",
    "Татьяна", "Елена", "Ирина", "Светлана", "Юлия"
]
SURNAMES = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Попов",
    "Васильев", "Смирнов", "Морозов", "Волков", "Соколов"
]
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Волгоград", "Красноярск",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону", "Уфа", "Иркутск", "Хабаровск"
]

def random_name() -> str:
    gender = random.choice(["male", "female"])
    if gender == "male":
        name = random.choice(MALE_NAMES)
        surname = random.choice(SURNAMES)
    else:
        name = random.choice(FEMALE_NAMES)
        surname = random.choice(SURNAMES)
        # Для женских фамилий добавим окончание "а" (упрощённо)
        if not surname.endswith("а"):
            surname += "а"
    return f"{name} {surname}"

def random_phone() -> str:
    # Формат: +7XXXXXXXXXX
    digits = [str(random.randint(0, 9)) for _ in range(10)]
    return "+7" + "".join(digits)

def random_city() -> str:
    return random.choice(CITIES)

def random_age() -> int:
    return random.randint(18, 80)

def random_height() -> int:
    return random.randint(160, 200)

class DryRunGigaChatService:
    """Заглушка для GigaChat, имитирует ответы без внешних запросов."""

    def __init__(self, *args, **kwargs):
        self.model = "GigaChat-DryRun"
        self.total_tokens_used = 0
        self.request_times = []
        logger.info("GigaChat client initialized successfully (DRY RUN mode)")

    def _count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _add_request_time(self):
        self.request_times.append(time.time())

    def _generate_fake_result(self) -> List[List[Any]]:
        result = [['Имя', 'Телефон', 'Город', 'Возраст', 'Рост']]
        for _ in range(5):
            row = [
                random_name(),         # Имя и фамилия
                random_phone(),        # Телефон
                random_city(),         # Город
                random_age(),          # Возраст
                random_height(),       # Рост
            ]
            result.append(row)
        return result

    async def process_query(
        self,
        query: str,
        input_data: Optional[List[Dict]] = None,
        temperature: float = 0.1
    ) -> Tuple[List[List[Any]], Dict[str, Any]]:
        self._add_request_time()
        time.sleep(0.2)
        fake_result = self._generate_fake_result()
        fake_metadata = {
            "processing_time": 0.2,
            "input_tokens": 10,
            "output_tokens": 8,
            "total_tokens": 18,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "request_id": "dryrun-123",
            "success": True
        }
        self.total_tokens_used += fake_metadata["total_tokens"]
        return fake_result, fake_metadata

    def get_available_models(self) -> List[str]:
        return [self.model]

    def check_service_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "response_time": 0.01,
            "model": self.model,
            "total_tokens_used": self.total_tokens_used,
            "requests_in_last_minute": len(self.request_times),
            "rate_limit_available": True
        }

    async def process_batch_queries(
        self,
        queries: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        results = []
        for query in queries:
            result, metadata = await self.process_query(query["query"], query.get("input_data"))
            results.append({
                "id": query.get("id"),
                "result": result,
                "metadata": metadata,
                "error": None
            })
        return results

    def get_usage_statistics(self) -> Dict[str, Any]:
        return {
            "total_tokens_used": self.total_tokens_used,
            "requests_last_minute": len(self.request_times),
            "rate_limit_remaining": 100,
            "max_requests_per_minute": 100,
            "max_tokens_per_request": 2048,
            "model": self.model
        }
