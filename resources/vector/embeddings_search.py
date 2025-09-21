import psycopg2
from typing import List, Tuple
from sentence_transformers import SentenceTransformer

# Инициализация модели один раз при старте приложения
_ru_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def ru_embedder(text: str) -> List[float]:
    """
    Получает эмбеддинг для строки на русском языке.
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

    :param query: Строка для поиска.
    :param conn: psycopg2 подключение к PostgreSQL.
    :param embedding_table: Имя таблицы с эмбеддингами (например, 'header_embeddings').
    :param limit: Максимальное количество результатов.
    :return: Список кортежей (header, score).
    """
    query_embedding = ru_embedder(query)
    with conn.cursor() as cur:
        sql = f"""
            SELECT header, 1 - (embedding <=> %s::vector) AS score
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