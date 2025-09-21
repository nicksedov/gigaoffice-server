import psycopg2
import csv
from sentence_transformers import SentenceTransformer

HEADERS_CSV_FILE = "common_headers.csv"
EMBEDDING_TABLE = "header_embeddings"  # Имя вашей таблицы
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

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

def read_headers_pairs_from_csv(filename):
    """
    Читает пары терминов из CSV файла, возвращает список кортежей (русский, английский)
    Может быть полезно для создания связанных записей в БД
    """
    pairs = []
    
    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Пропускаем заголовок CSV
        
        for row in reader:
            if len(row) >= 2:
                russian_term = row[0].strip()
                english_term = row[1].strip()
                pairs.append((russian_term, english_term))
    
    return pairs

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
    embeddings = model.encode(headers)
    print(f"Сгенерировано {len(embeddings)} эмбеддингов")

    with conn, conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {EMBEDDING_TABLE}")
        # Создание таблицы, если не существует
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                embedding VECTOR(384), -- размерность зависит от используемой модели
                language VARCHAR(10) -- 'ru', 'en'
            )
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

def main_with_pairs():
    """
    Альтернативная версия main(), которая сохраняет связи между русскими и английскими терминами
    """
    # Подключение к БД
    conn = psycopg2.connect(
        dbname="gigaoffice",
        user="gigaoffice",
        password="SbConnect~1",
        host="localhost",
        port=5432
    )
    
    model = SentenceTransformer(MODEL_NAME)
    
    # Читаем пары терминов из CSV
    pairs = read_headers_pairs_from_csv(HEADERS_CSV_FILE)
    
    # Собираем все уникальные термины
    all_terms = set()
    for ru_term, en_term in pairs:
        if ru_term:
            all_terms.add(ru_term)
        if en_term:
            all_terms.add(en_term)
    
    headers = sorted(list(all_terms))
    print(f"Найдено {len(headers)} уникальных терминов из {len(pairs)} пар")
    
    # Генерируем эмбеддинги
    embeddings = model.encode(headers)

    with conn, conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {EMBEDDING_TABLE}")

        # Создание основной таблицы эмбеддингов
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                embedding VECTOR(384),
                language VARCHAR(2)
            )
            """
        )
        
        # Создание таблицы связей между терминами
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS header_translations (
                id SERIAL PRIMARY KEY,
                russian_term TEXT,
                english_term TEXT,
                UNIQUE(russian_term, english_term)
            )
            """
        )
        
        import re
        
        # Вставляем эмбеддинги
        inserted_embeddings = 0
        for header, emb in zip(headers, embeddings):
            language = 'ru' if re.search(r'[а-яё]', header.lower()) else 'en'
            
            cur.execute(
                f"""INSERT INTO {EMBEDDING_TABLE} (header, embedding, language) 
                   VALUES (%s, %s, %s) ON CONFLICT (header) DO NOTHING""",
                (header, emb.tolist(), language)
            )
            
            if cur.rowcount > 0:
                inserted_embeddings += 1
        
        # Вставляем связи между терминами
        inserted_translations = 0
        for ru_term, en_term in pairs:
            if ru_term or en_term:  # Хотя бы один термин должен быть не пустым
                cur.execute(
                    """INSERT INTO header_translations (russian_term, english_term) 
                       VALUES (%s, %s) ON CONFLICT (russian_term, english_term) DO NOTHING""",
                    (ru_term if ru_term else None, en_term if en_term else None)
                )
                
                if cur.rowcount > 0:
                    inserted_translations += 1
    
    print(f"Загружено {inserted_embeddings} новых эмбеддингов")
    print(f"Загружено {inserted_translations} новых переводов")

if __name__ == "__main__":
    # Выберите нужную версию:
    main()  # Простая версия - только эмбеддинги
    #main_with_pairs()  # Расширенная версия - эмбеддинги + связи между терминами