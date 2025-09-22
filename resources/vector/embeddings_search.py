import psycopg2
from typing import List, Tuple, Union
from sentence_transformers import SentenceTransformer

#MODEL_NAME="sentence-transformers/all-mpnet-base-v2"
#MODEL_NAME="sentence-transformers/paraphrase-MiniLM-L6-v2"
MODEL_NAME = "ai-forever/FRIDA"

# Инициализация модели один раз при старте приложения
_ru_model = SentenceTransformer(MODEL_NAME)

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
) -> List[Tuple[str, str, float]]:
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
    distance = "<->"

    query_embedding = ru_embedder(query)
    with conn.cursor() as cur:
        sql = f"""
            SELECT header, language, 1 - (embedding {distance} %s::vector) AS score
            FROM {embedding_table}
            ORDER BY embedding {distance} %s::vector
            LIMIT %s
        """
        cur.execute(sql, (query_embedding, query_embedding, limit))
        results = cur.fetchall()
        # Return only header and score, ignoring language for compatibility
        return results

def main():
    # Подключение к БД
    conn = psycopg2.connect(
        dbname="gigaoffice",
        user="gigaoffice",
        password="SbConnect~1",
        host="localhost",
        port=5432
    )
    print(search_common_headers("пользователь", conn, "header_embeddings", 3))

if __name__ == "__main__":
    main()