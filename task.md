# Tasks: Close gaps in upload/crawling, indexing progress, metrics, and collection persistence

## Goals
- Persist collections in the database and stop relying on in-memory storage or static `collection_dict`.
- Provide full CRUD where appropriate (documents + webpages) and ensure related vector indexes are kept consistent.
- Expose clear indexing progress for both crawled pages and uploaded documents.
- Support per-collection and assistant-scoped metrics.
- Ensure that deleting a document/webpage also deletes its embeddings from ChromaDB.

## Current gaps (summary)
- Indexing job status (queue/task tracking) is not implemented; only background kicks without durable status.
- Analytics router is not mounted in the main API and isn’t scoped by collection/assistant yet.
- No PATCH variant for documents (PUT covers file/metadata updates via form fields).
- Test coverage missing for new deletion/indexing flows.

## Work plan (checklist)

1) DB schema and migrations (via Alembic)
- [x] Adopt Alembic for schema management; stop relying on `create_all` in production. (Configured env.py to aggregate all Base metadatas; uses sync driver.)
- [x] Ensure `webpages` and `documents` tables have `is_indexed` and `indexed_at` (captured in migrations; script deprecated).
- [x] Add new `collections` table via Alembic migration. (Applied.)
- [ ] Add CI step to verify the DB is at Alembic head and migrations apply cleanly. (Deferred)

2) Persist Collections in DB and wire API
- [x] Define `Collection` SQLAlchemy model with id (uuid str), name, description, type, created_at, updated_at, and optional owner/api_key_name.
- [x] Add migrations to create collections table; startup gated create_all for dev only.
- [x] Replace `collections_storage` usage in `fast_api_app.py` with DB CRUD (create/list/update/delete/get).
- [x] Update collection list endpoints to compute counts via DB queries (documents + webpages).
- [x] Backfill: script to import existing static `collection_dict` (kfc, kfcb, brs, odpc) into DB once. (`scripts/seed_collections.py`)

3) Stop using static `collection_dict` in RAG
- [x] Load collections from DB into `tool_loader` and cache; alias map for legacy keys.
- [x] Modify `tool_loader.get_index_dict()` to lazily initialize Chroma indexes per canonical collection_id; alias keys point to same index.
- [x] Update LlamaIndex orchestrator to build tools dynamically from DB collections; preserve legacy aliases; automatic cache refresh on collection create/update/delete.
- [x] Accept canonical UUIDs as agency tokens in `/chat/{agency}`.
- [ ] Optional: add a single generic retrieval tool name for all collections. (Deferred)

4) Document CRUD and Chroma deletion
- [x] Add PUT `/documents/{id}` to update metadata and (optionally) replace the file. If file replaced: re-upload to MinIO, mark `is_indexed=False`, delete vectors by `doc_id`, and trigger background re-indexing for the document's collection.
- [ ] Optional: add PATCH `/documents/{id}` (JSON body) for partial metadata updates without multipart. (Deferred)
- [x] Implement Chroma deletion on DELETE `/documents/{id}`:
  - [x] Utility: `delete_embeddings_for_doc(collection_id, doc_id)` added in `vectorstore_admin.py`.
  - [x] Called prior to MinIO + DB deletion; idempotent.
  - [x] Indexer uses `doc_id` metadata.

5) Webpage deletion and Chroma deletion
- [x] Add DELETE `/webpages/{id}` to remove webpage row and its vectors.
- [x] Add POST `/webpages/{id}`/recrawl to mark a single page for reprocess; sets `is_indexed=False` and clears `indexed_at`.

6) Indexing progress endpoints
- [x] Uploaded docs: Add GET `/documents/indexing-status?collection_id=...` returning `{ indexed, unindexed, progress_percent }`.
- [x] Webpages: Fix progress calculation (percentage now computed with `* 100`).
- [x] Add unified GET `/collection-stats/{id}/indexing-status` merging docs + webpages.

7) Indexing job status tracking (optional but recommended)
- [ ] Introduce in-memory (or DB-backed) tracker for indexing tasks, like `crawl_tasks`.
- [ ] Add POST `/collections/{id}/index` to start indexing; returns task_id.
- [ ] Add GET `/indexing/{task_id}` for status; GET `/indexing` to list.

8) Assistant/collection metrics
- [ ] Integrate `analytics` routers into main FastAPI app under `/analytics` (behind read permission). (Pending)
- [ ] Add optional filters to analytics endpoints to scope by `collection_id` or `assistant`. (Pending)
- [ ] Enhance chat persistence to record `retriever_type` or `agencies` in metadata. (Pending)

9) Orchestrator/tooling alignment
- [x] Use `collection_id` as Chroma collection name; alias pointers map to canonical.
- [x] Ensure ingestion metadata includes `doc_id` and `collection_id` (present); leveraged for delete.
- [x] Added `vectorstore_admin.py` for admin deletes.
 - [x] Dynamic tools generated from DB collections; automatic refresh on collection create/update/delete; legacy aliases supported; canonical UUIDs accepted.

10) Tests
- [ ] Unit test: delete-document removes rows from Chroma.
- [ ] Unit test: delete-webpage removes vectors.
- [ ] API tests: document PUT/PATCH; indexing-status endpoints.
- [ ] Orchestrator: system prompt reflects DB collections.
- [ ] Tool loader: initializes indexes for DB collections.

## API changes (proposed)
- Documents
  - PUT `/documents/{id}`: update metadata and optional file; reindex and delete vectors when file changes.
  - PATCH `/documents/{id}` (optional): partial metadata update without multipart.
  - GET `/documents/indexing-status?collection_id=...`: aggregate indexing status for uploads.
- Webpages
  - DELETE `/webpages/{id}`: delete page and its embeddings.
  - POST `/webpages/{id}/recrawl` (optional): recrawl a single page and reset indexing flags.
- Collections
  - CRUD backed by DB: POST `/collections`, GET `/collections`, GET `/collections/{id}`, PUT/PATCH `/collections/{id}`, DELETE `/collections/{id}`.
  - GET `/collections/{id}/indexing-status`: combined docs + webpages counts.
  - POST `/collections/{id}/index` + GET `/indexing/{task_id}` (optional job tracking).
- Analytics
  - Mount analytics router at `/analytics/*`; extend with `collection_id`/`assistant` filters when feasible.

## Technical notes: Chroma deletions
- We already embed metadata `doc_id` in both crawled pages and uploaded documents (via the indexer pipeline). Use this to delete.
- Implement utility (pseudo):
  ```python
  client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
  coll = client.get_or_create_collection(name=collection_id)
  coll.delete(where={"doc_id": str(doc_id)})
  ```
- Ensure `doc_id` is stored as a string consistently during ingestion; otherwise filter should match integers too.
- Consider using LlamaIndex `ChromaVectorStore` deletion if we standardize `ref_doc_id` (future improvement).

## Data model changes
- New `collections` table with: id (uuid str, PK), name (unique), description, type (documents|webpages|mixed), created_at, updated_at, api_key_name (opt).

## Risks / mitigations
- Risk: Vector deletions may leave orphans if metadata mismatch. Mitigation: Standardize metadata shape and add a one-time cleanup script.
- Risk: Changing tool loader from static dict to DB may affect agent tool names. Mitigation: keep legacy tools temporarily; introduce a generic retrieval tool.
- Risk: Long indexing jobs – prefer DB-backed job status for durability.

## Acceptance criteria
- Creating/updating/deleting collections persists in DB; API returns DB-backed data.
- Deleting a document/webpage removes corresponding vectors from Chroma for that collection.
- Indexing-status endpoints report accurate counts for documents and webpages; progress shows correct percentages.
- Orchestrator system prompt reflects DB collections; no dependency on `collection_dict` for display.
- Analytics endpoints mounted and can filter by collection/assistant where available.
- Tests pass for new endpoints and Chroma deletion flows.

## Rollout
- Phase 1: Alembic setup + baseline migrations.
- Phase 2: DB collections + replace in-memory + endpoints.
- Phase 3: Chroma deletion utility + wire into DELETE flows.
- Phase 4: Indexing status endpoints + progress fix.
- Phase 5: Document update + Webpage delete/recrawl.
- Phase 6: Tool loader/orchestrator reading from DB.
- Phase 7: Analytics mounting + filters.
- Phase 8: Tests and docs.

## Completed recently
- Alembic initialized and baseline + collections migrations added/applied.
- Collections persisted in DB with CRUD; counts computed via DB queries; seeding script added.
- RAG/tooling reads collections from DB; alias mapping preserved; canonical UUIDs accepted; auto-refresh on collection changes.
- DELETE `/documents/{id}` removes vectors (by `doc_id`), MinIO object, and DB row.
- PUT `/documents/{id}` updates metadata and optional file; clears vectors and reindexes when file changes.
- DELETE `/webpages/{id}` removes vectors and the DB row; POST `/webpages/{id}/recrawl` marks for reprocess.
- Indexing status endpoints for documents and combined collection stats implemented; webpage percentage fix applied.

## Next steps
- Add optional PATCH `/documents/{id}` (JSON) for partial updates (low risk).
- Add durable indexing job tracking endpoints (task queue + status) and optional `/collections/{id}/index` trigger.
- Mount analytics router under `/analytics` with optional `collection_id`/`assistant` filters.
- Add tests: vector deletion (docs/webpages), indexing status accuracy, and dynamic tool generation prompt content.

## Alembic setup and migration plan

1) Initialize Alembic in repo
- [ ] Add Alembic to dependencies.
- [ ] `alembic init alembic` (in repo root) to create `alembic.ini` and `alembic/` directory.
- [ ] Configure `alembic.ini` to read `DATABASE_URL` (or a dedicated `DATABASE_MIGRATIONS_URL`) from environment. Prefer using a sync driver (psycopg2) for migrations to simplify.

2) Configure env.py (metadata + URL)
- [ ] Import all model Base.metadata instances and expose to Alembic as a list:
  - `from app.db.models.document import Base as DocumentBase`
  - `from app.db.models.webpage import Base as WebpageBase`
  - `from app.db.models.chat import Base as ChatBase`
  - `from app.db.models.chat_event import Base as ChatEventBase`
  - `from app.db.models.message_rating import Base as MessageRatingBase`
  - `from app.db.models.audit_log import Base as AuditBase`
- [ ] In `env.py`: set `target_metadata = [DocumentBase.metadata, WebpageBase.metadata, ChatBase.metadata, ChatEventBase.metadata, MessageRatingBase.metadata, AuditBase.metadata]` to enable complete autogenerate.
- [ ] URL resolution: prefer `sqlalchemy.url = os.getenv("DATABASE_MIGRATIONS_URL") or os.getenv("DATABASE_URL").replace("+asyncpg", "")` so Alembic uses a sync engine even if the app uses asyncpg.

3) Create baseline migrations
- [ ] Revision 0001_initial: autogenerate current schema (documents, webpages, chats, chat_events, message_ratings, audit_logs).
- [ ] Revision 0002_indexing_columns: ensure `webpages.is_indexed/indexed_at` and `documents.is_indexed/indexed_at` exist (no-op if already present).
- [ ] Revision 0003_collections_table: add `collections` table (id [uuid/str PK], name, description, type, created_at, updated_at, api_key_name).
- [ ] Revision 0004_seed_collections (optional, data migration): seed initial agency collections from the former `collection_dict` (kfc, kfcb, brs, odpc) if desired.

4) Replace startup create_all
- [ ] Gate `create_all` behind an env flag for local dev only, or remove entirely; rely on `alembic upgrade head` for schema.

5) Developer workflow
- [ ] Create new migrations: `alembic revision --autogenerate -m "<message>"`.
- [ ] Apply: `alembic upgrade head`. Roll back: `alembic downgrade -1`.
- [ ] For existing DBs, first-time align: `alembic stamp head` (after verifying schema), then manage forward with migrations.

6) CI/CD
- [ ] Add a job to run `alembic upgrade head` against a clean test DB and fail on drift.
- [ ] Optionally run `alembic check` (if available) or a custom script to assert the current DB is at Alembic head.

7) Follow-on migrations in this project
- [ ] Migrations to support collection persistence (section 1), including any constraints/indexes.
- [ ] Any schema changes for indexing job tracking (optional section 6).
- [ ] Backfill/data migrations to map existing content to collections where necessary.
