import psycopg2
from typing import List, Tuple, Union
from sentence_transformers import SentenceTransformer

# Инициализация модели один раз при старте приложения
_ru_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def ru_embedder(text: str) -> List[float]:
    """
    Получает эмбеддинг для строки на русском языке.
    
    Args:
        text: Текст для векторизации
        
    Returns:
        Векторное представление текста как список чисел с плавающей точкой
    """
    return _ru_model.encode([text])[0].tolist()

def search_common_headers(
    query: str,
    conn: psycopg2.extensions.connection,
    embedding_table: str,
    limit: int = 10
) -> List[Tuple[str, float]]:
    """
    Выполняет полнотекстовый поиск по заголовкам с использованием векторного поиска pgvector.

    Args:
        query: Строка для поиска.
        conn: psycopg2 подключение к PostgreSQL.
        embedding_table: Имя таблицы с эмбеддингами (например, 'header_embeddings').
        limit: Максимальное количество результатов.
        
    Returns:
        Список кортежей (header, score) отсортированный по релевантности.
    """
    query_embedding = ru_embedder(query)
    with conn.cursor() as cur:
        sql = f"""
            SELECT header, language, 1 - (embedding <=> %s::vector) AS score
            FROM {embedding_table}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        cur.execute(sql, (query_embedding, query_embedding, limit))
        results = cur.fetchall()
        # Return only header and score, ignoring language for compatibility
        return [(row[0], row[2]) for row in results]

def search_headers_with_language(
    query: str,
    conn: psycopg2.extensions.connection,
    embedding_table: str,
    limit: int = 10
) -> List[Tuple[str, str, float]]:
    """
    Выполняет полнотекстовый поиск по заголовкам с возвратом языка.

    Args:
        query: Строка для поиска.
        conn: psycopg2 подключение к PostgreSQL.
        embedding_table: Имя таблицы с эмбеддингами (например, 'header_embeddings').
        limit: Максимальное количество результатов.
        
    Returns:
        Список кортежей (header, language, score) отсортированный по релевантности.
    """
    query_embedding = ru_embedder(query)
    with conn.cursor() as cur:
        sql = f"""
            SELECT header, language, 1 - (embedding <=> %s::vector) AS score
            FROM {embedding_table}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        cur.execute(sql, (query_embedding, query_embedding, limit))
        return cur.fetchall()

def main():
    # Подключение к БД
    conn = psycopg2.connect(
        dbname="gigaoffice",
        user="gigaoffice",
        password="SbConnect~1",
        host="localhost",
        port=5432
    )
    print(search_common_headers("имя пользователя", conn, "header_embeddings"))

if __name__ == "__main__":
    main()