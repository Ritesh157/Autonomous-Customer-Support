# Phase 1 - System Design Evolution (Runtime skeleton)

Each stage below is one sub-task. The diagram grows as the sub-task lands.

## Stage 0 - Starting point
Only a placeholder `main.py`. No server.

## Stage 1 - P1-1 Settings and JSON logging

```mermaid
flowchart LR
    ENV[".env / environment variables"] --> CFG["core/config.py<br/>Settings (cached get_settings)"]
    CFG --> LOG["core/logging.py<br/>JSON logs + request_id / workflow_id"]
    LOG --> OUT["stdout (JSON lines)"]
```

Design choices: one cached `Settings` object; secrets stored as `SecretStr` and masked in `model_dump`; URL passwords redacted; log lines are JSON with context ids.

## Stage 2 - P1-2 Health routes and request-id middleware

```mermaid
flowchart LR
    C["Client / probe"] -->|HTTP| RID["RequestIdMiddleware<br/>(echo safe id or new UUID)"]
    RID --> CORS["CORSMiddleware<br/>(exposes X-Request-ID)"]
    CORS --> R["Router: /health, /health/live, /health/ready"]
    R --> CFG["Settings"]
    RID -. binds id .-> LOG["JSON logger"]
    R --> RESP["Response + X-Request-ID header"]
```

- `/health` and `/health/live`: no I/O, `{"status":"ok"}`.
- `/health/ready`: configuration probes for database, redis, vector_store, llm. Returns 200 `ready` or 503 `degraded`, never leaking secrets.
- Unhandled errors become a JSON 500 that still carries the request id.

## Stage 3 - P1-3 Offline pytest harness

```mermaid
flowchart TB
    CT["tests/conftest.py<br/>forces offline env BEFORE importing app"] --> APP["create_app()"]
    CT --> FX["autouse fixture: clear settings cache"]
    T1["tests/unit"] --> APP
    T2["tests/api"] --> APP
    APP --> OFF["fake LLM, in-memory vector store,<br/>fake Redis, temp SQLite, :memory: checkpoints"]
```

## Stage 4 - P1-4 Makefile and .env.example (end of Phase 1)

```mermaid
flowchart LR
    DEV["Developer"] --> MK["Makefile<br/>setup / backend / test / lint<br/>(stubs: seed ingest demo mcp smoke terraform-validate)"]
    MK --> UV["uv + .venv"]
    MK --> API["FastAPI app (uvicorn :8000)"]
    MK --> PT["pytest (offline)"]
    EX[".env.example<br/>all Settings keys, placeholders"] -->|copy to| ENV[".env (git-ignored)"] --> API
    DT["tests/deployment<br/>checks .env.example covers Settings"] --> EX
```

## Final Phase 1 design

```mermaid
flowchart TB
    subgraph Config
      ENV[".env"] --> S["Settings"]
    end
    subgraph Backend["FastAPI backend"]
      RID["RequestId"] --> CORS["CORS"] --> H["Health router"]
      S --> H
      S --> L["JSON logging"]
      RID -.-> L
    end
    subgraph Dev
      MK["Makefile"] --> Backend
      TS["pytest harness (offline)"] --> Backend
    end
```

Not yet present: database, Redis, vector store, LLM, auth, tickets, agents, frontend (Phases 2+).
