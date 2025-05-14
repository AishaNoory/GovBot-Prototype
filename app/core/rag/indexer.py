"""
Indexer module for extracting text content from crawled webpages.
This module provides functions to retrieve and process text content
for use in Retrieval Augmented Generation (RAG) systems.
"""

import logging
import os
import asyncio
import nest_asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union, Tuple, Any
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
import chromadb

from app.db.models.webpage import Webpage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_texts_by_collection(
    db: AsyncSession,
    collection_id: str,
    hours_ago: Optional[int] = 24,
    include_title: bool = True,
    include_url: bool = True
) -> List[Dict[str, str]]:
    """
    Extract text content from webpages in a specific collection that were
    crawled within the specified time period.
    
    Args:
        db: Database session
        collection_id: The collection ID to filter by
        hours_ago: Extract pages from the last N hours (None for all)
        include_title: Whether to include the webpage title in the result
        include_url: Whether to include the webpage URL in the result
        
    Returns:
        List of dictionaries containing webpage content and metadata
    """
    try:
        # Build query base with collection filter
        query = select(Webpage).where(Webpage.collection_id == collection_id)
        
        # Add time filter if hours_ago is specified
        if hours_ago is not None:
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
            query = query.where(Webpage.last_crawled >= time_threshold)
        
        # Execute query
        result = await db.execute(query)
        webpages = result.scalars().all()
        
        # Process results
        texts = []
        for webpage in webpages:
            if not webpage.content_markdown:
                continue
                
            webpage_data = {}
            
            # Add metadata if requested
            if include_title and webpage.title:
                webpage_data["title"] = webpage.title
            
            if include_url:
                webpage_data["url"] = webpage.url
            
            # Add content
            webpage_data["content"] = webpage.content_markdown
            webpage_data["id"] = webpage.id
            webpage_data["last_crawled"] = webpage.last_crawled.isoformat() if webpage.last_crawled else None
            
            texts.append(webpage_data)
        
        logger.info(f"Extracted {len(texts)} texts from collection '{collection_id}'")
        return texts
    
    except Exception as e:
        logger.error(f"Error extracting texts from collection '{collection_id}': {e}")
        raise

async def extract_text_batch(
    db: AsyncSession,
    collection_id: str,
    hours_ago: Optional[int] = 24,
    output_format: str = "text"
) -> Union[str, List[Dict[str, str]]]:
    """
    Extract and format text content from webpages in a specific collection.
    
    Args:
        db: Database session
        collection_id: The collection ID to filter by
        hours_ago: Extract pages from the last N hours (None for all)
        output_format: Format for the output ("text", "json", "markdown")
        
    Returns:
        Formatted content based on output_format
    """
    texts = await extract_texts_by_collection(
        db=db, 
        collection_id=collection_id,
        hours_ago=hours_ago,
        include_title=True,
        include_url=True
    )
    
    if output_format == "json":
        return texts
    
    elif output_format == "markdown":
        # Format as markdown with document separators
        markdown_content = ""
        for item in texts:
            markdown_content += f"# {item.get('title', 'Untitled Document')}\n"
            markdown_content += f"Source: {item.get('url', 'Unknown')}\n\n"
            markdown_content += f"{item.get('content', '')}\n\n"
            markdown_content += "---\n\n"
        return markdown_content
    
    else:  # Default to raw text
        text_content = ""
        for item in texts:
            if item.get('title'):
                text_content += f"{item['title']}\n\n"
            text_content += f"{item.get('content', '')}\n\n"
            text_content += "------\n\n"
        return text_content

async def get_collection_stats(
    db: AsyncSession,
    collection_id: Optional[str] = None
) -> Dict[str, any]:
    """
    Get statistics about collections or a specific collection.
    
    Args:
        db: Database session
        collection_id: Optional collection ID to filter by
        
    Returns:
        Dictionary of collection statistics
    """
    try:
        if collection_id:
            # Stats for a specific collection
            query = select(Webpage).where(Webpage.collection_id == collection_id)
            result = await db.execute(query)
            webpages = result.scalars().all()
            
            # Find earliest and latest crawl dates
            earliest_crawl = None
            latest_crawl = None
            total_characters = 0
            
            for webpage in webpages:
                if webpage.content_markdown:
                    total_characters += len(webpage.content_markdown)
                
                if webpage.first_crawled:
                    if earliest_crawl is None or webpage.first_crawled < earliest_crawl:
                        earliest_crawl = webpage.first_crawled
                
                if webpage.last_crawled:
                    if latest_crawl is None or webpage.last_crawled > latest_crawl:
                        latest_crawl = webpage.last_crawled
            
            return {
                "collection_id": collection_id,
                "webpage_count": len(webpages),
                "total_characters": total_characters,
                "earliest_crawl": earliest_crawl.isoformat() if earliest_crawl else None,
                "latest_crawl": latest_crawl.isoformat() if latest_crawl else None
            }
        else:
            # Stats for all collections
            from sqlalchemy import func
            
            # Get distinct collection IDs
            query = select(Webpage.collection_id, func.count(Webpage.id).label("count")).\
                group_by(Webpage.collection_id)
            result = await db.execute(query)
            collections = result.fetchall()
            
            collection_stats = []
            for coll_id, count in collections:
                if coll_id:  # Skip None values
                    collection_stats.append({
                        "collection_id": coll_id,
                        "webpage_count": count
                    })
            
            return {
                "total_collections": len(collection_stats),
                "collections": collection_stats
            }
    
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

from llama_index.core import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter, MarkdownElementNodeParser
from llama_index.core.extractors import TitleExtractor
from llama_index.core.ingestion import IngestionPipeline, IngestionCache

import chromadb

from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.chroma import ChromaVectorStore

from llama_index.core import StorageContext

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Update the DATABASE_URL directly in the code
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/govstackdb")

# This code is already present, which is good, but ensure it works correctly
if "localhost" in DATABASE_URL and os.name == "nt":  # Windows-specific fix
    # Replace localhost with 127.0.0.1 on Windows to avoid DNS resolution issues
    DATABASE_URL = DATABASE_URL.replace("localhost", "127.0.0.1")

try:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

async def get_unindexed_documents(
    db: AsyncSession,
    collection_id: str
) -> List[Dict[str, str]]:
    """
    Get all unindexed documents for a specific collection.
    
    Args:
        db: Database session
        collection_id: The collection ID to filter by
        
    Returns:
        List of dictionaries containing webpage content and metadata
    """
    try:
        # Build query to get unindexed documents in this collection
        query = select(Webpage).where(
            and_(
                Webpage.collection_id == collection_id,
                Webpage.is_indexed == False,
                Webpage.content_markdown != None
            )
        )
        
        # Execute query
        result = await db.execute(query)
        webpages = result.scalars().all()
        
        # Process results
        texts = []
        for webpage in webpages:
            webpage_data = {
                "id": webpage.id,
                "url": webpage.url,
                "title": webpage.title or "",
                "content": webpage.content_markdown,
                "last_crawled": webpage.last_crawled.isoformat() if webpage.last_crawled else None,
            }
            texts.append(webpage_data)
        
        logger.info(f"Found {len(texts)} unindexed documents in collection '{collection_id}'")
        return texts
    
    except Exception as e:
        logger.error(f"Error getting unindexed documents from collection '{collection_id}': {e}")
        raise

async def mark_documents_as_indexed(
    db: AsyncSession,
    document_ids: List[int]
) -> None:
    """
    Mark documents as indexed in the database.
    
    Args:
        db: Database session
        document_ids: List of document IDs to mark as indexed
    """
    if not document_ids:
        return
        
    try:
        now = datetime.now(timezone.utc)
        
        # Update documents in batches to avoid memory issues with large sets
        batch_size = 100
        for i in range(0, len(document_ids), batch_size):
            batch_ids = document_ids[i:i+batch_size]
            
            # Use update with IN clause
            stmt = update(Webpage).where(
                Webpage.id.in_(batch_ids)
            ).values(
                is_indexed=True, 
                indexed_at=now
            )
            
            await db.execute(stmt)
            await db.commit()
            
        logger.info(f"Marked {len(document_ids)} documents as indexed")
    
    except Exception as e:
        logger.error(f"Error marking documents as indexed: {e}")
        await db.rollback()
        raise

async def setup_vector_store(collection_name: str):
    """
    Set up a vector store for document indexing.
    
    Args:
        collection_name: Name for the ChromaDB collection
        
    Returns:
        Tuple of (vector_store, pipeline)
    """
    try:
        # Connect to ChromaDB
        remote_db = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", "8050"))
        )

        # Get or create collection
        chroma_collection = remote_db.get_or_create_collection(
            name=collection_name
        )

        # Set up vector store and storage context
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Create the pipeline with transformations
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=1024, chunk_overlap=200),
                OpenAIEmbedding(
                    model="text-embedding-3-small",
                    chunk_size=64,
                ),
            ],
            vector_store=vector_store,
        )
        
        return vector_store, pipeline
    
    except Exception as e:
        logger.error(f"Error setting up vector store: {e}")
        raise

async def index_documents_by_collection(collection_id: str) -> Dict[str, Any]:
    """
    Index all unindexed documents in a collection.
    
    Args:
        collection_id: The collection ID to process
        
    Returns:
        Dictionary of indexing statistics
    """
    start_time = datetime.now(timezone.utc)
    stats = {
        "collection_id": collection_id,
        "start_time": start_time.isoformat(),
        "documents_processed": 0,
        "documents_indexed": 0,
        "status": "started"
    }
    
    try:
        # Connect to the database
        async with async_session_maker() as db:
            # Get unindexed documents
            documents = await get_unindexed_documents(db, collection_id)
            
            if not documents:
                logger.info(f"No unindexed documents found in collection '{collection_id}'")
                stats.update({
                    "status": "completed",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "message": "No unindexed documents found"
                })
                return stats
            
            # Set up vector store
            vector_store, pipeline = await setup_vector_store(collection_id)
            
            # Convert dictionary documents to Document objects
            doc_objects = [
                Document(
                    text=doc.get("content", ""),
                    metadata={
                        "title": doc.get("title", ""),
                        "url": doc.get("url", ""),
                        "doc_id": doc.get("id", ""),
                        "last_crawled": doc.get("last_crawled", "")
                    }
                ) for doc in documents
            ]
            
            # Track document IDs for marking as indexed
            document_ids = [doc.get("id") for doc in documents]
            stats["documents_processed"] = len(document_ids)
            
            # Run the pipeline
            nodes = pipeline.run(
                documents=doc_objects,
                show_progress=True,
            )
            
            # Create the index
            index = VectorStoreIndex(nodes)
            
            # Mark documents as indexed
            await mark_documents_as_indexed(db, document_ids)
            stats["documents_indexed"] = len(document_ids)
            
            # Update stats
            end_time = datetime.now(timezone.utc)
            stats.update({
                "status": "completed",
                "end_time": end_time.isoformat(),
                "processing_time_seconds": (end_time - start_time).total_seconds()
            })
            
            logger.info(f"Successfully indexed {len(document_ids)} documents in collection '{collection_id}'")
            return stats
    
    except Exception as e:
        logger.error(f"Error indexing documents in collection '{collection_id}': {e}")
        stats.update({
            "status": "failed",
            "error": str(e),
            "end_time": datetime.now(timezone.utc).isoformat()
        })
        return stats

def start_background_indexing(collection_id: str) -> None:
    """
    Start background indexing for a collection.
    
    This function runs the indexing process in a background task.
    It should be called after a crawl is completed.
    
    Args:
        collection_id: The collection ID to process
    """
    async def _run_indexing():
        try:
            logger.info(f"Starting background indexing for collection '{collection_id}'")
            result = await index_documents_by_collection(collection_id)
            logger.info(f"Background indexing completed for collection '{collection_id}': {result['status']}")
        except Exception as e:
            logger.error(f"Error in background indexing for collection '{collection_id}': {e}")
    
    # Create and start the task
    asyncio.create_task(_run_indexing())
    logger.info(f"Scheduled background indexing task for collection '{collection_id}'")

