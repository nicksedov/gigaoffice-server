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
- **Расширенная поддержка таблиц** с форматом JSON для сложных операций

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
python -c "from app.services.database.session import init_database; init_database()"
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

## Расширенная поддержка таблиц Р7-Офис

### Обзор

Сервис теперь поддерживает расширенный формат JSON для работы с таблицами Р7-Офис, который позволяет:
- Задавать структуру таблицы с заголовками, строками и определениями колонок
- Применять стили к ячейкам, строкам и заголовкам
- Добавлять формулы для вычислений
- Создавать диаграммы на основе данных таблицы
- Определять типы данных и форматы отображения

### Формат данных

Расширенный формат данных таблицы включает следующие компоненты:

```
{
  "metadata": {
    "version": "1.0",
    "format": "enhanced-spreadsheet-data",
    "created_at": "2024-01-01T00:00:00Z",
    "plugin_id": "example-plugin-id"
  },
  "worksheet": {
    "name": "Sheet1",
    "range": "A1",
    "options": {
      "auto_resize_columns": true,
      "freeze_headers": true,
      "auto_filter": true
    }
  },
  "columns": [
    {
      "index": 0,
      "name": "Product",
      "type": "string",
      "format": "text",
      "width": 150
    }
  ],
  "data": {
    "header": {
      "values": ["Product", "Q1", "Q2"]
    },
    "rows": [
      {
        "values": ["Product A", 1000, 1200]
      },
      {
        "values": ["Product B", 800, 900]
      }
    ],
    "styles": {
      "default": {
        "font_family": "Arial",
        "font_size": 10,
        "font_color": "#000000",
        "background_color": "#FFFFFF"
      }
    },
    "formulas": [
      {
        "cell": "D2",
        "formula": "=SUM(B2:C2)",
        "description": "Total Sales for Product A"
      }
    ]
  },
  "charts": [
    {
      "type": "column",
      "title": "Quarterly Sales by Product",
      "range": "A1:D3",
      "position": {
        "top": 100,
        "left": 300,
        "width": 400,
        "height": 300
      }
    }
  ]
}
```

### API эндпоинты для работы с таблицами

#### Обработка расширенных данных таблицы
- `POST /api/spreadsheets/process` - отправка данных таблицы на обработку
- `GET /api/spreadsheets/status/{request_id}` - статус обработки

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

#### Расширенная работа с таблицами
- `POST /api/spreadsheets/process` - отправка данных таблицы на обработку
- `GET /api/spreadsheets/status/{request_id}` - статус обработки таблицы

#### Управление промптами
- `GET /api/prompts/categories` - список категорий
- `GET /api/prompts/presets` - предустановленные промпты
- `POST /api/prompts/classify` - классификация запроса

#### Метрики
- `GET /api/metrics` - статистика использования

### Пример запроса для работы с таблицами

```
curl -X POST "http://localhost:8000/api/spreadsheets/process" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Добавь колонку с итогами и создай диаграмму",
    "spreadsheet_data": {
      "metadata": {
        "version": "1.0",
        "format": "enhanced-spreadsheet-data"
      },
      "worksheet": {
        "name": "Sales",
        "range": "A1"
      },
      "data": {
        "header": {
          "values": ["Product", "Q1", "Q2"]
        },
        "rows": [
          {
            "values": ["Product A", 1000, 1200]
          },
          {
            "values": ["Product B", 800, 900]
          }
        ]
      }
    }
  }'
```

## Тестирование

### Запуск тестов

Для запуска тестов используйте pytest:

```
pytest tests/
```

### Структура тестов

```
tests/
├── conftest.py                   # Конфигурация pytest
├── test_spreadsheet_models.py    # Тесты моделей данных таблиц
├── test_spreadsheet_api.py       # Тесты API эндпоинтов таблиц
└── test_spreadsheet_processor.py # Тесты сервиса обработки таблиц
```

## Разработка

### Структура проекта

```
app/
├── api/                          # API роутеры
│   ├── ai.py                     # Эндпоинты для ИИ обработки
│   ├── health.py                 # Эндпоинты проверки состояния
│   ├── metrics.py                # Эндпоинты метрик
│   ├── prompts.py                # Эндпоинты управления промптами
│   └── spreadsheets.py           # Эндпоинты для работы с таблицами
├── models/                       # Модели данных
│   ├── api/                      # Pydantic модели для API
│   └── orm/                      # SQLAlchemy модели для БД
├── services/                     # Бизнес-логика
│   ├── database/                 # Работа с БД
│   ├── gigachat/                 # Интеграция с GigaChat
│   └── spreadsheet/              # Обработка таблиц
└── main.py                      # Точка входа приложения
```

## Лицензия

MIT License - см. файл [LICENSE](LICENSE) для подробностей.