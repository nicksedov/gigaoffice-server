import os
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger

# Read DB_SCHEMA environment variable
schema = os.getenv("DB_SCHEMA", "").strip()

# Create metadata with schema if configured
if schema:
    logger.info(f"Configuring ORM Base with schema: {schema}")
    metadata = MetaData(schema=schema)
    Base = declarative_base(metadata=metadata)
else:
    logger.info("Configuring ORM Base with default schema (public)")
    Base = declarative_base()