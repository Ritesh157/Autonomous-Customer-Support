# Phase 2 - System Design Evolution (Persistence and demo data)

Each stage below is one sub-task. The diagram grows as the sub-task lands. Dashed lines mean
"designed or mirrored, but not connected or not run".

## Stage 0 - Starting point (end of Phase 1)

A running API with settings, logging and health routes. Nothing is stored.

```mermaid
flowchart LR
    C["Client / probe"] --> API["FastAPI<br/>RequestId + CORS"]
    API --> H["Health routes"]
    S["Settings"] --> API
    S --> H
```

## Stage 1 - P2-1 SQLAlchemy entities and category enum

```mermaid
flowchart LR
    ENUM["schemas/common.py<br/>10 categories + other enums"]
    ENT["models/entities.py<br/>16 SQLAlchemy tables"]
    ENUM -. "valid values for string columns" .-> ENT
```

Design choices:
- One model for two databases: `JSON` (not `JSONB`) and `String(36)` UUIDs work on SQLite and Postgres.
- Every table has `id`, `created_at`, `updated_at`.
- Enum-like columns are plain strings. The database does not enforce the allowed values.

### Data model at this stage

```mermaid
erDiagram
    customers ||--o| subscriptions : has
    customers ||--o{ workspaces : owns
    customers ||--o{ tickets : raises
    customers ||--o{ customer_memory : "remembered by"
    tickets ||--o{ ticket_messages : contains
    tickets ||--o{ workflow_runs : "processed by"
    workflow_runs ||--o{ workflow_events : traces
    tickets ||--o{ workflow_events : about
    tickets ||--o{ resolution_actions : "resolved by"
    workflow_runs |o--o{ resolution_actions : plans
    workflow_runs ||--o{ approval_requests : requests
    tickets ||--o{ approval_requests : about
    tickets ||--o{ escalations : "escalated as"
    tickets |o--o{ customer_memory : "source of"
```

Standalone tables (no foreign keys): `profiles`, `products`, `support_articles`, `incidents`, `audit_logs`.

## Stage 2 - P2-2 Postgres schema, RLS and migrations

```mermaid
flowchart LR
    ENT["models/entities.py"] -. "mirrored, checked by tests" .-> DDL["database/schema.sql<br/>16 tables + set_updated_at triggers"]
    DDL --- MIG["migrations/<br/>0001 schema, 0002 RLS"]
    RLS["database/rls_policies.sql"] --- MIG
    DDL -. "not yet run" .-> PG[("Postgres / Supabase")]
    RLS -. "not yet run" .-> PG
```

Access model as designed:

```mermaid
flowchart LR
    BR["Browser (anon key)"] -. "no policy: denied" .-> T[("Tables with RLS on")]
    ST["Signed-in staff<br/>viewer / agent / admin"] -. "SELECT only" .-> T
    BE["Backend (service-role key)"] -. "reads and writes, bypasses RLS" .-> T
```

Staff roles come from the `profiles` row matching the token email. A signed-in user can also read their own profile.

## Stage 3 - P2-3 Repository layer

```mermaid
flowchart TB
    CALL["Callers (services; API later)"] --> SC["core/database.py<br/>session_scope: commit or rollback"]
    CALL --> REPO["repositories/<br/>all SQL, flush only"]
    SC --> ENG["Async engine<br/>one per database URL"]
    REPO --> SC
    REPO --> ENT["models/entities.py"]
    ENG --> DB[("SQLite<br/>foreign keys ON")]
```

| Repository file | Covers |
|---|---|
| `customers.py` | profiles, customers, subscriptions, workspaces, customer memory (exact duplicates skipped) |
| `tickets.py` | tickets, search, history, ticket numbers, messages, escalations |
| `workflows.py` | runs, events, resolution actions, approvals |
| `knowledge.py` | articles, incidents, products |
| `audit.py` | audit log (update is refused) |

Key rule: the caller owns the transaction. Repositories never commit.

### An approval is decided only once

```mermaid
sequenceDiagram
    participant A as Decision A
    participant B as Decision B
    participant R as ApprovalRepository
    participant D as Database
    A->>R: decide(approved)
    R->>D: UPDATE ... WHERE status = 'pending'
    D-->>R: 1 row
    R-->>A: updated approval
    B->>R: decide(rejected)
    R->>D: UPDATE ... WHERE status = 'pending'
    D-->>R: 0 rows
    R-->>B: None
```

## Stage 4 - P2-4 Sample data and demo bootstrap (end of Phase 2)

```mermaid
flowchart LR
    SD["sample_data/<br/>JSON + 15 knowledge articles"] --> SEED["services/seed_service.py"]
    MAIN["main.py lifespan"] --> CT["create_tables()"]
    MAIN --> SEED
    MK["make seed"] --> SEED
    SEED --> REPO["repositories"]
    CT --> DB[("SQLite")]
    REPO --> DB
    SQL["database/seed.sql<br/>same data and ids"] -. "not yet run" .-> PG[("Postgres")]
```

### Startup sequence

```mermaid
sequenceDiagram
    participant App as FastAPI lifespan
    participant DB as Database
    participant Seed as seed_service
    App->>DB: create_tables()
    App->>Seed: bootstrap_demo_data()
    alt DEMO_MODE off
        Seed-->>App: skipped
    else customers already exist
        Seed->>DB: count customers
        Seed-->>App: skipped
    else empty database
        Seed->>DB: insert all demo data (one transaction)
        Seed-->>App: row counts
    end
    Note over App,DB: On shutdown the engine is disposed
```

Design choices:
- Ids are derived from natural keys (uuid5), so SQLite and `seed.sql` share the same ids.
- All or nothing: a failed load leaves the database empty.
- `previous_resolutions.json` is not a table; a later phase reads it.
- Extra workspace fields (storage used, integrations, SSO, external sharing) live in `workspaces.settings`.

## Final Phase 2 design

```mermaid
flowchart TB
    C["Client / probe"] --> RID["RequestId + CORS"] --> H["Health routes"]
    subgraph Backend["FastAPI backend"]
      RID
      H
      LS["Lifespan"] --> SEED["seed_service"]
      SEED --> REPO["repositories"]
      REPO --> CORE["core/database.py"]
      REPO --> ENT["entities + enums"]
    end
    SD["sample_data/"] --> SEED
    LS --> CORE
    CORE --> DB[("SQLite demo DB")]
    subgraph Cloud["Cloud design (not yet run)"]
      SQL["schema.sql, rls_policies.sql,<br/>seed.sql, migrations"] -.-> PG[("Postgres / Supabase")]
    end
    ENT -. mirrors .-> SQL
```

## What changed from Phase 1

| Area | End of Phase 1 | End of Phase 2 |
|---|---|---|
| Storage | none | 16 tables on SQLite |
| Startup | nothing | creates tables, seeds demo data |
| Layers | API and core | adds models, repositories, services |
| Cloud database | none | SQL written, not run |

## Not yet present

- `/health/ready` still checks configuration only; it does not open the database.
- No Postgres async driver, so a `postgresql+asyncpg://` URL does not work yet.
- No business API routes, auth, Redis, vector store, LLM, tools, agents or frontend (Phase 3 onward).
