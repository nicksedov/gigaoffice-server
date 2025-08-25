"""
Database Session Management
Enhanced database connection and session handling with improved error handling and pooling
"""

import time
from contextlib import contextmanager
from typing import Generator, Dict, Any, Optional
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from loguru import logger

from ..core.config import get_settings, load_config_file, app_state
from ..utils.logger import structured_logger


class DatabaseManager:
    """Enhanced database manager with improved connection handling"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self.metadata = MetaData()
        self._initialize_engine()
    
    def _get_database_config(self) -> Dict[str, Any]:
        """Get database configuration from settings and config files"""
        # Load from config file
        config = load_config_file("database_config")
        
        # Override with environment variables from settings
        return {
            "host": self.settings.database_url.split("@")[1].split(":")[0] if "@" in self.settings.database_url else config.get("host", "localhost"),
            "port": self.settings.database_url.split(":")[-1].split("/")[0] if ":" in self.settings.database_url else config.get("port", 5432),
            "name": self.settings.database_url.split("/")[-1] if "/" in self.settings.database_url else config.get("name", "gigaoffice"),
            "user": self.settings.database_url.split("://")[1].split(":")[0] if "://" in self.settings.database_url else config.get("user", ""),
            "password": self.settings.database_url.split("://")[1].split("@")[0].split(":")[1] if "://" in self.settings.database_url else config.get("password", ""),
            "pool_size": self.settings.database_pool_size,
            "max_overflow": self.settings.database_max_overflow,
            "pool_timeout": self.settings.database_pool_timeout,
            "echo": self.settings.debug
        }
    
    def _initialize_engine(self):
        """Initialize database engine with connection pooling"""
        try:
            # Use direct database URL if provided, otherwise construct from config
            if self.settings.database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
                database_url = self.settings.database_url
            else:
                config = self._get_database_config()
                database_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['name']}"
            
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_timeout=self.settings.database_pool_timeout,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=self.settings.debug,  # SQL logging in debug mode
                echo_pool=self.settings.debug,  # Pool logging in debug mode
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            from .models import Base
            
            with structured_logger.performance_timer("create_tables"):
                Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database tables created successfully")
            app_state.mark_component_ready("database")
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            app_state.mark_component_failed("database")
            raise
    
    def drop_tables(self):
        """Drop all database tables (for testing only)"""
        try:
            from .models import Base
            
            if not self.settings.is_development:
                raise ValueError("Table dropping is only allowed in development environment")
            
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
            
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def check_connection(self) -> bool:
        """Check database connectivity"""
        try:
            with structured_logger.performance_timer("db_connection_check"):
                with self.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()
            
            app_state.mark_component_ready("database")
            return True
            
        except (SQLAlchemyError, DisconnectionError) as e:
            logger.error(f"Database connection failed: {e}")
            app_state.mark_component_failed("database")
            return False
    
    def get_db_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        try:
            from ..utils.resource_loader import resource_loader
            
            with self.engine.connect() as connection:
                # Load database info query from resources
                sql_query = resource_loader.load_sql("sql/database_info.sql")
                if not sql_query:
                    # Fallback query if resource file not found
                    sql_query = """
                    SELECT 
                        version() as version,
                        current_database() as database_name,
                        current_user as current_user,
                        inet_server_addr() as server_addr,
                        inet_server_port() as server_port
                    """
                
                result = connection.execute(text(sql_query)).fetchone()
                
                # Get connection pool stats
                pool = self.engine.pool
                
                return {
                    "version": result.version if result else "unknown",
                    "database_name": result.database_name if result else "unknown",
                    "current_user": result.current_user if result else "unknown",
                    "server_addr": str(result.server_addr) if result and result.server_addr else "unknown",
                    "server_port": result.server_port if result else "unknown",
                    "pool_size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid(),
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}
    
    async def initialize(self) -> None:
        """
        Initialize database: check connection, create tables, setup default data
        
        This method is called during application startup and performs:
        1. Database connection validation
        2. Table creation if needed
        3. Default data initialization (categories, prompts, admin user)
        
        Raises:
            Exception: If initialization fails
        """
        try:
            logger.info("Starting database initialization...")
            
            # Check database connection
            if not self.check_connection():
                raise Exception("Database connection check failed")
            
            # Create tables if they don't exist
            self.create_tables()
            
            # Initialize default data
            self.init_default_data()
            
            logger.info("Database initialization completed successfully")
            app_state.mark_component_ready("database")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            app_state.mark_component_failed("database")
            raise
    
    async def cleanup(self) -> None:
        """
        Cleanup database connections and resources
        
        This method is called during application shutdown and performs:
        1. Connection pool disposal
        2. Resource cleanup
        """
        try:
            logger.info("Cleaning up database connections...")
            
            if self.engine:
                # Dispose of connection pool
                self.engine.dispose()
                logger.info("Database connection pool disposed")
            
            # Clear cache and reset state
            app_state.mark_component_shutdown("database")
            
        except Exception as e:
            logger.error(f"Database cleanup error: {e}")
    
    def init_default_data(self) -> None:
        """
        Initialize default categories, prompts, and admin user
        
        This method sets up the basic data required for the application:
        - Default prompt categories
        - Default prompt templates  
        - System administrator account
        
        Raises:
            Exception: If data initialization fails
        """
        try:
            from ..utils.resource_loader import resource_loader
            from .models import Prompt, User, Category
            from passlib.context import CryptContext
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            with get_db_session() as db:
                # Create admin user if doesn't exist
                admin_user = db.query(User).filter(User.username == "admin").first()
                if not admin_user:
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
                category_map = self._create_default_categories(db, resource_loader)
                
                # Create default prompts
                self._create_default_prompts(db, resource_loader, category_map)
                
                # Migrate legacy data if needed
                self._migrate_legacy_data(db)
                
                db.commit()
                logger.info("Default data initialization completed")
                
        except Exception as e:
            logger.error(f"Error initializing default data: {e}")
            raise
    
    def _create_default_categories(self, db: Session, resource_loader) -> Dict[str, int]:
        """
        Create default prompt categories and return name->id mapping
        
        Args:
            db: Database session
            resource_loader: Resource loader instance
            
        Returns:
            Dictionary mapping category names to IDs
        """
        from .models import Category
        
        categories_data = resource_loader.load_json("prompts/prompt_categories.json")
        existing_categories = db.query(Category).count()
        category_map = {}
        
        if existing_categories == 0 and categories_data:
            for category_data in categories_data:
                category = Category(**category_data)
                db.add(category)
                db.flush()  # Get ID
                category_map[category.name] = category.id
            
            logger.info(f"Created {len(categories_data)} categories")
        else:
            # Build mapping from existing categories
            category_map = {cat.name: cat.id for cat in db.query(Category).all()}
        
        return category_map
    
    def _create_default_prompts(self, db: Session, resource_loader, 
                               category_map: Dict[str, int]) -> None:
        """
        Create default prompt templates with category associations
        
        Args:
            db: Database session
            resource_loader: Resource loader instance
            category_map: Category name to ID mapping
        """
        from .models import Prompt
        
        default_prompts_data = resource_loader.load_json("prompts/default_prompts.json")
        existing_prompts = db.query(Prompt).count()
        
        if existing_prompts == 0 and default_prompts_data:
            for prompt_data in default_prompts_data:
                category_name = prompt_data.get('category')
                category_id = category_map.get(category_name) if category_name else None
                
                prompt = Prompt(
                    name=prompt_data['name'],
                    description=prompt_data.get('description'),
                    template=prompt_data['template'],
                    category_id=category_id
                )
                db.add(prompt)
            
            logger.info(f"Created {len(default_prompts_data)} default prompts")
    
    def _migrate_legacy_data(self, db: Session) -> None:
        """
        Handle backward compatibility for legacy data
        
        Args:
            db: Database session
        """
        from .models import Prompt, Category
        
        # Migrate existing prompts to use category_id
        category_map = {cat.name: cat.id for cat in db.query(Category).all()}
        prompts_to_migrate = db.query(Prompt).filter(Prompt.category_id.is_(None)).all()
        
        migrated_count = 0
        for prompt in prompts_to_migrate:
            if hasattr(prompt, 'category') and prompt.category in category_map:
                prompt.category_id = category_map[prompt.category]
                migrated_count += 1
        
        if migrated_count > 0:
            logger.info(f"Migrated {migrated_count} prompts to use category_id")
    
    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for getting database session
    Automatically handles rollback on exceptions
    """
    db = db_manager.get_session()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        structured_logger.log_error(e, {"component": "database", "operation": "session"})
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database session in services
    Automatically commits on success, rolls back on exception
    """
    db = db_manager.get_session()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        structured_logger.log_error(e, {"component": "database", "operation": "transaction"})
        raise
    finally:
        db.close()


class DatabaseRepository:
    """Base repository class with common database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def commit(self):
        """Commit current transaction"""
        try:
            self.db.commit()
            structured_logger.log_database_operation("COMMIT", "transaction", 0)
        except SQLAlchemyError as e:
            self.db.rollback()
            structured_logger.log_error(e, {"component": "database", "operation": "commit"})
            raise
    
    def rollback(self):
        """Rollback current transaction"""
        self.db.rollback()
        structured_logger.log_database_operation("ROLLBACK", "transaction", 0)
    
    def refresh(self, obj):
        """Refresh object from database"""
        self.db.refresh(obj)
    
    def add(self, obj):
        """Add object to session"""
        self.db.add(obj)
    
    def delete(self, obj):
        """Delete object from database"""
        self.db.delete(obj)
    
    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None):
        """Execute raw SQL query with performance tracking"""
        start_time = time.time()
        try:
            result = self.db.execute(text(sql), params or {})
            duration = time.time() - start_time
            structured_logger.log_database_operation("RAW_SQL", "custom", duration)
            return result
        except SQLAlchemyError as e:
            duration = time.time() - start_time
            structured_logger.log_database_operation("RAW_SQL_ERROR", "custom", duration)
            structured_logger.log_error(e, {"sql": sql, "params": params})
            raise


def init_database():
    """Initialize database on application startup"""
    try:
        logger.info("Initializing database...")
        
        # Check connection
        if not db_manager.check_connection():
            raise Exception("Cannot connect to database")
        
        # Create tables
        db_manager.create_tables()
        
        # Initialize default data
        _init_default_data()
        
        logger.info("Database initialized successfully")
        app_state.mark_component_ready("database")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        app_state.mark_component_failed("database")
        raise


def _init_default_data():
    """Initialize default data (admin user, categories, prompts)"""
    try:
        from ..utils.resource_loader import resource_loader
        from .models import Prompt, User, Category
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        with get_db_session() as db:
            # Create admin user if doesn't exist
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
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
            
            if existing_categories == 0 and categories_data:
                category_map = {}
                for category_data in categories_data:
                    category = Category(**category_data)
                    db.add(category)
                    db.flush()  # Get ID
                    category_map[category.name] = category.id
                
                logger.info(f"Created {len(categories_data)} categories")
                
                # Create default prompts
                default_prompts_data = resource_loader.load_json("prompts/default_prompts.json")
                if default_prompts_data:
                    for prompt_data in default_prompts_data:
                        category_name = prompt_data.get('category')
                        category_id = category_map.get(category_name) if category_name else None
                        
                        prompt = Prompt(
                            name=prompt_data['name'],
                            description=prompt_data.get('description'),
                            template=prompt_data['template'],
                            category_id=category_id
                        )
                        db.add(prompt)
                    
                    logger.info(f"Created {len(default_prompts_data)} default prompts")
            
            # Migration: update existing prompts to use category_id
            if existing_categories > 0:
                category_map = {cat.name: cat.id for cat in db.query(Category).all()}
                prompts_to_migrate = db.query(Prompt).filter(Prompt.category_id.is_(None)).all()
                
                migrated_count = 0
                for prompt in prompts_to_migrate:
                    if hasattr(prompt, 'category') and prompt.category in category_map:
                        prompt.category_id = category_map[prompt.category]
                        migrated_count += 1
                
                if migrated_count > 0:
                    logger.info(f"Migrated {migrated_count} prompts to use category_id")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Error initializing default data: {e}")
        raise


def check_database_health() -> Dict[str, Any]:
    """Check database health for health endpoints"""
    try:
        start_time = time.time()
        is_connected = db_manager.check_connection()
        response_time = time.time() - start_time
        
        if is_connected:
            db_info = db_manager.get_db_info()
            return {
                "status": "healthy",
                "response_time": response_time,
                "database_info": db_info,
                "connection_pool": {
                    "size": db_info.get("pool_size", 0),
                    "checked_out": db_info.get("checked_out", 0),
                    "overflow": db_info.get("overflow", 0),
                    "invalid": db_info.get("invalid", 0)
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