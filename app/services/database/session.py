"""
Database Session Management
Context managers and dependencies for database sessions
"""

import time
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from app.services.database.manager import db_manager
from app.resource_loader import resource_loader

def _get_db_session_base(auto_commit: bool = False) -> Generator[Session, None, None]:
    """
    Base function for database session management
    :param auto_commit: Whether to automatically commit transactions on success
    """
    db = db_manager.SessionLocal()
    try:
        yield db
        if auto_commit:
            db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Database transaction error" if auto_commit else "Database session error"
        logger.error(f"{error_msg}: {e}")
        raise
    finally:
        db.close()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии базы данных
    Используется в FastAPI для dependency injection
    """
    # Delegate to the base function without auto-commit
    generator = _get_db_session_base(auto_commit=False)
    yield from generator

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией базы данных
    Использовать в сервисах и утилитах
    """
    # Delegate to the base function with auto-commit
    generator = _get_db_session_base(auto_commit=True)
    yield from generator

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
            from app.model_orm import Prompt, User, Category
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

            # Initialize categories
            categories_data = resource_loader.load_json("prompts/prompt_categories.json")
            existing_categories = db.query(Category).count()
            
            if existing_categories == 0:
                category_map = {}
                for category_data in categories_data:
                    category = Category(**category_data)
                    db.add(category)
                    db.flush()  # Получаем ID
                    category_map[category.name] = category.id
                
                logger.info(f"Created {len(categories_data)} categories")
                
                # Create default prompts with category_id
                default_prompts_data = resource_loader.load_json("prompts/default_prompts.json")
                
                existing_prompts = db.query(Prompt).count()
                if existing_prompts == 0:
                    for prompt_data in default_prompts_data:
                        category_name = prompt_data.get('category')
                        category_id = category_map.get(category_name) if category_name else None
                        
                        # Создаем промпт только с category_id
                        prompt = Prompt(
                            name=prompt_data['name'],
                            description=prompt_data.get('description'),
                            template=prompt_data['template'],
                            category_id=category_id
                        )
                        db.add(prompt)
                    
                    logger.info(f"Created {len(default_prompts_data)} default prompts")
            else:
                # Миграция существующих промптов: перенос category -> category_id
                category_map = {cat.name: cat.id for cat in db.query(Category).all()}
                
                # Находим промпты, которые еще не имеют category_id
                prompts_to_migrate = db.query(Prompt).filter(
                    Prompt.category_id.is_(None)
                ).all()
                
                migrated_count = 0
                for prompt in prompts_to_migrate:
                    # Пытаемся найти category_id по старому полю category
                    if hasattr(prompt, 'category') and prompt.category in category_map:
                        prompt.category_id = category_map[prompt.category]
                        migrated_count += 1
                
                if migrated_count > 0:
                    logger.info(f"Migrated {migrated_count} prompts to use category_id")
            
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