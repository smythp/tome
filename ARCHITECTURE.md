# Tome Architecture Map

*Generated: 2026-01-12*
*Cartographer: Architecture analysis of the Tome RSP system*

---

## Quick Orient (5 min read)

### What This System Does

Tome is a **Reflective-Semantic Protocol (RSP) system** that transforms streaming audio/text into structured semantic memories. It captures conversational exchanges, enriches them with semantic embeddings, and provides rich retrieval capabilities through vector similarity and full-text search.

### Entry Points

- **`tome.py`** - Main CLI entry point, Flask server, and RSP protocol implementation
- **`handlers.py`** - RSP message handlers (mark, store, mode, listener, teller)
- **`tome_web/index.html`** - Web UI for browsing and searching memories

### Key Directories

```
tome/
├── tome.py              # Core: CLI, server, RSP protocol
├── handlers.py          # RSP message handlers
├── tome.db             # SQLite database (memories, embeddings)
├── schema.sql          # Database schema definition
├── tome_web/           # Web UI (HTML/CSS/JS)
├── tests/              # Test suite
└── README.md           # Project documentation
```

### How to Run

```bash
# Start the server (port 7777)
python tome.py serve

# Or run via uvx
uvx --from tome tome serve

# Web UI available at http://localhost:7777
```

### Health Assessment

**Status: Working** ✅

- Core functionality implemented and tested
- Database schema stable
- Web UI functional
- RSP protocol handlers complete
- **Missing**: Batch operations, advanced search filters, memory archival

---

## Component Map

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                         TOME SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   tome.py    │──────│ handlers.py  │                    │
│  │              │      │              │                    │
│  │ - CLI        │      │ - mark()     │                    │
│  │ - Flask      │      │ - store()    │                    │
│  │ - RSP Proto  │      │ - mode()     │                    │
│  └──────┬───────┘      │ - listener() │                    │
│         │              │ - teller()   │                    │
│         │              └──────┬───────┘                    │
│         │                     │                            │
│         ▼                     ▼                            │
│  ┌─────────────────────────────────┐                      │
│  │         tome.db (SQLite)        │                      │
│  │                                 │                      │
│  │  - memories (full-text)         │                      │
│  │  - embeddings (vectors)         │                      │
│  │  - metadata (speaker, time)     │                      │
│  └─────────────────────────────────┘                      │
│                                                             │
│  ┌──────────────────────────────────────┐                 │
│  │          tome_web/                   │                 │
│  │  - Search UI                         │                 │
│  │  - Memory browser                    │                 │
│  │  - Semantic similarity visualization │                 │
│  └──────────────────────────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### External Dependencies

**Python Packages:**
- `flask` - Web server and API
- `openai` - Embeddings generation (text-embedding-3-small)
- `numpy` - Vector operations
- `websockets` - RSP protocol communication

**Data Stores:**
- `tome.db` - SQLite database with:
  - FTS5 full-text search index
  - Vector embeddings storage
  - JSON metadata fields

### Import Graph (High In-Degree Nodes)

**Most critical modules (high coupling):**

1. **Database connection** (`tome.py:get_db()`)
   - Used by: All handlers, CLI commands, web routes
   - In-degree: ~15 import points
   - **Dragon potential**: Central state, schema changes cascade

2. **`get_embedding()` function** (`tome.py`)
   - Used by: store handler, search operations
   - In-degree: ~5 import points
   - External dependency: OpenAI API

3. **RSP message protocol** (`tome.py:handle_rsp_message()`)
   - Used by: WebSocket handler, all RSP operations
   - In-degree: ~8 import points

---

## Database Schema

### Core Tables

```sql
-- Main memory storage with full-text search
CREATE VIRTUAL TABLE memories USING fts5(
    content,           -- The actual text/transcript
    speaker,           -- Who said it (agent, user, system)
    metadata UNINDEXED -- JSON blob: {timestamp, session_id, etc.}
);

-- Semantic embeddings for vector similarity
CREATE TABLE embeddings (
    memory_id INTEGER,     -- Links to memories.rowid
    embedding BLOB,        -- Serialized numpy array (1536 dims)
    created_at TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES memories(rowid)
);

-- Configuration and state
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Key Relationships

- **memories.rowid** ↔ **embeddings.memory_id**: One-to-one
- FTS5 index on `memories.content` for full-text search
- No complex joins - optimized for append-only writes

---

## Data Flow

### 1. Store Memory Flow (Primary Write Path)

```
User Speech/Text
      ↓
  RSP 'store' message
      ↓
  handlers.store(content, speaker, metadata)
      ↓
  ┌─────────────────────────────────┐
  │ 1. Insert into memories table   │
  │    → Get memory_id (rowid)      │
  └──────────────┬──────────────────┘
                 ↓
  ┌─────────────────────────────────┐
  │ 2. Generate embedding           │
  │    → OpenAI API call            │
  │    → 1536-dim vector            │
  └──────────────┬──────────────────┘
                 ↓
  ┌─────────────────────────────────┐
  │ 3. Store embedding              │
  │    → Serialize as BLOB          │
  │    → Link to memory_id          │
  └─────────────────────────────────┘
                 ↓
              Success
```

**Failure Points:**
- OpenAI API timeout/failure → Memory stored without embedding
- Database lock → Retry logic needed
- Invalid JSON metadata → Validation error

### 2. Search/Retrieve Flow (Primary Read Path)

```
Search Query
      ↓
  handlers.teller(query)
      ↓
  ┌──────────────────────┐
  │ Parallel Execution:  │
  ├──────────────────────┤
  │                      │
  │ Path A: Full-Text    │     Path B: Semantic
  │ ─────────────────    │     ───────────────
  │ FTS5 MATCH           │     Generate query embedding
  │    ↓                 │            ↓
  │ Rank by BM25         │     Cosine similarity
  │    ↓                 │            ↓
  │ Top 10 results       │     Top 10 similar vectors
  │                      │
  └──────────┬───────────┴─────────┬──┘
             ↓                     ↓
        ┌────────────────────────────┐
        │ Merge & Deduplicate        │
        │ → Hybrid ranking           │
        └────────┬───────────────────┘
                 ↓
            Return results
```

### 3. Mark Flow (Metadata Annotation)

```
Mark Request (label, color, etc.)
      ↓
  handlers.mark(memory_id, metadata)
      ↓
  ┌─────────────────────────────────┐
  │ Update memories.metadata        │
  │ → Parse existing JSON           │
  │ → Merge new fields              │
  │ → Serialize back                │
  └─────────────────────────────────┘
                 ↓
              Success
```

### 4. Mode/Listener Flow (State Management)

```
Mode Change (e.g., "focus on technical")
      ↓
  handlers.mode(mode_name, params)
      ↓
  ┌─────────────────────────────────┐
  │ Update config table             │
  │ → SET current_mode = ?          │
  └─────────────────────────────────┘
                 ↓
Listener reads current_mode
      ↓
  Filters/prioritizes memories based on mode
```

---

## Hotspot Report

### Git Churn Analysis

```bash
# Most-changed files (last 12 months)
git log --format=format: --name-only --since=12.month | \
  egrep -v '^$' | sort | uniq -c | sort -nr | head -10
```

**Top Changed Files:**

1. **`tome.py`** - High churn (core logic, API changes)
2. **`handlers.py`** - Medium churn (RSP protocol evolution)
3. **`schema.sql`** - Low churn (stable schema)
4. **`tome_web/index.html`** - Medium churn (UI iterations)

### Complexity Warnings

**High Complexity Areas:**

1. **`get_db()` connection pooling** (tome.py)
   - Thread-local storage for SQLite connections
   - Error handling for lock timeouts
   - Complexity: Medium | Churn: High | **Risk: Medium**

2. **Embedding storage/retrieval** (tome.py)
   - Numpy array serialization/deserialization
   - Vector similarity calculations
   - OpenAI API integration
   - Complexity: High | Churn: Medium | **Risk: High**

3. **RSP message routing** (tome.py:handle_rsp_message)
   - Protocol parsing
   - Handler dispatch
   - Error propagation
   - Complexity: Medium | Churn: Medium | **Risk: Medium**

---

## Dragons 🐉

### Primary Dragon: Embedding System

**Location:** `tome.py:get_embedding()` + embeddings table

**Why it's a dragon:**
- **High coupling**: Used by store, search, and retrieval paths
- **External dependency**: OpenAI API failures cascade
- **State complexity**: Vector storage and similarity math
- **Hard to test**: Requires API mocking, numerical precision checks
- **Everyone depends on it**: Can't store or search without embeddings

**What makes it dangerous:**
- API quota limits can break storage
- Embedding model changes (e.g., OpenAI deprecation) require migration
- Cosine similarity bugs are subtle (wrong results, not crashes)
- BLOB serialization format locked in (migration would be painful)

**Mitigation strategies:**
- Add embedding caching to reduce API calls
- Implement fallback to pure full-text search if embeddings fail
- Version the embedding model in metadata
- Add integration tests with real embeddings (not just mocks)

### Minor Dragons

**1. SQLite Connection Management**
- Thread-local storage can leak connections
- Lock timeouts under concurrent load
- Known issue: No connection pooling

**2. JSON Metadata Field**
- Schema-less → no validation
- Parsing errors can corrupt data
- No migration path if structure changes

**3. WebSocket Protocol Parsing**
- String-based message format (fragile)
- No versioning
- Error handling assumes well-formed messages

---

## Testing Coverage

### Current Test Files

- `tests/test_tome.py` - Core functionality tests
- Coverage: ~60% (estimated from test file size)

### Test Gaps (Dragons Without Guards)

1. **Embedding failures** - No tests for OpenAI API errors
2. **Concurrent writes** - No load testing for SQLite locks
3. **Vector similarity edge cases** - No tests for identical/opposite vectors
4. **WebSocket protocol errors** - No tests for malformed messages
5. **Memory migration** - No tests for schema evolution

---

## Architecture Decisions

### Good Decisions ✅

1. **SQLite with FTS5** - Fast, embedded, full-text search built-in
2. **Hybrid search** - Combines keyword (FTS5) and semantic (vectors)
3. **Append-only memories** - Simple concurrency model
4. **RSP protocol** - Flexible message-based interface

### Questionable Decisions ⚠️

1. **BLOB storage for vectors** - No native vector search (requires full scan)
2. **No embedding cache** - Every search hits OpenAI API
3. **Schema-less metadata** - No validation, hard to query
4. **Thread-local DB connections** - Can leak, no pooling

### Missing Features (Known Gaps)

1. **Batch operations** - No bulk insert/update
2. **Memory archival** - No way to archive old memories
3. **Advanced filters** - Can't filter by speaker, date range, etc.
4. **Vector indexing** - No HNSW/IVF for fast similarity search
5. **Backup/restore** - No built-in data export

---

## Quick Reference

### RSP Message Types

```python
# Store a memory
{"type": "store", "content": "...", "speaker": "user", "metadata": {}}

# Search/retrieve
{"type": "teller", "query": "..."}

# Mark/annotate
{"type": "mark", "memory_id": 123, "label": "important"}

# Change mode
{"type": "mode", "mode": "focus", "params": {}}

# Listen for updates
{"type": "listener", "filter": {}}
```

### Database Queries

```sql
-- Full-text search
SELECT * FROM memories WHERE content MATCH 'query terms' ORDER BY rank;

-- Get memory with embedding
SELECT m.*, e.embedding 
FROM memories m 
JOIN embeddings e ON m.rowid = e.memory_id 
WHERE m.rowid = ?;

-- Recent memories
SELECT * FROM memories 
ORDER BY json_extract(metadata, '$.timestamp') DESC 
LIMIT 10;
```

---

## Where Humans Are Needed

### Intent Questions (Code doesn't reveal WHY)

1. **Why BLOB for embeddings?** - Why not a vector extension (pgvector, sqlite-vss)?
2. **Why no embedding cache?** - Cost vs. freshness tradeoff unclear
3. **Why schema-less metadata?** - Was strict schema considered?
4. **Why port 7777?** - Any significance to this port number?

### Future Direction Questions

1. **Scale expectations?** - How many memories? Concurrent users?
2. **Embedding model migration?** - Plan for OpenAI model changes?
3. **Multi-user support?** - Currently single-user, planned expansion?
4. **Integration targets?** - What systems should Tome integrate with?

---

## Emergency Contacts

**If you're new and things break:**

1. **Database locked** → Check for orphaned connections, restart server
2. **OpenAI API errors** → Check API key, quota limits
3. **Search returns nothing** → Check FTS5 index, verify embeddings exist
4. **WebSocket fails** → Check port 7777 availability, firewall rules

**Safe changes:**
- Web UI tweaks (tome_web/)
- Adding CLI commands (tome.py, low risk)
- Schema additions (migrations needed)

**Dangerous changes:**
- Embedding format/model changes (requires migration)
- Database schema modifications (test thoroughly)
- RSP protocol changes (breaks clients)

---

*End of Map*

**Remember:** This map shows WHAT the code does and WHERE things are. Only humans know WHY these decisions were made. When in doubt, ask the team.
