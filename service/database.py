"""
GigaOffice Service Database Configuration
Настройка подключения к PostgreSQL базе данных
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from models import Base

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://gigaoffice:gigaoffice_password@localhost:5432/gigaoffice_db"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Number of connections to maintain
    max_overflow=30,  # Maximum overflow connections
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"  # SQL logging
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Metadata for migrations
metadata = MetaData()

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """Создание всех таблиц"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Удаление всех таблиц (только для тестирования)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def check_connection(self) -> bool:
        """Проверка подключения к базе данных"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_db_info(self) -> dict:
        """Получение информации о базе данных"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT 
                        version() as version,
                        current_database() as database_name,
                        current_user as current_user,
                        inet_server_addr() as server_addr,
                        inet_server_port() as server_port
                """)).fetchone()
                
                return {
                    "version": result.version,
                    "database_name": result.database_name,
                    "current_user": result.current_user,
                    "server_addr": result.server_addr,
                    "server_port": result.server_port,
                    "pool_size": self.engine.pool.size(),
                    "checked_out": self.engine.pool.checkedout(),
                    "overflow": self.engine.pool.overflow(),
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

# Create database manager instance
db_manager = DatabaseManager()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии базы данных
    Используется в FastAPI для dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией базы данных
    Использовать в сервисах и утилитах
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        db.close()

class DatabaseRepository:
    """Базовый класс для репозиториев работы с базой данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def commit(self):
        """Коммит транзакции"""
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Commit error: {e}")
            raise
    
    def rollback(self):
        """Откат транзакции"""
        self.db.rollback()
    
    def refresh(self, obj):
        """Обновление объекта из базы данных"""
        self.db.refresh(obj)
    
    def add(self, obj):
        """Добавление объекта в сессию"""
        self.db.add(obj)
    
    def delete(self, obj):
        """Удаление объекта"""
        self.db.delete(obj)
    
    def execute_raw_sql(self, sql: str, params: dict = None):
        """Выполнение сырого SQL запроса"""
        try:
            return self.db.execute(sql, params or {})
        except SQLAlchemyError as e:
            logger.error(f"Raw SQL execution error: {e}")
            raise

def init_database():
    """Инициализация базы данных при запуске приложения"""
    try:
        logger.info("Initializing database...")
        
        # Check connection
        if not db_manager.check_connection():
            raise Exception("Cannot connect to database")
        
        # Create tables
        db_manager.create_tables()
        
        # Initialize default data
        init_default_data()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def init_default_data():
    """Инициализация базовых данных"""
    try:
        with get_db_session() as db:
            from models import Prompt, User
            from passlib.context import CryptContext
            
            # Create password context
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Check if admin user exists
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                # Create admin user
                admin_user = User(
                    username="admin",
                    email="admin@gigaoffice.com",
                    hashed_password=pwd_context.hash("admin123"),
                    full_name="System Administrator",
                    role="admin"
                )
                db.add(admin_user)
                logger.info("Admin user created")
            
            # Check if default prompts exist
            existing_prompts = db.query(Prompt).count()
            if existing_prompts == 0:
                # Create default prompts
                default_prompts = [
                    Prompt(
                        name="Анализ данных",
                        description="Анализ табличных данных с выводами",
                        template="Проанализируй данные в таблице. Предоставь краткую сводку основных показателей, найди закономерности и предложи выводы в табличном формате.",
                        category="analysis",
                        language="ru"
                    ),
                    Prompt(
                        name="Генерация данных",
                        description="Генерация тестовых данных",
                        template="Сгенерируй тестовые данные для таблицы. Создай реалистичные данные с указанными колонками и количеством строк.",
                        category="generation",
                        language="ru"
                    ),
                    Prompt(
                        name="Преобразование данных",
                        description="Очистка и преобразование данных",
                        template="Преобразуй данные из таблицы в нужный формат. Очисти, структурируй и приведи к единому стандарту.",
                        category="transformation",
                        language="ru"
                    ),
                    Prompt(
                        name="Создание отчета",
                        description="Формирование структурированного отчета",
                        template="На основе данных создай структурированный отчет с выводами и рекомендациями в табличном виде.",
                        category="reporting",
                        language="ru"
                    ),
                    Prompt(
                        name="Топ-5 торговых центров",
                        description="Данные о крупнейших торговых центрах мира",
                        template='Предоставь данные по пяти самым большим торговым центрам в мире. Ответ должен содержать колонки: "Страна", "Город", "Название ТЦ", "Площадь в кв. м.". Добавь в конец итоговую строку (слово "ИТОГО" добавь в колонку "Страна"), в которой будет указываться сумма значений по колонкам "Площадь в кв. м."',
                        category="data_examples",
                        language="ru"
                    ),
                    Prompt(
                        name="Financial Analysis",
                        description="Financial data analysis template",
                        template="Analyze the financial data in the table. Provide key metrics, trends, and insights in a structured tabular format.",
                        category="analysis",
                        language="en"
                    )
                ]
                
                for prompt in default_prompts:
                    db.add(prompt)
                
                logger.info(f"Created {len(default_prompts)} default prompts")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Error initializing default data: {e}")
        raise

# Database health check functions
def check_database_health() -> dict:
    """Проверка состояния базы данных для health check"""
    try:
        start_time = time.time()
        is_connected = db_manager.check_connection()
        response_time = time.time() - start_time
        
        if is_connected:
            db_info = db_manager.get_db_info()
            return {
                "status": "healthy",
                "response_time": response_time,
                "connection_pool": {
                    "size": db_info.get("pool_size", 0),
                    "checked_out": db_info.get("checked_out", 0),
                    "overflow": db_info.get("overflow", 0)
                }
            }
        else:
            return {
                "status": "unhealthy",
                "response_time": response_time,
                "error": "Cannot connect to database"
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Import for time module
import time