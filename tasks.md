# LlamaIndex Orchestrator Usage Tracking — Tasks

This task adds DB-backed usage tracking for the agency-based chatbot (LlamaIndex FunctionAgent) and its tools, and removes redundant orchestrator code.

## Goals
- Persist when the agent runs and when a tool is invoked, with collection/agency info.
- Enable aggregation such as: tool calls per collection, chats per collection.
- Keep PII out of events; leverage existing ChatEventService redaction.
- Clean up duplicate/unnecessary orchestrator files.

## User stories
- As an analyst, I can see how many times each agency tool was called over time to learn which collections are most used.
- As a product owner, I can measure how many questions were answered per collection to prioritize content updates.
- As an engineer, I can query raw events for troubleshooting a session.

## Deliverables
- Event emission in `app/core/llamaindex_orchestrator.py` for:
  - agent_invocation: started/completed/failed
  - tool_search_documents: started/completed/failed with { collection, count?, error? }
- API layering updated to pass DB session to orchestrator (agency-scoped endpoint).
- Remove duplicate `orchestrator_clean.py` (or mark deprecated) to reduce confusion.
- Docs: requirements/use-cases and this task list.

## Tasks
1) Add lightweight event context and emit helpers in LlamaIndex orchestrator [Done]
2) Emit tool events from static and dynamic tools [Done]
3) Emit agent invocation events [Done]
4) Wire API `process_chat_by_agency` to pass db to orchestrator [Done]
5) Mark `app/core/orchestrator_clean.py` as deprecated placeholder [Done]
6) Create docs (requirements and tasks) [Done]
7) Follow-ups (deferred):
   - Wire DB to default `process_chat` endpoint CompatibilityAgent path
   - Add aggregation queries/endpoints (e.g., counts by collection)
   - Extract sources/snippets in outputs for better attribution

## Validation
- Session runs produce ChatEvent rows for agent start/completion.
- Tool invocations produce ChatEvent rows with event_type=tool_search_documents and event_data.collection.
- No exceptions thrown if DB/session not provided (no-op emissions).
