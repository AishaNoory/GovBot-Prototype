# Data Architecture & Production Deployment for GovStack
**Presented by: Paul Wanjohi**
**THiNK eCitizen Technical Exchange Workshop**
**Day 4: Advanced Data Systems and Production Deployment (29 Aug 2025)**

---

Slide 1 — Title & Objectives

- Title: "Production-Grade Data Architecture and Containerized Deployment"
- Objectives:
  - Deep dive into multi-database architecture: PostgreSQL, MinIO, ChromaDB
  - Implement automated backup, disaster recovery, and monitoring systems
  - Deploy production containerized infrastructure with Docker Compose and Kubernetes
  - Build scalable data pipelines with real-time indexing and analytics

Recommended image: Complete infrastructure architecture diagram with all components

---

Slide 2 — Multi-Database Architecture Overview

**Database Strategy & Rationale:**
```yaml
# Data storage architecture
PostgreSQL (Port 5432):
  - Structured relational data
  - ACID compliance for critical operations
  - Advanced indexing and query optimization
  - Real-time analytics support

ChromaDB (Port 8050):
  - Vector embeddings storage
  - Semantic similarity search
  - Collection-based organization
  - Scalable vector operations

MinIO (Ports 9000, 9001):
  - S3-compatible object storage
  - Binary file management
  - Presigned URL generation
  - Bucket lifecycle management
```

**Data Flow Architecture:**
```
Upload → MinIO (Binary Storage) → PostgreSQL (Metadata) → Text Extraction → 
ChromaDB (Vector Indexing) → RAG Retrieval → Analytics Pipeline
```

**Production Configuration:**
```yaml
# docker-compose.yml production settings
services:
  postgres:
    image: postgres:17.5
    environment:
      POSTGRES_MULTIPLE_DATABASES: govstackdb,metabase
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./scripts/postgres-init:/docker-entrypoint-initdb.d
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

Recommended image: Database interaction diagram showing data flow and relationships

---

Slide 3 — PostgreSQL: Advanced Configuration & Optimization

**Production Database Schema:**
```sql
-- Core database tables with advanced indexing
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    object_name VARCHAR(255) UNIQUE NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size INTEGER NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collection_id VARCHAR(64) NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    api_key_name VARCHAR(100) NOT NULL,
    is_indexed BOOLEAN NOT NULL DEFAULT FALSE,
    indexed_at TIMESTAMP WITH TIME ZONE
);

-- Performance optimization indexes
CREATE INDEX CONCURRENTLY idx_documents_collection_indexed 
    ON documents(collection_id, is_indexed, indexed_at);
CREATE INDEX CONCURRENTLY idx_documents_upload_date 
    ON documents(upload_date DESC);
CREATE INDEX CONCURRENTLY idx_documents_created_by_date 
    ON documents(created_by, upload_date);
```

**Advanced PostgreSQL Configuration:**
```ini
# postgresql.conf optimizations
shared_buffers = 256MB                    # 25% of available RAM
effective_cache_size = 1GB                # 75% of available RAM
work_mem = 16MB                          # Per-connection work memory
maintenance_work_mem = 64MB              # Maintenance operations
max_connections = 100                    # Connection limit
random_page_cost = 1.1                  # SSD optimization
effective_io_concurrency = 200          # Concurrent I/O operations

# Write-ahead logging optimization
wal_buffers = 16MB
wal_level = replica
max_wal_size = 2GB
min_wal_size = 80MB
```

**Connection Pooling Implementation:**
```python
# SQLAlchemy async connection pool
DATABASE_URL = "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/govstackdb"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,                        # Core connections
    max_overflow=10,                     # Additional connections
    pool_pre_ping=True,                  # Connection health checks
    pool_recycle=3600,                   # Connection lifetime (1 hour)
    echo=False                           # Disable SQL logging in production
)
```

**Database Partitioning Strategy:**
```sql
-- Partition audit logs by month for performance
CREATE TABLE audit_logs (
    id BIGSERIAL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    -- ... other columns
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE audit_logs_2025_08 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
```

Recommended image: PostgreSQL performance monitoring dashboard

---

Slide 4 — MinIO Object Storage: Production Architecture

**MinIO Production Configuration:**
```yaml
# High-availability MinIO setup
minio:
  image: minio/minio:RELEASE.2025-04-22T22-12-26Z-cpuv1
  environment:
    MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
    MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    MINIO_PROMETHEUS_AUTH_TYPE: public
  volumes:
    - ./data/minio:/data
  command: server /data --console-address ":9001"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 20s
    retries: 3
```

**Bucket Lifecycle Management:**
```python
class MinioClient:
    def __init__(self):
        self.client = Minio(
            f"{self.endpoint}:{self.port}",
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        self._setup_bucket_policies()
    
    def _setup_bucket_policies(self):
        """Configure bucket lifecycle and security policies"""
        
        # Lifecycle policy for automatic cleanup
        lifecycle_config = {
            "Rules": [{
                "ID": "DeleteOldVersions",
                "Status": "Enabled",
                "Expiration": {"Days": 365},
                "NoncurrentVersionExpiration": {"NoncurrentDays": 30}
            }]
        }
        
        # Security policy for bucket access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "AllowGovStackAccess",
                "Effect": "Allow",
                "Principal": {"AWS": [f"arn:aws:iam:::{self.access_key}:root"]},
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
            }]
        }
```

**Presigned URL Security:**
```python
def get_secure_presigned_url(self, object_name: str, expires: int = 3600) -> str:
    """Generate secure presigned URLs with audit logging"""
    
    # Log presigned URL generation for audit
    logger.info(f"Generating presigned URL for {object_name}")
    
    try:
        url = self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=expires),
            response_headers={
                'response-content-disposition': f'attachment; filename="{object_name}"'
            }
        )
        
        # Audit log the URL generation
        await self.log_url_generation(object_name, expires)
        
        return url
    except S3Error as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise
```

**File Upload with Metadata:**
```python
async def upload_with_metadata(
    self, 
    file_obj: BinaryIO, 
    object_name: str,
    metadata: Dict[str, str]
) -> str:
    """Upload file with comprehensive metadata tracking"""
    
    # Enhanced metadata
    enhanced_metadata = {
        **metadata,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "content_hash": await self._calculate_content_hash(file_obj),
        "govstack_version": "1.0.0"
    }
    
    # Upload with metadata
    self.client.put_object(
        bucket_name=self.bucket_name,
        object_name=object_name,
        data=file_obj,
        length=file_obj.seek(0, 2),
        content_type=metadata.get("content_type", "application/octet-stream"),
        metadata=enhanced_metadata
    )
    
    return object_name
```

Recommended image: MinIO architecture diagram with bucket policies and security layers

---

Slide 5 — ChromaDB Vector Database: Production Implementation

**ChromaDB Authentication & Security:**
```yaml
# Production ChromaDB with authentication
chroma:
  image: chromadb/chroma:latest
  environment:
    CHROMA_SERVER_AUTHN_CREDENTIALS_FILE: /chroma/server.htpasswd
    CHROMA_SERVER_AUTHN_PROVIDER: chromadb.auth.basic_authn.BasicAuthenticationServerProvider
    CHROMA_TELEMETRY_ANONYMOUS: false
  volumes:
    - ./data/chroma:/data:rw
    - ./server.htpasswd:/chroma/server.htpasswd:ro
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Vector Store Setup & Management:**
```python
async def setup_vector_store(collection_name: str):
    """Production-ready vector store setup with monitoring"""
    
    try:
        # Connect with authentication
        remote_db = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", "8050")),
            settings=ChromaSettings(
                chroma_client_auth_provider="chromadb.auth.basic_authn.BasicAuthClientProvider",
                chroma_client_auth_credentials=f"{os.getenv('CHROMA_USERNAME')}:{os.getenv('CHROMA_PASSWORD')}"
            )
        )
        
        # Get or create collection with metadata
        chroma_collection = remote_db.get_or_create_collection(
            name=collection_name,
            metadata={
                "created_at": datetime.utcnow().isoformat(),
                "description": collection_dict.get(collection_name, {}).get("collection_description", ""),
                "embedding_model": "text-embedding-3-small",
                "chunk_size": 1024,
                "chunk_overlap": 50
            }
        )
        
        # Set up vector store with optimized settings
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Create ingestion pipeline with performance optimizations
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=1024,
                    chunk_overlap=50,
                    separator=" "
                ),
                OpenAIEmbedding(
                    model="text-embedding-3-small",
                    embed_batch_size=100,  # Batch processing for efficiency
                    chunk_size=64
                ),
            ],
            vector_store=vector_store
        )
        
        return vector_store, pipeline
        
    except Exception as e:
        logger.error(f"Error setting up vector store: {e}")
        raise
```

**Collection Statistics & Monitoring:**
```python
async def get_collection_health_metrics(collection_id: str) -> Dict[str, Any]:
    """Comprehensive collection health monitoring"""
    
    try:
        # Get collection statistics
        collection = remote_db.get_collection(collection_id)
        
        # Vector count and distribution
        vector_count = collection.count()
        
        # Sample embeddings for health check
        sample_results = collection.peek(limit=10)
        
        # Calculate embedding quality metrics
        embedding_dimensions = len(sample_results['embeddings'][0]) if sample_results['embeddings'] else 0
        
        # Query performance test
        start_time = time.time()
        test_query = collection.query(
            query_texts=["test query"],
            n_results=5
        )
        query_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return {
            "collection_id": collection_id,
            "vector_count": vector_count,
            "embedding_dimensions": embedding_dimensions,
            "query_latency_ms": query_latency,
            "health_status": "healthy" if query_latency < 1000 else "degraded",
            "last_updated": datetime.utcnow().isoformat(),
            "memory_usage": collection.count() * embedding_dimensions * 4,  # Approximate bytes
        }
        
    except Exception as e:
        logger.error(f"Error getting collection health metrics: {e}")
        return {"collection_id": collection_id, "health_status": "error", "error": str(e)}
```

**Backup & Recovery for Vector Data:**
```python
async def backup_collection(collection_id: str, backup_path: str):
    """Backup vector collection with metadata"""
    
    collection = remote_db.get_collection(collection_id)
    
    # Export all vectors and metadata
    all_data = collection.get(include=['embeddings', 'metadatas', 'documents'])
    
    backup_data = {
        "collection_id": collection_id,
        "backup_timestamp": datetime.utcnow().isoformat(),
        "vector_count": len(all_data['ids']),
        "data": all_data,
        "metadata": collection.metadata
    }
    
    # Save to compressed JSON
    with gzip.open(f"{backup_path}/{collection_id}_backup.json.gz", "wt") as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"Collection {collection_id} backed up successfully")
```

Recommended image: ChromaDB monitoring dashboard with collection metrics

---

Slide 6 — Advanced Embeddings Pipeline & Indexing

**Production Indexing Pipeline:**
```python
async def index_uploaded_documents_by_collection(collection_id: str) -> Dict[str, Any]:
    """Advanced document indexing with monitoring and error handling"""
    
    async with async_session_maker() as db:
        try:
            # Get unindexed documents with metadata
            documents = await get_unindexed_documents(db, collection_id)
            
            if not documents:
                return {
                    "status": "completed",
                    "message": "No unindexed documents found",
                    "collection_id": collection_id,
                    "stats": await get_collection_stats(db, collection_id)
                }
            
            logger.info(f"Found {len(documents)} documents to index for collection '{collection_id}'")
            
            # Set up vector store with monitoring
            vector_store, pipeline = await setup_vector_store(collection_id)
            
            # Process documents in optimized batches
            batch_size = 10  # Smaller batches for memory efficiency
            total_indexed = 0
            failed_documents = []
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_num = i//batch_size + 1
                total_batches = (len(documents)-1)//batch_size + 1
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_docs)} documents)")
                
                # Create temporary directory for this batch
                with tempfile.TemporaryDirectory() as temp_dir:
                    try:
                        # Download and process documents
                        processed_docs = await download_and_process_documents(batch_docs, temp_dir)
                        
                        if not processed_docs:
                            logger.warning(f"No documents processed in batch {batch_num}")
                            continue
                        
                        # Run the ingestion pipeline
                        await pipeline.arun(documents=processed_docs)
                        
                        # Mark documents as indexed
                        document_ids = [doc["id"] for doc in batch_docs]
                        await mark_documents_as_indexed(db, document_ids)
                        
                        total_indexed += len(batch_docs)
                        logger.info(f"Successfully indexed batch {batch_num} ({len(batch_docs)} documents)")
                        
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_num}: {e}")
                        failed_documents.extend([doc["id"] for doc in batch_docs])
                        continue
                
                # Add delay between batches to prevent overwhelming the system
                await asyncio.sleep(1)
            
            # Final statistics
            stats = await get_collection_stats(db, collection_id)
            
            return {
                "status": "completed" if not failed_documents else "partial",
                "collection_id": collection_id,
                "total_processed": total_indexed,
                "failed_documents": failed_documents,
                "processing_time_seconds": time.time() - start_time,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Critical error in indexing pipeline: {e}")
            return {
                "status": "error",
                "collection_id": collection_id,
                "error": str(e),
                "stats": await get_collection_stats(db, collection_id)
            }
```

**Chunking Strategy Optimization:**
```python
class AdaptiveChunker:
    """Advanced chunking strategy based on document type and content"""
    
    def __init__(self):
        self.chunk_strategies = {
            "pdf": {"chunk_size": 1024, "chunk_overlap": 100},
            "docx": {"chunk_size": 800, "chunk_overlap": 80},
            "txt": {"chunk_size": 1200, "chunk_overlap": 120},
            "html": {"chunk_size": 900, "chunk_overlap": 90}
        }
    
    def get_chunking_params(self, document: Document) -> Dict[str, int]:
        """Determine optimal chunking parameters based on document characteristics"""
        
        content_type = document.metadata.get("content_type", "txt")
        file_extension = content_type.split('/')[-1] if '/' in content_type else "txt"
        
        # Default chunking parameters
        params = self.chunk_strategies.get(file_extension, self.chunk_strategies["txt"])
        
        # Adjust based on document length
        doc_length = len(document.text)
        if doc_length < 1000:
            params["chunk_size"] = min(params["chunk_size"], doc_length // 2)
            params["chunk_overlap"] = params["chunk_size"] // 10
        
        return params
    
    def create_semantic_chunks(self, document: Document) -> List[Document]:
        """Create semantically meaningful chunks"""
        
        params = self.get_chunking_params(document)
        
        # Use sentence splitter with adaptive parameters
        splitter = SentenceSplitter(
            chunk_size=params["chunk_size"],
            chunk_overlap=params["chunk_overlap"],
            separator=" "
        )
        
        chunks = splitter.split_text(document.text)
        
        # Create document objects with enhanced metadata
        chunk_documents = []
        for i, chunk in enumerate(chunks):
            chunk_doc = Document(
                text=chunk,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk),
                    "chunking_strategy": f"adaptive_{params['chunk_size']}"
                }
            )
            chunk_documents.append(chunk_doc)
        
        return chunk_documents
```

**Embedding Quality Monitoring:**
```python
async def monitor_embedding_quality(collection_id: str) -> Dict[str, Any]:
    """Monitor embedding quality and detect degradation"""
    
    try:
        collection = remote_db.get_collection(collection_id)
        
        # Sample embeddings for analysis
        sample_data = collection.get(limit=100, include=['embeddings', 'metadatas'])
        
        if not sample_data['embeddings']:
            return {"status": "no_data", "collection_id": collection_id}
        
        embeddings = np.array(sample_data['embeddings'])
        
        # Calculate quality metrics
        metrics = {
            "embedding_dimension": embeddings.shape[1],
            "sample_size": embeddings.shape[0],
            "mean_magnitude": np.mean(np.linalg.norm(embeddings, axis=1)),
            "std_magnitude": np.std(np.linalg.norm(embeddings, axis=1)),
            "cosine_similarity_mean": np.mean(cosine_similarity(embeddings)),
            "embedding_density": np.count_nonzero(embeddings) / embeddings.size,
            "collection_id": collection_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Quality assessment
        quality_score = calculate_embedding_quality_score(metrics)
        metrics["quality_score"] = quality_score
        metrics["status"] = "healthy" if quality_score > 0.7 else "degraded"
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error monitoring embedding quality: {e}")
        return {"status": "error", "collection_id": collection_id, "error": str(e)}
```

Recommended image: Embeddings pipeline flow diagram with quality monitoring

---

Slide 7 — Automated Backup & Disaster Recovery

**Production Backup Service:**
```dockerfile
# docker/backup.Dockerfile
FROM postgres:17.5

RUN apt-get update && apt-get install -y \
    cron \
    gzip \
    aws-cli \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/backup_service.sh /usr/local/bin/
COPY scripts/backup_cron.sh /usr/local/bin/
COPY scripts/restore_service.sh /usr/local/bin/

RUN chmod +x /usr/local/bin/*.sh

CMD ["cron", "-f"]
```

**Comprehensive Backup Script:**
```bash
#!/bin/bash
# scripts/backup_service.sh - Production backup implementation

set -euo pipefail

BACKUP_TYPE=${1:-full}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${BACKUP_DIR}/backup.log"
}

backup_postgres() {
    local backup_file="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"
    
    log_message "Starting PostgreSQL backup..."
    
    # Create compressed backup with consistent snapshot
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --verbose \
        --no-password \
        --clean \
        --if-exists \
        --create \
        --encoding=UTF8 | gzip > "$backup_file"
    
    # Verify backup integrity
    if gzip -t "$backup_file"; then
        log_message "PostgreSQL backup completed: $backup_file"
        echo "$backup_file" >> "${BACKUP_DIR}/backup_manifest.txt"
    else
        log_message "ERROR: PostgreSQL backup verification failed"
        rm -f "$backup_file"
        exit 1
    fi
}

backup_minio() {
    local backup_dir="${BACKUP_DIR}/minio_${TIMESTAMP}"
    
    log_message "Starting MinIO backup..."
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Sync MinIO data (requires MinIO client)
    mc mirror --overwrite minio/govstack-docs "$backup_dir/"
    
    # Create compressed archive
    tar -czf "${backup_dir}.tar.gz" -C "$backup_dir" .
    rm -rf "$backup_dir"
    
    log_message "MinIO backup completed: ${backup_dir}.tar.gz"
    echo "${backup_dir}.tar.gz" >> "${BACKUP_DIR}/backup_manifest.txt"
}

backup_chroma() {
    local backup_file="${BACKUP_DIR}/chroma_${TIMESTAMP}.json.gz"
    
    log_message "Starting ChromaDB backup..."
    
    # Export all collections using Python script
    python3 /usr/local/bin/backup_chroma.py --output "$backup_file"
    
    if [ -f "$backup_file" ]; then
        log_message "ChromaDB backup completed: $backup_file"
        echo "$backup_file" >> "${BACKUP_DIR}/backup_manifest.txt"
    else
        log_message "ERROR: ChromaDB backup failed"
        exit 1
    fi
}

cleanup_old_backups() {
    log_message "Cleaning up backups older than $RETENTION_DAYS days..."
    
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.json.gz" -mtime +$RETENTION_DAYS -delete
    
    log_message "Cleanup completed"
}

# Main backup execution
case "$BACKUP_TYPE" in
    postgres)
        backup_postgres
        ;;
    minio)
        backup_minio
        ;;
    chroma)
        backup_chroma
        ;;
    full)
        backup_postgres
        backup_minio
        backup_chroma
        cleanup_old_backups
        ;;
    *)
        echo "Usage: $0 {postgres|minio|chroma|full}"
        exit 1
        ;;
esac

log_message "Backup operation completed successfully"
```

**Disaster Recovery Procedures:**
```python
class DisasterRecoveryManager:
    def __init__(self):
        self.backup_dir = "/backups"
        self.recovery_log = "/var/log/recovery.log"
    
    async def restore_from_backup(self, backup_date: str, components: List[str] = None):
        """Comprehensive disaster recovery procedure"""
        
        if components is None:
            components = ["postgres", "minio", "chroma"]
        
        recovery_plan = {
            "postgres": self.restore_postgres,
            "minio": self.restore_minio,
            "chroma": self.restore_chroma
        }
        
        self.log_recovery(f"Starting disaster recovery for {backup_date}")
        
        for component in components:
            try:
                await recovery_plan[component](backup_date)
                self.log_recovery(f"Successfully restored {component}")
            except Exception as e:
                self.log_recovery(f"Failed to restore {component}: {e}")
                raise
        
        # Verify system integrity after restore
        await self.verify_system_integrity()
        self.log_recovery("Disaster recovery completed successfully")
    
    async def restore_postgres(self, backup_date: str):
        """Restore PostgreSQL from backup"""
        backup_file = f"{self.backup_dir}/postgres_{backup_date}.sql.gz"
        
        if not os.path.exists(backup_file):
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        # Stop application services
        await self.stop_application_services()
        
        # Restore database
        restore_cmd = f"""
        zcat {backup_file} | PGPASSWORD={os.getenv('POSTGRES_PASSWORD')} psql \
            -h {os.getenv('POSTGRES_HOST')} \
            -p {os.getenv('POSTGRES_PORT')} \
            -U {os.getenv('POSTGRES_USER')} \
            -d postgres
        """
        
        result = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"PostgreSQL restore failed: {result.stderr}")
    
    async def verify_system_integrity(self):
        """Verify system integrity after restore"""
        
        # Database connectivity test
        try:
            async with async_session_maker() as db:
                result = await db.execute(text("SELECT COUNT(*) FROM documents"))
                doc_count = result.scalar()
                self.log_recovery(f"Database verification: {doc_count} documents found")
        except Exception as e:
            raise RuntimeError(f"Database verification failed: {e}")
        
        # MinIO connectivity test
        try:
            storage_client = MinioClient()
            files = storage_client.list_files()
            self.log_recovery(f"MinIO verification: {len(files)} files found")
        except Exception as e:
            raise RuntimeError(f"MinIO verification failed: {e}")
        
        # ChromaDB connectivity test
        try:
            remote_db = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST"),
                port=int(os.getenv("CHROMA_PORT"))
            )
            collections = remote_db.list_collections()
            self.log_recovery(f"ChromaDB verification: {len(collections)} collections found")
        except Exception as e:
            raise RuntimeError(f"ChromaDB verification failed: {e}")
```

**Backup Monitoring Dashboard:**
```python
async def get_backup_status() -> Dict[str, Any]:
    """Get comprehensive backup status and health metrics"""
    
    backup_dir = "/backups"
    
    # Get latest backups
    postgres_backups = sorted(glob.glob(f"{backup_dir}/postgres_*.sql.gz"))
    minio_backups = sorted(glob.glob(f"{backup_dir}/minio_*.tar.gz"))
    chroma_backups = sorted(glob.glob(f"{backup_dir}/chroma_*.json.gz"))
    
    # Calculate backup freshness
    now = datetime.utcnow()
    
    def get_backup_age(backup_files):
        if not backup_files:
            return None
        latest = backup_files[-1]
        timestamp = os.path.getmtime(latest)
        age_hours = (now.timestamp() - timestamp) / 3600
        return age_hours
    
    return {
        "backup_status": {
            "postgres": {
                "latest_backup": postgres_backups[-1] if postgres_backups else None,
                "age_hours": get_backup_age(postgres_backups),
                "backup_count": len(postgres_backups),
                "status": "healthy" if get_backup_age(postgres_backups) and get_backup_age(postgres_backups) < 25 else "stale"
            },
            "minio": {
                "latest_backup": minio_backups[-1] if minio_backups else None,
                "age_hours": get_backup_age(minio_backups),
                "backup_count": len(minio_backups),
                "status": "healthy" if get_backup_age(minio_backups) and get_backup_age(minio_backups) < 25 else "stale"
            },
            "chroma": {
                "latest_backup": chroma_backups[-1] if chroma_backups else None,
                "age_hours": get_backup_age(chroma_backups),
                "backup_count": len(chroma_backups),
                "status": "healthy" if get_backup_age(chroma_backups) and get_backup_age(chroma_backups) < 25 else "stale"
            }
        },
        "disk_usage": {
            "total_backup_size_gb": sum(os.path.getsize(f) for f in postgres_backups + minio_backups + chroma_backups) / (1024**3),
            "available_space_gb": shutil.disk_usage(backup_dir).free / (1024**3)
        },
        "recovery_metrics": {
            "rpo_hours": 24,  # Recovery Point Objective
            "rto_hours": 4,   # Recovery Time Objective
            "last_recovery_test": "2025-08-15T10:00:00Z"
        }
    }
```

Recommended image: Backup monitoring dashboard showing status and metrics

---

Slide 8 — Production Monitoring & Observability

**Comprehensive Monitoring Stack:**
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/datasources:/etc/grafana/provisioning/datasources

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
```

**Application Metrics Implementation:**
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics definitions
REQUEST_COUNT = Counter('govstack_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('govstack_request_duration_seconds', 'Request duration', ['endpoint'])
ACTIVE_CONNECTIONS = Gauge('govstack_active_connections', 'Active database connections')
VECTOR_SEARCH_LATENCY = Histogram('govstack_vector_search_duration_seconds', 'Vector search latency')
DOCUMENT_PROCESSING_TIME = Histogram('govstack_document_processing_seconds', 'Document processing time')

class MetricsMiddleware:
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            method = scope["method"]
            path = scope["path"]
            
            # Custom send wrapper to capture response status
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    duration = time.time() - start_time
                    
                    # Record metrics
                    REQUEST_COUNT.labels(method=method, endpoint=path, status=status_code).inc()
                    REQUEST_DURATION.labels(endpoint=path).observe(duration)
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

# Add middleware to FastAPI app
app.add_middleware(MetricsMiddleware)

# Database connection monitoring
async def update_connection_metrics():
    """Update database connection metrics"""
    try:
        async with async_session_maker() as db:
            result = await db.execute(text("""
                SELECT count(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active'
            """))
            active_count = result.scalar()
            ACTIVE_CONNECTIONS.set(active_count)
    except Exception as e:
        logger.error(f"Error updating connection metrics: {e}")
```

**Custom Dashboard Configuration:**
```json
{
  "dashboard": {
    "title": "GovStack Production Monitoring",
    "panels": [
      {
        "title": "API Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(govstack_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(govstack_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "govstack_active_connections",
            "legendFormat": "Active Connections"
          },
          {
            "expr": "rate(postgres_queries_total[5m])",
            "legendFormat": "Queries/sec"
          }
        ]
      },
      {
        "title": "Vector Search Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(govstack_vector_search_duration_seconds_bucket[5m]))",
            "legendFormat": "Vector Search Latency p95"
          }
        ]
      }
    ]
  }
}
```

**Alerting Rules:**
```yaml
# prometheus/alerts.yml
groups:
  - name: govstack_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(govstack_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/second"

      - alert: DatabaseConnectionsHigh
        expr: govstack_active_connections > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High database connection count"
          description: "Database has {{ $value }} active connections"

      - alert: VectorSearchLatencyHigh
        expr: histogram_quantile(0.95, rate(govstack_vector_search_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Vector search latency is high"
          description: "95th percentile latency is {{ $value }} seconds"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critically low"
          description: "Only {{ $value | humanizePercentage }} disk space remaining"
```

**Log Aggregation with ELK Stack:**
```python
import structlog

# Structured logging configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def log_api_request(self, request_id: str, method: str, path: str, 
                       user_id: str, response_time: float, status_code: int):
        self.logger.info(
            "api_request",
            request_id=request_id,
            method=method,
            path=path,
            user_id=user_id,
            response_time_ms=response_time * 1000,
            status_code=status_code,
            event_type="api_access"
        )
    
    def log_document_processing(self, document_id: str, collection_id: str,
                              processing_time: float, success: bool):
        self.logger.info(
            "document_processing",
            document_id=document_id,
            collection_id=collection_id,
            processing_time_seconds=processing_time,
            success=success,
            event_type="document_indexing"
        )
```

Recommended image: Comprehensive monitoring dashboard with all system metrics

---

Slide 9 — Container Orchestration & Production Deployment

**Production Docker Compose Configuration:**
```yaml
# docker-compose.prod.yml
name: govstack-production

services:
  govstack-server:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    ports:
      - "5000:5000"
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=INFO
      - RATE_LIMITING_ENABLED=true
      - SECURITY_HEADERS_ENABLED=true
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./data:/app/data:rw
      - ./logs:/app/logs:rw
    networks:
      - govstack-production
    depends_on:
      postgres:
        condition: service_healthy
      chroma:
        condition: service_healthy
      minio:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/logs:/var/log/nginx:rw
    depends_on:
      - govstack-server
    networks:
      - govstack-production
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

**Nginx Configuration for Production:**
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream govstack_backend {
        server govstack-server:5000;
        # Add more servers for load balancing
        # server govstack-server-2:5000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=1r/s;

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://govstack_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # File upload with stricter rate limiting
        location /documents/ {
            limit_req zone=upload burst=5;
            client_max_body_size 100M;
            proxy_pass http://govstack_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Health check endpoint (no rate limiting)
        location /health {
            proxy_pass http://govstack_backend;
            access_log off;
        }
    }
}
```

**Kubernetes Deployment Manifests:**
```yaml
# k8s/govstack-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: govstack-api
  labels:
    app: govstack-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: govstack-api
  template:
    metadata:
      labels:
        app: govstack-api
    spec:
      containers:
      - name: govstack-api
        image: govstack/api:1.0.0
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: govstack-secrets
              key: database-url
        - name: GOVSTACK_API_KEY
          valueFrom:
            secretKeyRef:
              name: govstack-secrets
              key: api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: govstack-api-service
spec:
  selector:
    app: govstack-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: govstack-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: govstack-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Helm Chart Configuration:**
```yaml
# helm/govstack/values.yaml
replicaCount: 3

image:
  repository: govstack/api
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 5000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.govstack.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: govstack-api-tls
      hosts:
        - api.govstack.com

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    postgresPassword: "secure-password"
    database: "govstackdb"
  primary:
    persistence:
      enabled: true
      size: 100Gi
```

Recommended image: Kubernetes deployment architecture with scaling and load balancing

---

Slide 10 — Analytics Microservice Architecture

**Microservice Implementation:**
```python
# analytics/main.py - Production analytics service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI(
    title="GovStack Analytics API",
    description="Privacy-preserving analytics microservice",
    version="1.0.0",
    docs_url="/analytics/docs",
    redoc_url="/analytics/redoc"
)

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.govstack.com"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include specialized routers
app.include_router(user_analytics.router, prefix="/analytics/user", tags=["User Analytics"])
app.include_router(usage_analytics.router, prefix="/analytics/usage", tags=["Usage Analytics"])
app.include_router(conversation_analytics.router, prefix="/analytics/conversation", tags=["Conversation Analytics"])
app.include_router(business_analytics.router, prefix="/analytics/business", tags=["Business Analytics"])
```

**Real-Time Analytics Pipeline:**
```python
class AnalyticsProcessor:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.batch_size = 100
        self.processing_interval = 60  # seconds
    
    async def process_real_time_events(self):
        """Process analytics events in real-time"""
        while True:
            try:
                # Get events from queue
                events = await self.get_pending_events()
                
                if events:
                    # Process in batches for efficiency
                    for i in range(0, len(events), self.batch_size):
                        batch = events[i:i+self.batch_size]
                        await self.process_event_batch(batch)
                
                # Wait before next processing cycle
                await asyncio.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in analytics processing: {e}")
                await asyncio.sleep(self.processing_interval)
    
    async def process_event_batch(self, events: List[Dict]):
        """Process a batch of analytics events"""
        
        # Group events by type for efficient processing
        event_groups = defaultdict(list)
        for event in events:
            event_groups[event['event_type']].append(event)
        
        # Process each event type
        for event_type, group_events in event_groups.items():
            if event_type == 'chat_message':
                await self.process_chat_events(group_events)
            elif event_type == 'document_access':
                await self.process_document_events(group_events)
            elif event_type == 'api_request':
                await self.process_api_events(group_events)
```

**Analytics Data Models:**
```python
# Comprehensive analytics schemas
class ConversationAnalytics(BaseModel):
    """Detailed conversation analytics"""
    
    total_conversations: int
    average_conversation_length: float
    completion_rate: float
    abandonment_rate: float
    user_satisfaction_score: float
    
    # Topic analysis
    most_common_topics: List[TopicFrequency]
    topic_success_rates: Dict[str, float]
    
    # Performance metrics
    average_response_time: float
    p95_response_time: float
    error_rate: float
    
    # Temporal patterns
    hourly_distribution: List[HourlyStats]
    daily_trends: List[DailyTrend]
    
    # Intent analysis
    intent_distribution: List[IntentAnalysis]
    intent_resolution_rates: Dict[str, float]

class DocumentRetrieval(BaseModel):
    """Document access and retrieval analytics"""
    
    total_retrievals: int
    unique_documents_accessed: int
    average_relevance_score: float
    
    # Document popularity
    most_accessed_documents: List[DocumentStats]
    collection_usage: Dict[str, CollectionStats]
    
    # Retrieval performance
    average_retrieval_time: float
    cache_hit_rate: float
    failed_retrievals: int
    
    # Content gaps analysis
    unanswered_queries: List[str]
    low_confidence_responses: int
    missing_document_indicators: List[str]

class SystemHealth(BaseModel):
    """Comprehensive system health metrics"""
    
    api_response_times: ResponseTimeMetrics
    database_performance: DatabaseMetrics
    vector_db_performance: VectorDBMetrics
    storage_metrics: StorageMetrics
    
    # Resource utilization
    cpu_utilization: ResourceMetrics
    memory_utilization: ResourceMetrics
    disk_utilization: ResourceMetrics
    network_utilization: ResourceMetrics
    
    # Error tracking
    error_rates: ErrorMetrics
    alert_summary: AlertSummary
    
    # Capacity planning
    growth_projections: GrowthProjections
    scalability_recommendations: List[str]
```

**Privacy-Preserving Analytics:**
```python
class PrivacyPreservingAnalytics:
    """Implement differential privacy for sensitive analytics"""
    
    def __init__(self, epsilon: float = 1.0):
        self.epsilon = epsilon  # Privacy parameter
        self.sensitivity = 1.0  # Query sensitivity
    
    def add_noise(self, true_value: float) -> float:
        """Add Laplace noise for differential privacy"""
        scale = self.sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        return max(0, true_value + noise)  # Ensure non-negative results
    
    async def get_user_demographics_private(self, time_period: int = 30) -> UserDemographics:
        """Get user demographics with privacy protection"""
        
        # Get raw metrics
        raw_metrics = await self.get_raw_user_metrics(time_period)
        
        # Apply differential privacy
        return UserDemographics(
            total_users=int(self.add_noise(raw_metrics.total_users)),
            new_users=int(self.add_noise(raw_metrics.new_users)),
            returning_users=int(self.add_noise(raw_metrics.returning_users)),
            active_users=int(self.add_noise(raw_metrics.active_users)),
            user_growth_rate=self.add_noise(raw_metrics.user_growth_rate)
        )
    
    async def get_aggregated_metrics_only(self, min_threshold: int = 10) -> Dict[str, Any]:
        """Return only aggregated metrics with minimum thresholds"""
        
        # Ensure all reported metrics meet minimum threshold for privacy
        raw_data = await self.get_raw_analytics_data()
        
        filtered_metrics = {}
        for metric_name, value in raw_data.items():
            if isinstance(value, (int, float)) and value >= min_threshold:
                filtered_metrics[metric_name] = value
            elif isinstance(value, dict):
                # Filter nested metrics
                filtered_nested = {k: v for k, v in value.items() 
                                 if isinstance(v, (int, float)) and v >= min_threshold}
                if filtered_nested:
                    filtered_metrics[metric_name] = filtered_nested
        
        return filtered_metrics
```

Recommended image: Analytics microservice architecture with privacy controls

---

Slide 11 — Advanced Deployment Strategies

**Blue-Green Deployment Implementation:**
```bash
#!/bin/bash
# scripts/blue_green_deploy.sh

set -euo pipefail

ENVIRONMENT=${1:-staging}
NEW_VERSION=${2:-latest}
HEALTH_CHECK_URL="http://localhost:5000/health"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

deploy_blue_green() {
    local current_env=$1
    local new_version=$2
    
    log "Starting blue-green deployment for version $new_version"
    
    # Determine current and target environments
    if docker-compose -p govstack-blue ps | grep -q "Up"; then
        CURRENT="blue"
        TARGET="green"
    else
        CURRENT="green"
        TARGET="blue"
    fi
    
    log "Current environment: $CURRENT, Target environment: $TARGET"
    
    # Deploy to target environment
    log "Deploying to $TARGET environment..."
    docker-compose -p govstack-$TARGET -f docker-compose.$TARGET.yml down
    docker-compose -p govstack-$TARGET -f docker-compose.$TARGET.yml build --no-cache
    docker-compose -p govstack-$TARGET -f docker-compose.$TARGET.yml up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    TARGET_URL="http://localhost:$(get_port $TARGET)/health"
    if ! health_check "$TARGET_URL"; then
        log "Health check failed, rolling back..."
        docker-compose -p govstack-$TARGET -f docker-compose.$TARGET.yml down
        exit 1
    fi
    
    # Switch traffic (update load balancer)
    log "Switching traffic to $TARGET environment..."
    update_load_balancer_target "$TARGET"
    
    # Final verification
    sleep 10
    if health_check "$HEALTH_CHECK_URL"; then
        log "Deployment successful, shutting down $CURRENT environment..."
        docker-compose -p govstack-$CURRENT -f docker-compose.$CURRENT.yml down
        log "Blue-green deployment completed successfully"
    else
        log "Final health check failed, rolling back..."
        update_load_balancer_target "$CURRENT"
        docker-compose -p govstack-$TARGET -f docker-compose.$TARGET.yml down
        exit 1
    fi
}

health_check() {
    local url=$1
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null; then
            log "Health check passed on attempt $attempt"
            return 0
        fi
        log "Health check failed, attempt $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done
    
    return 1
}

# Execute deployment
deploy_blue_green "$ENVIRONMENT" "$NEW_VERSION"
```

**Canary Deployment with Kubernetes:**
```yaml
# k8s/canary-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: govstack-api-rollout
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10   # 10% traffic to canary
      - pause:
          duration: 300s  # 5 minutes
      - setWeight: 25   # 25% traffic to canary
      - pause:
          duration: 300s
      - setWeight: 50   # 50% traffic to canary
      - pause:
          duration: 600s  # 10 minutes
      - setWeight: 75   # 75% traffic to canary
      - pause:
          duration: 300s
      # If all checks pass, complete rollout
      canaryService: govstack-api-canary
      stableService: govstack-api-stable
      trafficRouting:
        nginx:
          stableIngress: govstack-api-stable
          annotationPrefix: nginx.ingress.kubernetes.io
          additionalIngressAnnotations:
            canary-by-header: "X-Canary"
      analysis:
        templates:
        - templateName: success-rate
        - templateName: response-time
        args:
        - name: service-name
          value: govstack-api-canary
  selector:
    matchLabels:
      app: govstack-api
  template:
    metadata:
      labels:
        app: govstack-api
    spec:
      containers:
      - name: govstack-api
        image: govstack/api:{{.Values.image.tag}}
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 30s
    successCondition: result[0] >= 0.95
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(govstack_requests_total{service="{{args.service-name}}",status!~"5.."}[5m])) /
          sum(rate(govstack_requests_total{service="{{args.service-name}}"}[5m]))
```

**Infrastructure as Code with Terraform:**
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "govstack-production"
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  # Node groups
  eks_managed_node_groups = {
    govstack_nodes = {
      min_size     = 3
      max_size     = 10
      desired_size = 5
      
      instance_types = ["m5.large", "m5.xlarge"]
      
      k8s_labels = {
        Environment = "production"
        Application = "govstack"
      }
    }
  }
  
  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
}

# RDS for PostgreSQL
resource "aws_db_instance" "govstack_postgres" {
  identifier = "govstack-production"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.r5.large"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "govstackdb"
  username = "postgres"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.govstack.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  deletion_protection = true
  skip_final_snapshot = false
  
  tags = {
    Name        = "GovStack Production Database"
    Environment = "production"
  }
}

# S3 for MinIO-compatible storage
resource "aws_s3_bucket" "govstack_storage" {
  bucket = "govstack-production-storage"
  
  tags = {
    Name        = "GovStack Production Storage"
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "govstack_versioning" {
  bucket = aws_s3_bucket.govstack_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "govstack_encryption" {
  bucket = aws_s3_bucket.govstack_storage.id
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
```

Recommended image: Deployment pipeline diagram with blue-green and canary strategies

---

Slide 12 — CI/CD Pipeline & GitOps Implementation

**Advanced CI/CD Pipeline:**
```yaml
# .github/workflows/production-deploy.yml
name: Production Deployment Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  test-suite:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17.5
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run unit tests
        run: |
          pytest tests/unit_tests/ -v --cov=app --cov-report=xml
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/testdb
        run: |
          pytest tests/integration_tests/ -v
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3

  build-and-push:
    needs: [security-scan, test-suite]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: docker/api.Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      
      - name: Deploy to staging
        env:
          KUBE_CONFIG: ${{ secrets.STAGING_KUBE_CONFIG }}
        run: |
          echo "$KUBE_CONFIG" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          
          # Update image tag in deployment
          kubectl set image deployment/govstack-api \
            govstack-api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main \
            -n staging
          
          # Wait for rollout
          kubectl rollout status deployment/govstack-api -n staging --timeout=600s
      
      - name: Run smoke tests
        run: |
          curl -f https://staging-api.govstack.com/health
          python tests/smoke_tests/test_staging.py

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production with Argo CD
        env:
          ARGOCD_SERVER: ${{ secrets.ARGOCD_SERVER }}
          ARGOCD_AUTH_TOKEN: ${{ secrets.ARGOCD_AUTH_TOKEN }}
        run: |
          # Install Argo CD CLI
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          
          # Update application image
          ./argocd app set govstack-production \
            --parameter image.tag=${GITHUB_REF#refs/tags/} \
            --server $ARGOCD_SERVER \
            --auth-token $ARGOCD_AUTH_TOKEN
          
          # Sync application
          ./argocd app sync govstack-production \
            --server $ARGOCD_SERVER \
            --auth-token $ARGOCD_AUTH_TOKEN
          
          # Wait for sync
          ./argocd app wait govstack-production \
            --timeout 600 \
            --server $ARGOCD_SERVER \
            --auth-token $ARGOCD_AUTH_TOKEN
```

**GitOps with ArgoCD:**
```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: govstack-production
  namespace: argocd
spec:
  project: default
  
  source:
    repoURL: https://github.com/think-ke/govstack
    targetRevision: HEAD
    path: k8s/production
    helm:
      valueFiles:
        - values.yaml
        - values-production.yaml
  
  destination:
    server: https://kubernetes.default.svc
    namespace: govstack-production
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  
  revisionHistoryLimit: 10
  
  # Health checks
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

**Database Migration Pipeline:**
```python
# scripts/migration_pipeline.py
import asyncio
import logging
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

class MigrationPipeline:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(database_url)
        self.alembic_cfg = Config("alembic.ini")
        
    async def run_migrations(self, target_revision: str = "head"):
        """Run database migrations safely"""
        
        try:
            # Backup database before migration
            await self.backup_database()
            
            # Run pre-migration checks
            await self.pre_migration_checks()
            
            # Execute migrations
            logging.info(f"Running migrations to {target_revision}")
            command.upgrade(self.alembic_cfg, target_revision)
            
            # Run post-migration validation
            await self.post_migration_validation()
            
            logging.info("Migration pipeline completed successfully")
            
        except Exception as e:
            logging.error(f"Migration failed: {e}")
            await self.rollback_migration()
            raise
    
    async def backup_database(self):
        """Create database backup before migration"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/backups/pre_migration_{timestamp}.sql.gz"
        
        backup_cmd = f"""
        PGPASSWORD={os.getenv('POSTGRES_PASSWORD')} pg_dump \
            -h {os.getenv('POSTGRES_HOST')} \
            -U {os.getenv('POSTGRES_USER')} \
            -d {os.getenv('POSTGRES_DB')} \
            --clean --if-exists | gzip > {backup_file}
        """
        
        result = subprocess.run(backup_cmd, shell=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Database backup failed: {result.stderr}")
            
        logging.info(f"Database backed up to {backup_file}")
    
    async def pre_migration_checks(self):
        """Validate system state before migration"""
        
        # Check database connectivity
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Check disk space
        backup_dir = Path("/backups")
        stat = backup_dir.stat()
        free_space = stat.st_bavail * stat.st_frsize
        if free_space < 1024**3:  # Less than 1GB
            raise RuntimeError("Insufficient disk space for migration")
        
        # Check active connections
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active' AND pid != pg_backend_pid()
            """))
            active_connections = result.scalar()
            if active_connections > 10:
                logging.warning(f"High number of active connections: {active_connections}")
    
    async def post_migration_validation(self):
        """Validate database state after migration"""
        
        # Verify table integrity
        async with self.engine.begin() as conn:
            # Check for any broken foreign keys
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE constraint_type = 'FOREIGN KEY'
            """))
            fk_count = result.scalar()
            logging.info(f"Foreign key constraints verified: {fk_count}")
            
            # Verify critical tables exist
            critical_tables = ['documents', 'chats', 'audit_logs', 'webpages']
            for table in critical_tables:
                result = await conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                logging.info(f"Table {table} verified")
```

Recommended image: Complete CI/CD pipeline diagram with all stages and gates

---

Slide 13 — Performance Optimization & Scaling Strategies

**Database Performance Optimization:**
```python
# Database query optimization patterns
class OptimizedQueries:
    
    @staticmethod
    async def get_documents_with_stats(
        db: AsyncSession, 
        collection_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """Optimized query with pagination and statistics"""
        
        # Use window functions for efficient counting
        query = text("""
            WITH document_stats AS (
                SELECT 
                    *,
                    COUNT(*) OVER() as total_count,
                    AVG(size) OVER() as avg_size,
                    SUM(size) OVER() as total_size
                FROM documents 
                WHERE collection_id = :collection_id
                ORDER BY upload_date DESC
                LIMIT :limit OFFSET :offset
            )
            SELECT * FROM document_stats
        """)
        
        result = await db.execute(query, {
            "collection_id": collection_id,
            "limit": limit,
            "offset": offset
        })
        
        rows = result.fetchall()
        if not rows:
            return [], {"total_count": 0, "avg_size": 0, "total_size": 0}
        
        # Extract statistics from first row
        stats = {
            "total_count": rows[0].total_count,
            "avg_size": float(rows[0].avg_size) if rows[0].avg_size else 0,
            "total_size": rows[0].total_size or 0
        }
        
        # Convert to Document objects
        documents = [Document(**row._asdict()) for row in rows]
        
        return documents, stats
    
    @staticmethod
    async def get_collection_analytics(
        db: AsyncSession,
        collection_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Advanced analytics query with time-based aggregation"""
        
        query = text("""
            WITH daily_stats AS (
                SELECT 
                    DATE(upload_date) as date,
                    COUNT(*) as documents_uploaded,
                    SUM(size) as total_size,
                    AVG(size) as avg_size
                FROM documents 
                WHERE collection_id = :collection_id 
                    AND upload_date >= NOW() - INTERVAL :days DAY
                GROUP BY DATE(upload_date)
                ORDER BY date DESC
            ),
            content_type_stats AS (
                SELECT 
                    content_type,
                    COUNT(*) as count,
                    SUM(size) as total_size
                FROM documents 
                WHERE collection_id = :collection_id
                GROUP BY content_type
                ORDER BY count DESC
            )
            SELECT 
                json_build_object(
                    'daily_trends', json_agg(daily_stats),
                    'content_types', (SELECT json_agg(content_type_stats) FROM content_type_stats)
                ) as analytics
            FROM daily_stats
        """)
        
        result = await db.execute(query, {
            "collection_id": collection_id,
            "days": days
        })
        
        return result.scalar() or {}
```

**Caching Strategy Implementation:**
```python
import redis.asyncio as redis
from functools import wraps
import json
import hashlib

class AdvancedCacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        self.default_ttl = 3600  # 1 hour
    
    def cache_result(self, ttl: int = None, key_prefix: str = ""):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_cache_key(func.__name__, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.redis_client.setex(
                    cache_key, 
                    ttl or self.default_ttl, 
                    json.dumps(result, default=str)
                )
                
                return result
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict, prefix: str) -> str:
        """Generate deterministic cache key"""
        key_data = f"{prefix}:{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache keys matching pattern"""
        keys = await self.redis_client.keys(pattern)
        if keys:
            await self.redis_client.delete(*keys)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        info = await self.redis_client.info()
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": info.get("keyspace_hits") / (info.get("keyspace_hits") + info.get("keyspace_misses")) if info.get("keyspace_hits") else 0
        }

# Usage example
cache_manager = AdvancedCacheManager()

@cache_manager.cache_result(ttl=1800, key_prefix="analytics")
async def get_collection_stats_cached(collection_id: str) -> Dict[str, Any]:
    """Cached collection statistics"""
    async with async_session_maker() as db:
        return await get_collection_stats(db, collection_id)
```

**Horizontal Scaling Architecture:**
```yaml
# k8s/autoscaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: govstack-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: govstack-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 4
        periodSeconds: 60
      - type: Percent
        value: 100
        periodSeconds: 15

---
apiVersion: v1
kind: Service
metadata:
  name: govstack-api-headless
spec:
  clusterIP: None
  selector:
    app: govstack-api
  ports:
  - port: 5000
    targetPort: 5000
```

**Connection Pool Optimization:**
```python
# Advanced connection pool configuration
class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            # Connection pool settings
            pool_size=20,                    # Core connections
            max_overflow=30,                 # Additional connections
            pool_timeout=30,                 # Timeout waiting for connection
            pool_recycle=3600,              # Connection lifetime (1 hour)
            pool_pre_ping=True,             # Validate connections
            # Performance optimizations
            echo=False,                     # Disable SQL logging in production
            future=True,                    # Use 2.0 style
            # Connection arguments
            connect_args={
                "command_timeout": 60,      # Query timeout
                "server_settings": {
                    "application_name": "govstack_api",
                    "jit": "off"           # Disable JIT for predictable performance
                }
            }
        )
        
        # Session factory with optimizations
        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,         # Keep objects alive after commit
            autoflush=False                 # Manual flush control
        )
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
```

Recommended image: Scaling architecture diagram with auto-scaling metrics and thresholds

---

Slide 13 — Performance Optimization & Scaling Strategies

**Database Performance Optimization:**
```python
# Database query optimization patterns
class OptimizedQueries:
    
    @staticmethod
    async def get_documents_with_stats(
        db: AsyncSession, 
        collection_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """Optimized query with pagination and statistics"""
        
        # Use window functions for efficient counting
        query = text("""
            WITH document_stats AS (
                SELECT 
                    *,
                    COUNT(*) OVER() as total_count,
                    AVG(size) OVER() as avg_size,
                    SUM(size) OVER() as total_size
                FROM documents 
                WHERE collection_id = :collection_id
                ORDER BY upload_date DESC
                LIMIT :limit OFFSET :offset
            )
            SELECT * FROM document_stats
        """)
        
        result = await db.execute(query, {
            "collection_id": collection_id,
            "limit": limit,
            "offset": offset
        })
        
        rows = result.fetchall()
        if not rows:
            return [], {"total_count": 0, "avg_size": 0, "total_size": 0}
        
        # Extract statistics from first row
        stats = {
            "total_count": rows[0].total_count,
            "avg_size": float(rows[0].avg_size) if rows[0].avg_size else 0,
            "total_size": rows[0].total_size or 0
        }
        
        # Convert to Document objects
        documents = [Document(**row._asdict()) for row in rows]
        
        return documents, stats

# Advanced connection pool configuration
class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            # Connection pool settings
            pool_size=20,                    # Core connections
            max_overflow=30,                 # Additional connections
            pool_timeout=30,                 # Timeout waiting for connection
            pool_recycle=3600,              # Connection lifetime (1 hour)
            pool_pre_ping=True,             # Validate connections
            # Performance optimizations
            echo=False,                     # Disable SQL logging in production
            future=True,                    # Use 2.0 style
            # Connection arguments
            connect_args={
                "command_timeout": 60,      # Query timeout
                "server_settings": {
                    "application_name": "govstack_api",
                    "jit": "off"           # Disable JIT for predictable performance
                }
            }
        )
```

**Caching Strategy Implementation:**
```python
import redis.asyncio as redis
from functools import wraps
import json
import hashlib

class AdvancedCacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        self.default_ttl = 3600  # 1 hour
    
    def cache_result(self, ttl: int = None, key_prefix: str = ""):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_cache_key(func.__name__, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.redis_client.setex(
                    cache_key, 
                    ttl or self.default_ttl, 
                    json.dumps(result, default=str)
                )
                
                return result
            return wrapper
        return decorator

# Usage example
cache_manager = AdvancedCacheManager()

@cache_manager.cache_result(ttl=1800, key_prefix="analytics")
async def get_collection_stats_cached(collection_id: str) -> Dict[str, Any]:
    """Cached collection statistics"""
    async with async_session_maker() as db:
        return await get_collection_stats(db, collection_id)
```

**Horizontal Scaling Architecture:**
```yaml
# k8s/autoscaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: govstack-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: govstack-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 4
        periodSeconds: 60
      - type: Percent
        value: 100
        periodSeconds: 15
```

Recommended image: Scaling architecture diagram with auto-scaling metrics and thresholds

---

Slide 14 — Cost Optimization & Resource Management

**Resource Allocation Strategies:**
```yaml
# k8s/resource-management.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: govstack-quota
  namespace: govstack-production
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 100Gi
    limits.cpu: "100"
    limits.memory: 200Gi
    persistentvolumeclaims: 10
    services.loadbalancers: 2

---
apiVersion: v1
kind: LimitRange
metadata:
  name: govstack-limits
  namespace: govstack-production
spec:
  limits:
  - default:
      cpu: "2"
      memory: "4Gi"
    defaultRequest:
      cpu: "500m"
      memory: "1Gi"
    max:
      cpu: "8"
      memory: "16Gi"
    min:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

**Cost Monitoring & Analytics:**
```python
# scripts/cost_analyzer.py
class CostAnalyzer:
    def __init__(self):
        config.load_incluster_config()
        self.k8s_client = client.CoreV1Api()
        self.prometheus = PrometheusConnect(url="http://prometheus:9090")
        
    async def analyze_resource_costs(self, namespace: str = "govstack-production") -> Dict[str, Any]:
        """Analyze resource costs and utilization"""
        
        # Get current resource allocations
        pods = self.k8s_client.list_namespaced_pod(namespace)
        
        cost_analysis = {
            "total_pods": len(pods.items),
            "resource_requests": {"cpu": 0, "memory": 0},
            "resource_limits": {"cpu": 0, "memory": 0},
            "optimization_recommendations": []
        }
        
        for pod in pods.items:
            for container in pod.spec.containers:
                if container.resources:
                    if container.resources.requests:
                        cpu_req = self._parse_cpu(container.resources.requests.get('cpu', '0'))
                        mem_req = self._parse_memory(container.resources.requests.get('memory', '0'))
                        cost_analysis["resource_requests"]["cpu"] += cpu_req
                        cost_analysis["resource_requests"]["memory"] += mem_req
        
        # Get actual utilization from Prometheus
        utilization = await self._get_utilization_metrics(namespace)
        
        # Calculate cost efficiency
        efficiency = self._calculate_efficiency(cost_analysis, utilization)
        cost_analysis["efficiency_score"] = efficiency
        
        # Generate optimization recommendations
        cost_analysis["optimization_recommendations"] = self._generate_recommendations(
            cost_analysis, utilization
        )
        
        return cost_analysis
    
    def _generate_recommendations(self, resources: Dict, utilization: Dict) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # Check for over-provisioning
        cpu_usage_ratio = utilization["cpu_utilization"] / resources["resource_requests"]["cpu"] if resources["resource_requests"]["cpu"] > 0 else 0
        mem_usage_ratio = utilization["memory_utilization"] / resources["resource_requests"]["memory"] if resources["resource_requests"]["memory"] > 0 else 0
        
        if cpu_usage_ratio < 0.3:
            recommendations.append("Consider reducing CPU requests - current utilization is below 30%")
        
        if mem_usage_ratio < 0.3:
            recommendations.append("Consider reducing memory requests - current utilization is below 30%")
        
        if cpu_usage_ratio > 0.8:
            recommendations.append("Consider increasing CPU requests - current utilization is above 80%")
        
        return recommendations
```

**Database Storage Optimization:**
```python
# Storage lifecycle management
class StorageOptimizer:
    
    async def optimize_database_storage(self, db: AsyncSession):
        """Optimize database storage and identify cleanup opportunities"""
        
        # Analyze table sizes
        table_sizes = await self._get_table_sizes(db)
        
        # Identify old audit logs for archival
        old_audit_logs = await self._identify_old_audit_logs(db)
        
        # Find unused document chunks
        unused_chunks = await self._find_unused_chunks(db)
        
        optimization_plan = {
            "table_sizes": table_sizes,
            "archival_candidates": old_audit_logs,
            "cleanup_candidates": unused_chunks,
            "recommendations": self._generate_storage_recommendations(table_sizes)
        }
        
        return optimization_plan
    
    async def _get_table_sizes(self, db: AsyncSession) -> Dict[str, Dict]:
        """Get detailed table size information"""
        
        query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        
        result = await db.execute(query)
        return {row.tablename: dict(row._mapping) for row in result}
```

Recommended image: Cost optimization dashboard showing resource utilization and efficiency metrics

---

Slide 15 — Hands-on Lab: Deployment Walkthrough

**Lab Setup Environment:**
```bash
#!/bin/bash
# setup-lab-environment.sh

set -e

echo "🚀 Setting up GovStack Lab Environment..."

# Prerequisites check
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check available disk space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ $available_space -lt 5242880 ]; then  # 5GB in KB
        echo "❌ Insufficient disk space. At least 5GB required."
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Setup lab directories
setup_directories() {
    echo "Setting up lab directories..."
    
    mkdir -p lab/{data,logs,configs,scripts}
    mkdir -p lab/data/{postgres,minio,chroma}
    
    echo "✅ Directories created"
}

# Generate lab configuration
generate_lab_config() {
    echo "Generating lab configuration..."
    
    cat > lab/configs/.env << EOF
# Lab Environment Configuration
POSTGRES_USER=labuser
POSTGRES_PASSWORD=labpass123
POSTGRES_DB=govstack_lab
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

MINIO_ROOT_USER=labadmin
MINIO_ROOT_PASSWORD=labpass123
MINIO_ENDPOINT=http://minio:9000

CHROMA_HOST=chroma
CHROMA_PORT=8000

API_KEY=lab-api-key-123
SECRET_KEY=lab-secret-key-456
LOG_LEVEL=DEBUG

# Lab-specific settings
ENABLE_DEBUG=true
ENABLE_METRICS=true
LAB_MODE=true
EOF

    echo "✅ Lab configuration generated"
}

# Main execution
main() {
    check_prerequisites
    setup_directories
    generate_lab_config
    
    echo ""
    echo "🎉 Lab environment setup completed!"
    echo ""
    echo "Next steps:"
    echo "1. cd lab"
    echo "2. docker-compose -f docker-compose.lab.yml up -d"
    echo "3. ./scripts/test-deployment.sh"
    echo ""
    echo "Access points:"
    echo "- API: http://localhost:5000"
    echo "- MinIO Console: http://localhost:9001"
    echo "- Grafana: http://localhost:3000 (admin/labpass123)"
    echo "- Prometheus: http://localhost:9090"
}

main "$@"
```

**Lab Exercise Guide:**
```markdown
# Lab Exercise 1: Basic Deployment

## Objective
Deploy the GovStack system and verify all components are running correctly.

## Steps

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/think-ke/govstack.git
cd govstack

# Run lab setup
./setup-lab-environment.sh
cd lab
```

### 2. Deploy Services
```bash
# Start all services
docker-compose -f docker-compose.lab.yml up -d

# Monitor startup logs
docker-compose -f docker-compose.lab.yml logs -f
```

### 3. Verify Deployment
```bash
# Run automated tests
./scripts/test-deployment.sh

# Manual verification
curl http://localhost:5000/health
curl http://localhost:5000/api/v1/collections
```

### 4. Explore the System
1. Access MinIO Console at http://localhost:9001
2. Log in with credentials: labadmin/labpass123
3. Create a bucket named "govstack-lab"
4. Upload a test document

### 5. Monitor Performance
1. Access Grafana at http://localhost:3000
2. Log in with credentials: admin/labpass123
3. Import the GovStack dashboard
4. Monitor system metrics during document processing

## Expected Outcomes
- All services running with healthy status
- API responding to requests
- Document upload and processing working
- Metrics visible in Grafana dashboard

## Troubleshooting
Common issues and solutions:
1. Port conflicts: Check if ports are already in use
2. Insufficient memory: Ensure at least 4GB RAM available
3. Database connection: Verify PostgreSQL is fully started
```

Recommended image: Lab environment architecture diagram with service connections and ports
  2. Apply migrations: scripts/run-migrations.sh or Alembic
  3. Upload sample documents (use `scripts/run_document_indexing.py`)
  4. Query the API for embeddings and RAG responses
- Deliverable: Working local instance and indexed collection

Tools: Docker, docker-compose, curl/postman, repo scripts

---

Slide 16 — Data Migration & Moving to Prod

- Strategies:
  - Dump & restore for Postgres (pg_dump/pg_restore)
  - Export/Import vector collections and object buckets
  - Validate hashes and metadata during import
- Migration testing: staging environment and canary traffic

Recommended image: Migration workflow diagram

---

Slide 17 — Operational Playbooks

- Runbook examples:
  - Restoring Postgres from backup
  - Recovering MinIO bucket
  - Rebuilding a vector index from raw documents
- Include checklists and contact points

Recommended image: Runbook screenshot or template

---

Slide 18 — Compliance & Data Governance (Short)

- Data residency, audit logging, and retention policies
- Regular data inventories and access reviews
- Automate exports for compliance audits

Recommended image: Compliance checklist

---

Slide 19 — Known Limitations & Future Work

- Vector DB vendor lock-in risk — plan for exportable formats
- Index rebuilding time for large corpora — incremental indexing strategies
- Observability gaps (more traces, synthetic tests)

Recommended image: Roadmap items list

---

Slide 20 — Closing & Resources

- Repo pointers: `docker-compose.dev.yml`, `scripts/`, `docs/` (`LLAMAINDEX_ORCHESTRATOR.md`, `implementation_status.md`)
- Next steps: deploy to staging, run DR rehearsals, define RTO/RPO targets

Contact: paul@think.ke

_End of Paul deck — 20 slides with hands-on lab steps and links to repo scripts_
