import os
import psycopg2
import csv
import re
import numpy as np
from typing import Optional
from loguru import logger

# Читаем переменные окружения с значениями по умолчанию
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "gigaoffice")
DB_USER = os.getenv("DB_USER", "gigaoffice")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "")
DB_EXTENSIONS_SCHEMA = os.getenv("DB_EXTENSIONS_SCHEMA", "")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "ai-forever/ru-en-RoSBERTa")

HEADERS_CSV_FILE = "table_headers.csv"
TARGET_TABLE = "header_embeddings"

try:
    from pymystem3 import Mystem
    MYSTEM_AVAILABLE = True
except ImportError:
    MYSTEM_AVAILABLE = False
    logger.warning("pymystem3 not available, Russian lemmatization will be disabled")


class LemmatizationError(Exception):
    pass


class MystemLemmatizer:
    def __init__(self):
        if not MYSTEM_AVAILABLE:
            raise LemmatizationError("pymystem3 not available")
        self.mystem = Mystem()

    def lemmatize(self, text: str) -> str:
        try:
            lemmatized = self.mystem.lemmatize(text)
            result = ''.join(lemmatized).strip()
            return result
        except Exception as e:
            logger.error(f"Error during Russian lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize Russian text: {e}")


class LemmatizationService:
    def __init__(self, config: Optional[dict] = None):
        self._lemmatizer = None
        try:
            if MYSTEM_AVAILABLE:
                self._lemmatizer = MystemLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")

    def lemmatize(self, text: str) -> str:
        if not text.strip():
            return text
        try:
            return self._lemmatizer.lemmatize(text)
        except Exception as e:
            logger.error(f"Error during lemmatization: {e}")
            return text


lemmatization_service = LemmatizationService()


def read_headers_from_csv(filename):
    headers = set()
    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                russian_term = row[0].strip()
                english_term = row[1].strip()
                if russian_term:
                    headers.add(russian_term)
                if english_term:
                    headers.add(english_term)
    return sorted(list(headers))


def main():
    model_path = f"{MODEL_CACHE_PATH}/{EMBEDDING_MODEL_NAME}" if MODEL_CACHE_PATH else EMBEDDING_MODEL_NAME

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    headers = read_headers_from_csv(HEADERS_CSV_FILE)
    print(f"Найдено {len(headers)} уникальных терминов в CSV файле")

    lemmatized_headers = []
    languages = []
    for header in headers:
        language = 'ru' if re.search(r'[а-яё]', header.lower()) else 'en'
        languages.append(language)
        if language == 'ru':
            lemmatized_header = lemmatization_service.lemmatize(header)
            lemmatized_headers.append(lemmatized_header)
        else:
            lemmatized_headers.append(header)
    print(f"Сгенерировано {len(headers)} лемматизированных терминов")

    print(f"Инициализируем модель эмбеддингов {model_path}")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_path)
    MODEL_DIMENSION = model.get_sentence_embedding_dimension()
    print(f"Размерность модели: {MODEL_DIMENSION}")
    embeddings = model.encode(lemmatized_headers, normalize_embeddings=True)
    print(f"Сгенерировано {len(embeddings)} эмбеддингов")

    with conn, conn.cursor() as cur:
        
        if DB_SCHEMA:
            cur.execute(f"SET search_path TO {DB_SCHEMA};")
        
        print(f"Удаляем таблицу {TARGET_TABLE}, если есть...")
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE};")
        
        print(f"Создаем таблицу {TARGET_TABLE}...")
        vector_prefix=""
        if DB_EXTENSIONS_SCHEMA:
            vector_prefix = f"{DB_EXTENSIONS_SCHEMA}."
        embedding_type = f"{vector_prefix}VECTOR({MODEL_DIMENSION})"
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"""
            DROP TABLE IF EXISTS {TARGET_TABLE};
            CREATE TABLE {TARGET_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                lemmatized_header TEXT,
                embedding {embedding_type},
                language VARCHAR(2)
            );
            """
        )
        print(f"Заполняем таблицу {TARGET_TABLE} значениями...")
        inserted_count = 0
        for header, lemmatized_header, emb, language in zip(headers, lemmatized_headers, embeddings, languages):
            cur.execute(
                f"""INSERT INTO {TARGET_TABLE} (header, lemmatized_header, embedding, language) 
                   VALUES (%s, %s, %s, %s) ON CONFLICT (header) DO NOTHING""",
                (header, lemmatized_header, emb.tolist(), language)
            )
            if cur.rowcount > 0:
                inserted_count += 1

        print(f"Создаем индексы таблицы {TARGET_TABLE}...")
        cur.execute(f"CREATE INDEX {TARGET_TABLE}_idx_lemmatized_header ON {TARGET_TABLE} (lemmatized_header);")

        cur.execute(f"""
            CREATE INDEX {TARGET_TABLE}_idx_embedding_l2 ON {TARGET_TABLE} USING ivfflat (embedding {vector_prefix}vector_l2_ops);
            CREATE INDEX {TARGET_TABLE}_idx_embedding_cos ON {TARGET_TABLE} USING ivfflat (embedding {vector_prefix}vector_cosine_ops);
            """)
    print(f"Загружено {inserted_count} новых эмбеддингов в таблицу {TARGET_TABLE}")
    print(f"Всего в таблице: {len(headers)} терминов")


if __name__ == "__main__":
    main()
