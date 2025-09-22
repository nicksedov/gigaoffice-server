import psycopg2
import csv
from sentence_transformers import SentenceTransformer

HEADERS_CSV_FILE = "common_headers.csv"
EMBEDDING_TABLE = "header_embeddings"

#MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
#MODEL_DIMENSION=768

MODEL_NAME = "ai-forever/FRIDA"
MODEL_DIMENSION=1536

#MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L6-v2"
#MODEL_DIMENSION=384

def read_headers_from_csv(filename):
    """
    Читает заголовки из CSV файла и возвращает список уникальных терминов
    из обеих колонок (русской и английской), исключая пустые значения
    """
    headers = set()  # Используем set для исключения дубликатов
    
    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Пропускаем заголовок CSV
        
        for row in reader:
            if len(row) >= 2:
                russian_term = row[0].strip()
                english_term = row[1].strip()
                
                # Добавляем термины, если они не пустые
                if russian_term:
                    headers.add(russian_term)
                if english_term:
                    headers.add(english_term)
    
    return sorted(list(headers))  # Возвращаем отсортированный список

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
    
    # Читаем все уникальные заголовки из CSV
    headers = read_headers_from_csv(HEADERS_CSV_FILE)
    print(f"Найдено {len(headers)} уникальных терминов в CSV файле")
    
    # Генерируем эмбеддинги
    embeddings = model.encode(headers, normalize_embeddings=True)
    print(f"Сгенерировано {len(embeddings)} эмбеддингов")

    with conn, conn.cursor() as cur:
        cur.execute(f"""
            DROP TABLE IF EXISTS {EMBEDDING_TABLE};
            
            CREATE TABLE {EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                embedding VECTOR({MODEL_DIMENSION}), -- размерность зависит от используемой модели
                language VARCHAR(2) -- 'ru', 'en'
            );

            CREATE INDEX {EMBEDDING_TABLE}_idx_embedding_l2 ON {EMBEDDING_TABLE} USING ivfflat (embedding vector_l2_ops);
            CREATE INDEX {EMBEDDING_TABLE}_idx_embedding_cos ON {EMBEDDING_TABLE} USING ivfflat (embedding vector_cosine_ops);
            """
        )
        # Определяем язык для каждого термина
        import re
        
        inserted_count = 0
        for header, emb in zip(headers, embeddings):
            # Простое определение языка по наличию кириллических символов
            language = 'ru' if re.search(r'[а-яё]', header.lower()) else 'en'
            
            cur.execute(
                f"""INSERT INTO {EMBEDDING_TABLE} (header, embedding, language) 
                   VALUES (%s, %s, %s) ON CONFLICT (header) DO NOTHING""",
                (header, emb.tolist(), language)
            )
            
            # Проверяем, была ли вставлена запись
            if cur.rowcount > 0:
                inserted_count += 1
    
    print(f"Загружено {inserted_count} новых эмбеддингов в таблицу {EMBEDDING_TABLE}")
    print(f"Всего в таблице: {len(headers)} терминов")

if __name__ == "__main__":
    # Выберите нужную версию:
    main()  # Простая версия - только эмбеддинги
    #main_with_pairs()  # Расширенная версия - эмбеддинги + связи между терминами