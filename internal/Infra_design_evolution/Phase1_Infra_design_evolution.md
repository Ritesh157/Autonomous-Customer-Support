# Phase 1 - Infrastructure Design Evolution

## Honest status
There is **no Docker, Compose or cloud infrastructure yet** (planned for Phase 13; see CLAUDE.md section 15).
In Phase 1 the "infrastructure" is a single local process plus the wiring that later containers will reuse.
This document describes what exists now and the networking contract it is preparing.

## Stage 1 - Local runtime (P1-1, P1-2, P1-4)

```mermaid
flowchart LR
    B["Browser / curl / probe"] -->|"HTTP :8000"| U["uvicorn process"]
    U --> A["FastAPI app"]
    A --> M1["RequestIdMiddleware"] --> M2["CORSMiddleware"] --> R["Health router"]
    ENV[".env"] --> A
    A --> SO["stdout JSON logs"]
```

Routing table:

| Path | Purpose | I/O | Who calls it |
|---|---|---|---|
| `/health`, `/health/live` | Liveness | none | container/orchestrator probes (future), humans |
| `/health/ready` | Readiness (config probes, 503 when degraded) | none yet | load balancer / smoke test (future) |

Middleware order (request in): RequestId -> CORS -> router. `X-Request-ID` is exposed to browsers via CORS.

## Stage 2 - Offline test wiring (P1-3)

```mermaid
flowchart LR
    PT["pytest"] --> TC["FastAPI TestClient<br/>(in-process, no network)"]
    TC --> A["create_app()"]
    A -.-> F1["fake LLM"]
    A -.-> F2["in-memory vector store"]
    A -.-> F3["fake Redis"]
    A -.-> F4["temp SQLite file"]
```

No ports are opened and no external services are used; this is what lets tests run without Docker.

## Stage 3 - Configuration wiring (P1-4)

```mermaid
flowchart LR
    EX[".env.example (committed)"] -->|cp| E[".env (git-ignored)"]
    E --> S["Settings"]
    CI["Real env vars (containers / cloud secrets)"] -->|override| S
```

Environment variables override `.env`, so the same code runs locally, in tests and in containers.

## Preview: where this is heading (not built yet)

```mermaid
flowchart LR
    FE["Next.js :3000"] --> BE["FastAPI :8000<br/>HEALTHCHECK /health/live"]
    BE --> RD["Redis"]
    BE --> QD["Qdrant"]
    BE --> DB["Postgres / SQLite"]
```

Phase 1 fixes the contract: the liveness probe has no I/O, the readiness probe will verify dependencies, and config comes from environment variables.
