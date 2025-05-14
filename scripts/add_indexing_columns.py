"""
Script to add indexing-related columns to the Webpage table.

This script adds is_indexed and indexed_at columns to support tracking
which documents have been processed by the RAG indexer.
"""

import asyncio
import sys
import os
import logging
from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.declarative import declarative_base

# Add project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.models.webpage import Webpage
from app.db.models.document import Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_columns():
    """Add the indexing-related columns to the Webpage table."""
    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/govstackdb")
    
    # Handle Windows-specific issue with localhost
    if "localhost" in database_url and os.name == "nt":
        database_url = database_url.replace("localhost", "127.0.0.1")
    
    logger.info(f"Connecting to database: {database_url}")
    
    # Create engine
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Check if columns already exist
        has_is_indexed = False
        has_indexed_at = False
        
        try:
            # Try to get column info
            result = await conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'webpages' AND column_name IN ('is_indexed', 'indexed_at')")
            existing_columns = [row[0] for row in result.fetchall()]
            
            has_is_indexed = 'is_indexed' in existing_columns
            has_indexed_at = 'indexed_at' in existing_columns
            
            logger.info(f"Existing columns check - is_indexed: {has_is_indexed}, indexed_at: {has_indexed_at}")
        
        except Exception as e:
            logger.error(f"Error checking existing columns: {e}")
            raise
        
        # Add columns if they don't exist
        try:
            if not has_is_indexed:
                logger.info("Adding is_indexed column...")
                await conn.execute("ALTER TABLE webpages ADD COLUMN is_indexed BOOLEAN NOT NULL DEFAULT FALSE")
                logger.info("Added is_indexed column")
            
            if not has_indexed_at:
                logger.info("Adding indexed_at column...")
                await conn.execute("ALTER TABLE webpages ADD COLUMN indexed_at TIMESTAMP WITH TIME ZONE")
                logger.info("Added indexed_at column")
            
            logger.info("Database update completed successfully")
            
        except Exception as e:
            logger.error(f"Error adding columns: {e}")
            raise

if __name__ == "__main__":
    try:
        asyncio.run(add_columns())
        logger.info("Script completed successfully.")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)
