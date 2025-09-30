import psycopg2
import csv
from sentence_transformers import SentenceTransformer
import re
from typing import Optional
from loguru import logger


HEADERS_CSV_FILE = "common_headers.csv"
EMBEDDING_TABLE = "header_embeddings"

MODEL_NAME = "ai-forever/FRIDA"
MODEL_DIMENSION=1536

"""
Lemmatization Service
Service for text lemmatization for Russian language
"""


try:
    from pymystem3 import Mystem
    MYSTEM_AVAILABLE = True
except ImportError:
    MYSTEM_AVAILABLE = False
    logger.warning("pymystem3 not available, Russian lemmatization will be disabled")

class LemmatizationError(Exception):
    """Exception raised for errors in the lemmatization process"""
    pass

class MystemLemmatizer:
    """Implementation using pymystem3 for Russian text lemmatization"""
    
    def __init__(self):
        """Initialize the Russian lemmatizer"""
        if not MYSTEM_AVAILABLE:
            raise LemmatizationError("pymystem3 not available")
        self.mystem = Mystem()
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize Russian text
        
        Args:
            text: Text to lemmatize
            
        Returns:
            Lemmatized text
        """
        try:
            # Mystem returns a list, we join it back to a string
            lemmatized = self.mystem.lemmatize(text)
            # Remove newline characters that Mystem sometimes adds
            result = ''.join(lemmatized).strip()
            return result
        except Exception as e:
            logger.error(f"Error during Russian lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize Russian text: {e}")

class LemmatizationService:
    """Unified interface for lemmatizing text with language detection"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the lemmatization service
        
        Args:
            config: Configuration dictionary with lemmatization settings
        """
        # Initialize lemmatizers
        self._lemmatizer = None

        try:
            if MYSTEM_AVAILABLE:
                self._lemmatizer = MystemLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize text
        
        Args:
            text: Text to lemmatize
            
        Returns:
            lemmatized_text
        """
     
        # Return early if text is empty
        if not text.strip():
            return text
        
        try:
            return self._lemmatizer.lemmatize(text)
            
        except Exception as e:
            logger.error(f"Error during lemmatization: {e}")
            # Fallback to original text in case of error
            return text

# Create singleton instance
lemmatization_service = LemmatizationService()

# =======================================================================
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
    
    # Generate lemmatized versions of headers and determine languages
    lemmatized_headers = []
    languages = []
    
    for header in headers:
        # Determine language
        language = 'ru' if re.search(r'[а-яё]', header.lower()) else 'en'
        languages.append(language)
        
        # Lemmatize header
        if language == 'ru':
            lemmatized_header = lemmatization_service.lemmatize(header)
            lemmatized_headers.append(lemmatized_header)
        else:
            lemmatized_headers.append(header)
    
    # Генерируем эмбеддинги from lemmatized headers instead of raw headers
    embeddings = model.encode(lemmatized_headers, normalize_embeddings=True)
    print(f"Сгенерировано {len(embeddings)} эмбеддингов")

    with conn, conn.cursor() as cur:
        print(f"Создаем таблицу {EMBEDDING_TABLE}...")
        cur.execute(f"""
            DROP TABLE IF EXISTS {EMBEDDING_TABLE};
            
            CREATE TABLE {EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                header TEXT UNIQUE NOT NULL,
                lemmatized_header TEXT,
                embedding VECTOR({MODEL_DIMENSION}), -- размерность зависит от используемой модели
                language VARCHAR(2) -- 'ru', 'en'
            );
            """
        )
        
        print(f"Заполняем таблицу {EMBEDDING_TABLE} значениями...")
        inserted_count = 0
        for header, lemmatized_header, emb, language in zip(headers, lemmatized_headers, embeddings, languages):
            cur.execute(
                f"""INSERT INTO {EMBEDDING_TABLE} (header, lemmatized_header, embedding, language) 
                   VALUES (%s, %s, %s, %s) ON CONFLICT (header) DO NOTHING""",
                (header, lemmatized_header, emb.tolist(), language)
            )
            
            # Проверяем, была ли вставлена запись
            if cur.rowcount > 0:
                inserted_count += 1
    
        print(f"Создаем индексы таблицы {EMBEDDING_TABLE}...")
        cur.execute(f"""
            CREATE INDEX {EMBEDDING_TABLE}_idx_embedding_l2 ON {EMBEDDING_TABLE} USING ivfflat (embedding vector_l2_ops);
            CREATE INDEX {EMBEDDING_TABLE}_idx_embedding_cos ON {EMBEDDING_TABLE} USING ivfflat (embedding vector_cosine_ops);
            CREATE INDEX {EMBEDDING_TABLE}_idx_lemmatized_header ON {EMBEDDING_TABLE} (lemmatized_header);
            """
        )

    print(f"Загружено {inserted_count} новых эмбеддингов в таблицу {EMBEDDING_TABLE}")
    print(f"Всего в таблице: {len(headers)} терминов")

if __name__ == "__main__":
    main()