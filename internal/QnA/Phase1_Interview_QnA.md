# Phase 1 - Interview Q&A (Runtime skeleton)

Scope: settings and JSON logging (P1-1), health routes and request-id middleware (P1-2), offline pytest harness (P1-3), Makefile and `.env.example` (P1-4). Answers describe what is actually built; limits are stated honestly.

---

## A. Overview and non-technical questions

**Q1. What did you build in Phase 1, in one minute?**
The foundation of a support platform, with no tickets or AI yet. A FastAPI server with central settings, structured JSON logging, health endpoints, a tracking ID on every response, an offline test suite, a Makefile for common commands, and a `.env.example` template. Every later feature plugs into this base.

**Q2. Why spend a whole phase on something users never see?**
Because it makes every later phase cheaper and safer. If logging, config, health checks and tests exist first, each new feature is traceable, configurable and verifiable from day one. Retrofitting them later is more expensive.

**Q3. Explain it to a non-technical person.**
It is the building, power, front door, security camera and "Open" sign of a restaurant, built before any cooking. Each visitor gets a tracking number, everything is written in a diary, and a health desk can say whether we are open.

**Q4. How do you know Phase 1 works?**
25 automated tests pass offline in under 2 seconds. They cover settings, logging, health routes, request IDs, the harness itself and the `.env.example` template.

**Q5. What is NOT done in Phase 1?**
No database, Redis, vector store or LLM connections (the readiness check only inspects configuration), no auth, no tickets or agents, no frontend, no Docker or cloud. Makefile targets `seed`, `ingest`, `demo`, `mcp`, `smoke` and `terraform-validate` are stubs that exit 1.

---

## B. Settings and configuration (P1-1)

**Q6. How is configuration managed?**
One `Settings` class (pydantic-settings) in `core/config.py`. It reads environment variables, falling back to `.env`, and is fetched via a cached `get_settings()`.

**Q7. Why `lru_cache` on `get_settings()`? What is the drawback?**
Settings are parsed once and shared, which is cheap and consistent. The drawback is that `.env` edits need a restart. Tests clear the cache around every test so overrides take effect.

**Q8. Why do environment variables override `.env`?**
The same code must run locally (`.env`), in tests (forced env), and in containers or cloud (injected env and secret managers). Environment-first is the standard twelve-factor approach.

**Q9. How do you stop secrets leaking from settings?**
Secret fields are `SecretStr`, so printing them shows `**********`. A custom `model_dump` masks secrets as `***` and redacts passwords inside URLs (for example `postgresql://user:***@host`). Readiness output never includes URLs or keys; a test with the password `hunter2` asserts this.

**Q10. Why does the JWT secret have a default value?**
`dev-only-change-me` keeps the demo runnable offline. It is a demo convenience; `SUPABASE_JWT_SECRET` takes precedence through `effective_jwt_secret`, and production must set a real value. Auth itself arrives in Phase 3.

**Q11. How are invalid values handled?**
Pydantic validates types and bounds (for example `embedding_dimensions > 0`, `rate_limit_per_minute > 0`). A validator lower-cases and trims provider names, so `OpenAI` and `openai` behave the same.

**Q12. Why default to `LLM_PROVIDER=fake`?**
Requirement F14: the whole system must run offline with no API key. It makes demos free and tests deterministic.

---

## C. Logging (P1-1)

**Q13. Why JSON logs?**
Machines can filter and aggregate them (CloudWatch, Log Analytics, Cloud Logging). Each line has timestamp, level, logger, message, `request_id` and `workflow_id`, plus any extra fields and exception text.

**Q14. How does the request ID get into every log line without passing it around?**
`ContextVar`s hold `request_id` and `workflow_id`. A `log_context` context manager sets and restores them, and the JSON formatter reads them. `ContextVar` is safe for concurrent async requests because each task has its own value.

**Q15. Why a context manager that restores values?**
Nested use must not leak. `log_context` only changes the IDs you pass and resets them with tokens afterwards, so a workflow ID can be added inside a request context and removed cleanly.

**Q16. Is `setup_logging()` safe to call repeatedly?**
Yes, it is idempotent. It removes its own previously installed handler (marked with a private attribute) before adding a new one, so there are no duplicate log lines when the app is created many times in tests.

---

## D. Health checks (P1-2)

**Q17. Difference between liveness and readiness?**
Liveness (`/health`, `/health/live`) means the process is up; restart it if not. It does no I/O. Readiness (`/health/ready`) means it can serve traffic with its dependencies; if not ready, stop routing traffic to it but do not restart.

**Q18. Why must liveness do no I/O?**
If liveness called the database, a database outage would make the orchestrator kill healthy app containers, turning a partial outage into a total one.

**Q19. What does readiness check today?**
Configuration only: database URL present, Redis configured or fake or demo mode, vector store valid (Qdrant needs a URL), LLM key present unless provider is `fake`. It returns 200 `ready` or 503 `degraded` with per-component status.

**Q20. Is that a real readiness check?**
Not yet, and I say so openly. It proves configuration is complete, not that dependencies are reachable. Real connection probes are planned once those dependencies exist (CLAUDE.md section 10 lists db, redis, vector store, llm).

**Q21. Why return 503 when degraded?**
Load balancers and probes act on the status code, not the body. 503 is the conventional "not ready" signal.

**Q22. Why are health routes not under `/api/v1`?**
Probes and load balancers need stable, version-independent paths, and health must not require auth or API versioning.

---

## E. Request ID middleware (P1-2)

**Q23. What does `X-Request-ID` give you?**
End-to-end tracing: the same ID appears in the response header and in every log line for that request, so a user report can be traced through logs (requirement N3).

**Q24. Do you trust an ID sent by the client?**
Only if it matches `^[A-Za-z0-9._-]{1,128}$`. Otherwise a fresh UUID replaces it. This blocks log injection (newlines, fake JSON) and header injection. A test covers an unsafe ID being replaced.

**Q25. Why a pure ASGI middleware rather than `BaseHTTPMiddleware`?**
It binds the ID for the entire request, including error paths, and avoids known `BaseHTTPMiddleware` issues with context variables and streaming. It also lets the middleware wrap the `send` callable to add the header to every response start message.

**Q26. What happens on an unhandled exception?**
The middleware logs it with the request ID and, if the response has not started, returns a JSON `{"detail": "Internal Server Error"}` with status 500 that still carries `X-Request-ID`. If the response already started, it re-raises, since headers cannot be changed.

**Q27. Why does middleware order matter?**
`add_middleware` prepends, so the last added is outermost. RequestId is added first so it sits inside CORS in code order, and CORS exposes `X-Request-ID` to browsers via `expose_headers`; without that, frontend JavaScript could not read the header. Later phases add RateLimit and Audit with the same ordering rule from CLAUDE.md section 9.

**Q28. Does it handle non-HTTP traffic?**
It passes through anything whose scope type is not `http` (for example lifespan or websocket) untouched.

---

## F. Test harness (P1-3)

**Q29. What does "offline" mean here?**
Tests need no API key, Docker, network, real Redis or Qdrant. `tests/conftest.py` forces `LLM_PROVIDER=fake`, `VECTOR_STORE=memory`, `USE_FAKE_REDIS=true`, `CHECKPOINT_DB_PATH=:memory:` and a temp SQLite file.

**Q30. Why set env vars before importing the app?**
`app.main` builds the app and reads settings at import time (`app = create_app()`). If env vars were set after, the app would already have captured real or default values.

**Q31. Why force values instead of `setdefault`?**
A developer's own `.env` or shell variables (maybe a real API key) must never leak into tests. Forcing guarantees the same result on every machine and in CI.

**Q32. Why an autouse fixture clearing the settings cache?**
Because `get_settings` is cached, a test that monkeypatches the environment would otherwise either not see its change or leak it to later tests. Clearing before and after isolates tests.

**Q33. Why a temp directory for the database?**
Tests must never touch `data/support.db`. The temp path is outside the repo, so nothing needs `.gitignore` handling and no stale state survives.

**Q34. What are the pytest-asyncio settings and why?**
`asyncio_mode = "auto"` with session loop scope, as CLAUDE.md section 13 requires. Async tests need no decorator, and one event loop is shared, which suits later session-scoped async fixtures. Mixing in `@pytest.mark.asyncio` with another scope is avoided.

**Q35. What is deliberately missing from the harness?**
The `agent_headers`, `admin_headers` and `viewer_headers` fixtures. They need JWT code (Phase 3), so adding them now would be fake.

**Q36. Show an example of a test that guards security.**
`test_ready_degraded_without_leaking_secrets` sets a database URL containing `hunter2` and asserts neither the password nor the string `postgresql` appears in the readiness response.

---

## G. Makefile and `.env.example` (P1-4)

**Q37. Why a Makefile?**
One memorable command set (`make test`, `make backend`, `make lint`) that matches the documentation and CI, and hides platform details such as the venv path and `PYTHONPATH` separator (`;` on Windows, `:` elsewhere).

**Q38. Why stub targets that exit 1 instead of empty ones?**
An empty target would report success and mislead people. A stub that prints "not implemented yet (Phase N)" and fails is honest; it follows the project's honest-status rule.

**Q39. What is `.env.example` for, and what must it never contain?**
A committed template listing every setting with safe placeholders, so a new developer can `cp .env.example .env`. It must never contain real secrets; keys are blank. `.gitignore` ignores `.env` and `.env.*` but allows `!.env.example`.

**Q40. How do you stop `.env.example` drifting from the code?**
`tests/deployment/test_env_example.py` compares `Settings.model_fields` with the keys in the file and fails if a setting is missing. It also checks secret variables are blank and the core Makefile targets exist.

**Q41. Which tool manages dependencies?**
`uv` with `pyproject.toml` and `uv.lock`; `make setup` runs `uv sync` and copies `.env.example` to `.env` if absent. (I could not execute `make` itself in the Windows Git Bash session, so Makefile targets were reviewed but not run there.)

---

## H. Design and trade-off questions

**Q42. Why FastAPI?**
Async-native, Pydantic validation, automatic OpenAPI docs, and a good fit for the later LangGraph and background-task work.

**Q43. Why create the app with a `create_app()` factory?**
Tests can build a fresh app per scenario with different settings, and the module-level `app` still works for uvicorn.

**Q44. How does Phase 1 prepare for Docker and the cloud?**
Config comes from environment variables, logs go to stdout as JSON, and liveness is I/O-free for container `HEALTHCHECK`s. Docker itself is Phase 13.

**Q45. What would you do differently or improve next?**
Make readiness open real connections with short timeouts, add the auth fixtures in Phase 3, add log level configuration through settings, and run `ruff` and tests in CI once the repo has GitHub Actions.

**Q46. How would this scale?**
The app is stateless, with config in the environment and logs on stdout, so more replicas can sit behind a load balancer. State will live in Postgres and Redis later.

**Q47. What is the biggest risk in this phase?**
Treating a configuration-only readiness check as proof of health. It is documented as a limitation, and the response contract (`status` plus `checks`) will not change when real probes arrive.

---

## I. Process questions

**Q48. How did you organise the work?**
One feature branch per sub-task (`feature/<name>`), a PR into `development` for each, tracked in `TASKS.md` with the merge order P1-1, then P1-2 and P1-4, then P1-3.

**Q49. How do you keep documentation honest?**
`MEMORY.md` and CLAUDE.md section 15.1 separate implemented, validated locally, needs credentials and deployed. Nothing is called deployed or "passes in CI" until it is.

**Q50. Walk me through a request to `/health/ready`.**
The request hits `RequestIdMiddleware`, which validates or generates an ID and binds it to the log context. It passes through `CORSMiddleware`, then the health router calls `readiness_checks(get_settings())`. The result becomes a 200 or 503 JSON response, the middleware adds `X-Request-ID`, and the logger tags any line with that ID.
