# GigaOffice AI Service

## Описание проекта

GigaOffice AI Service — это промежуточный сервис для интеграции плагина Р7-Офис с большой языковой моделью GigaChat. Сервис предоставляет RESTful API для обработки запросов от офисных документов и получения интеллектуальных ответов через GigaChat API.

### Основные возможности

- **Асинхронная обработка запросов** с использованием Apache Kafka
- **Классификация запросов** по предустановленным категориям
- **Управление промптами** с базой данных шаблонов
- **Поддержка трех режимов работы**: dryrun, cloud, mTLS
- **Rate limiting** и мониторинг производительности
- **PostgreSQL** для хранения данных и метрик
- **Кэширование** часто используемых промптов

## Технический стек

### Backend
- **Python 3.8+** - основной язык разработки
- **FastAPI** - веб-фреймворк для REST API
- **SQLAlchemy** - ORM для работы с базой данных
- **Alembic** - миграции базы данных
- **Pydantic** - валидация и сериализация данных

### Интеграции
- **LangChain GigaChat** - интеграция с GigaChat API
- **Apache Kafka** (aiokafka) - очереди сообщений
- **PostgreSQL** - основная база данных

### Инфраструктура
- **Docker** - контейнеризация
- **Uvicorn** - ASGI сервер
- **Loguru** - структурированное логирование
- **SlowAPI** - rate limiting

## Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Р7-Офис       │    │  GigaOffice API  │    │    GigaChat     │
│   Плагин        │◄──►│     Service      │◄──►│      API        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │   Apache Kafka  │
                       │   (Очереди)     │
                       └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │   PostgreSQL    │
                       │  (Данные)       │
                       └─────────────────┘
```

## Установка и настройка

### Предварительные требования

- Python 3.8+
- PostgreSQL 12+
- Apache Kafka 2.8+
- Docker и Docker Compose (рекомендуется)

### Установка через Docker

1. **Клонирование репозитория:**
```bash
git clone <repository_url>
cd gigaoffice-service
```

2. **Создание файла окружения:**
```bash
cp .env.example .env
```

3. **Настройка переменных окружения в `.env`:**
```env
# Основные настройки
GIGACHAT_RUN_MODE=cloud  # dryrun, cloud, mtls
PORT=8000
LOG_LEVEL=info

# База данных PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gigaoffice
DB_USER=gigaoffice
DB_PASSWORD=your_secure_password

# GigaChat API (для cloud режима)
GIGACHAT_CREDENTIALS=your_base64_encoded_credentials
GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
GIGACHAT_MODEL=GigaChat
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# GigaChat mTLS (для mtls режима)
GIGACHAT_MTLS_CA_BUNDLE_FILE=/path/to/ca-bundle.crt
GIGACHAT_MTLS_CERT_FILE=/path/to/client.crt
GIGACHAT_MTLS_KEY_FILE=/path/to/client.key
GIGACHAT_MTLS_KEY_FILE_PASSWORD=your_key_password

# Apache Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_REQUESTS=gigaoffice-requests
KAFKA_TOPIC_RESPONSES=gigaoffice-responses
KAFKA_CONSUMER_GROUP=gigaoffice-group

# Rate limiting
GIGACHAT_MAX_REQUESTS_PER_MINUTE=20
GIGACHAT_MAX_TOKENS_PER_REQUEST=8192
```

4. **Запуск через Docker Compose:**
```bash
docker-compose up -d
```

### Ручная установка

1. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

2. **Создание базы данных:**
```sql
CREATE DATABASE gigaoffice;
CREATE USER gigaoffice WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE gigaoffice TO gigaoffice;
```

3. **Инициализация базы данных:**
```bash
python -c "from service.database import init_database; init_database()"
```

4. **Запуск сервиса:**
```bash
cd service
python main.py
```

## Конфигурация

### Структура конфигурационных файлов

```
resources/
├── config/
│   ├── database_config.json      # Настройки БД
│   ├── gigachat_config.json      # Настройки GigaChat
│   └── kafka_config.json         # Настройки Kafka
├── prompts/
│   ├── default_prompts.json      # Предустановленные промпты
│   ├── prompt_categories.json    # Категории промптов
│   └── system_prompt_*.yaml      # Системные промпты
└── sql/
    └── database_info.sql         # SQL запросы
```

### Режимы работы GigaChat

1. **dryrun** - режим отладки без реальных запросов к GigaChat
2. **cloud** - подключение через облачное API с авторизацией по токену
3. **mtls** - подключение через взаимную TLS аутентификацию

## API Документация

После запуска сервиса документация доступна по адресам:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Основные эндпоинты

#### Проверка состояния
- `GET /api/health` - статус сервиса

#### Обработка ИИ запросов
- `POST /api/ai/process` - отправка запроса на обработку
- `GET /api/ai/status/{request_id}` - статус обработки
- `GET /api/ai/result/{request_id}` - получение результата

#### Управление промптами
- `GET /api/prompts/categories` - список категорий
- `GET /api/prompts/presets` - предустановленные промпты
- `POST /api/prompts/classify` - классификация запроса

#### Метрики
- `GET /api/metrics` - статистика использования

### Пример запроса

```bash
curl -X POST "http://localhost:8000/api/ai/process" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Проанализируй данные продаж и найди тренды",
    "input_range": "A1:D10",
    "category": "analysis",
    "input_data": [
      ["Товар", "Январь", "Февраль", "Март"],
      ["Товар A", 100, 120, 110],
      ["Товар B", 80, 90, 95]
    ]
  }'
```

## Мониторинг и логирование

### Логи
Логи записываются в файл `logs/gigaoffice.log` с ротацией каждый день.

### Метрики
Сервис собирает метрики:
- Количество запросов
- Время обработки
- Использование токенов
- Ошибки и их типы

### Health Check
```bash
curl http://localhost:8000/api/health
```

## Разработка

### Структура проекта

```
service/
├── core/                    # Core application components
│   ├── config.py           # Centralized configuration
│   ├── exceptions.py       # Custom exceptions
│   └── dependencies.py     # Common dependencies
├── api/                     # API layer
│   └── routes/
│       ├── health.py       # Health endpoints
│       ├── ai.py           # AI processing
│       ├── prompts.py      # Prompt management
│       └── metrics.py      # Metrics endpoints
├── services/                # Business logic layer
│   └── gigachat/
│       ├── base.py         # Base service interface
│       ├── factory.py      # Service factory
│       ├── prompt_builder.py
│       ├── response_parser.py
│       └── implementations/
│           ├── cloud.py    # Cloud implementation
│           ├── mtls.py     # mTLS implementation
│           └── dryrun.py   # Development implementation
├── models/                  # Data models
│   ├── base.py             # Base model classes
│   ├── database.py         # ORM models
│   └── schemas.py          # API schemas
├── database/               # Database layer
│   └── connection.py       # Database connection
└── utils/                  # Utility functions
    └── resource_loader.py
```

### Добавление новых функций

1. **Новые промпты**: добавить в `resources/prompts/default_prompts.json`
2. **Новые категории**: добавить в `resources/prompts/prompt_categories.json`
3. **Новые API эндпоинты**: добавить в `routers.py`
4. **Новые модели данных**: добавить в `model_orm.py` и `model_api.py`

### Тестирование

```bash
# Запуск тестов
python -m pytest tests/

# Тестирование в режиме dryrun
export GIGACHAT_RUN_MODE=dryrun
python main.py
```

## Производственное развертывание

### Рекомендации для продакшена

1. **Использовать прокси-сервер** (nginx/apache) перед приложением
2. **Настроить SSL/TLS** для безопасности
3. **Мониторинг** через Prometheus/Grafana
4. **Резервное копирование** базы данных
5. **Масштабирование** через множественные экземпляры

### Пример nginx конфигурации

```nginx
upstream gigaoffice {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;  # дополнительные экземпляры
}

server {
    listen 80;
    server_name gigaoffice.example.com;
    
    location / {
        proxy_pass http://gigaoffice;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd сервис

```ini
[Unit]
Description=GigaOffice AI Service
After=network.target postgresql.service

[Service]
Type=simple
User=gigaoffice
WorkingDirectory=/opt/gigaoffice
Environment=PYTHONPATH=/opt/gigaoffice
ExecStart=/opt/gigaoffice/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Устранение неполадок

### Частые проблемы

1. **Ошибка подключения к БД**:
   - Проверить настройки в `.env`
   - Убедиться, что PostgreSQL запущен
   - Проверить права доступа пользователя БД

2. **Ошибки GigaChat API**:
   - Проверить корректность credentials
   - Убедиться в доступности GigaChat API
   - Проверить лимиты запросов

3. **Проблемы с Kafka**:
   - Проверить, что Kafka запущен
   - Убедиться в корректности настроек топиков
   - Проверить права доступа consumer group

### Логи и отладка

```bash
# Просмотр логов
tail -f logs/gigaoffice.log

# Увеличение уровня логирования
export LOG_LEVEL=debug

# Проверка статуса компонентов
curl http://localhost:8000/api/health
```
