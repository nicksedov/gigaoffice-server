import psycopg2
from sentence_transformers import SentenceTransformer

HEADERS_FILE = "resources/vector/common_headers.txt"
EMBEDDING_TABLE = "header_embeddings"  # Имя вашей таблицы
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def read_headers(filename):
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def main():
    # Подключение к БД
    conn = psycopg2.connect(
        dbname="gigaoffice",
        user="gigaoffice",
        password="SbConnect~1",
        host="localhost",
        port=5432
    )
    model = SentenceTransformer(MODEL_NAME)
    headers = read_headers(HEADERS_FILE)
    embeddings = model.encode(headers)

    with conn, conn.cursor() as cur:
        # Создание таблицы, если не существует
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                embedding VECTOR(384) -- размерность зависит от используемой модели
            )
            """
        )
        for header, emb in zip(headers, embeddings):
            cur.execute(
                f"INSERT INTO {EMBEDDING_TABLE} (header, embedding) VALUES (%s, %s) ON CONFLICT (header) DO NOTHING",
                (header, emb.tolist())
            )
    print(f"Загружено {len(headers)} эмбеддингов в таблицу {EMBEDDING_TABLE}")

if __name__ == "__main__":
    main()