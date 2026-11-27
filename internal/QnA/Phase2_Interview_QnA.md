# Phase 2 - Interview Q&A (Persistence and demo data)

Scope: entities and category enum (P2-1), Postgres schema, RLS and migrations (P2-2), repository layer
(P2-3), sample data and demo bootstrap (P2-4). Answers describe what is actually built; limits are
stated honestly.

---

## A. Overview and non-technical questions

**Q1. What did you build in Phase 2, in one minute?**
The system's memory. A 16-table data model, a matching Postgres schema with row-level security, a repository layer that holds all database queries, and fictional demo data that loads automatically into an empty database. There is still no AI and no business API.

**Q2. Explain it to a non-technical person.**
We designed the forms, built the filing cabinets, hired a records clerk who is the only one allowed to open them, and filled them with practice paperwork.

**Q3. How do you know it works?**
48 offline tests pass for the project at the end of Phase 2, 23 of them added in this phase. The seed command was run twice on an empty SQLite file: it loaded the data once and skipped the second time.

**Q4. What is NOT done?**
The SQL has never run on a real Postgres or Supabase. The `asyncpg` driver is not installed. No route reads the database yet, `/health/ready` does not open a connection, and there is no auth.

---

## B. Data model and enums (P2-1)

**Q5. What are the 16 tables?**
`profiles, customers, subscriptions, workspaces, products, tickets, ticket_messages, support_articles, incidents, workflow_runs, workflow_events, resolution_actions, approval_requests, escalations, customer_memory, audit_logs`.

**Q6. Why SQLAlchemy 2 with typed `Mapped` columns?**
One typed definition gives Python type hints, async support and the ability to target SQLite and Postgres from the same code.

**Q7. Why `JSON` rather than `JSONB`, and `String(36)` rather than a UUID type?**
Portability. SQLite has neither `JSONB` nor a native UUID type, and the demo must run offline. The cost is that Postgres loses `JSONB` indexing and compact UUID storage. A test fails if a Postgres-only type appears.

**Q8. Why use UUIDs instead of auto-increment ids?**
They can be generated in the application before insert, do not reveal record counts and do not collide across environments. People still see a readable `ticket_number` such as `CD-1002`.

**Q9. What does the timestamp mixin do?**
Gives every table `id`, `created_at` and `updated_at`, so the rule is written once. `created_at` and `updated_at` default to UTC now, and `updated_at` changes on update.

**Q10. Why are enum-like columns plain strings?**
Adding a value needs no database type change, and both databases behave the same. The trade-off is that the database will accept an invalid value; validation has to happen in the application using `schemas/common.py`. The repositories do not enforce it today.

**Q11. How many ticket categories are there, and where are they defined?**
Exactly ten, defined first in `backend/app/schemas/common.py`: `login_issue, billing, api_failure, workspace_permissions, storage_quota, integration, feature_request, account, security, other`. One source avoids two lists drifting apart.

**Q12. Why `StrEnum`?**
Each member is also a string, so it serialises to JSON and stores in a string column without conversion.

**Q13. Why is `Ticket.category` nullable?**
A new ticket has not been classified. Classification is the workflow's job in a later phase, so seeded tickets have no category or severity.

**Q14. Why store workflow state as JSON?**
The workflow state is a nested document that changes shape as agents are added. Fields needed for filtering, such as status and current node, are separate columns.

---

## C. Postgres schema, security and migrations (P2-2)

**Q15. Why keep both SQLAlchemy models and `schema.sql`?**
The models drive the SQLite demo; `schema.sql` is for the Supabase SQL editor. `schema.sql` is the authority for table count, and a test compares its tables and columns with the models.

**Q16. What does that sync test not catch?**
It compares table and column names only, plus a few text checks. It does not prove types, constraints or syntax are right on a real server. Running the SQL on Postgres in CI would close that gap.

**Q17. What is Row Level Security?**
A Postgres feature that filters which rows a database role may read or write, enforced by the database itself rather than only by application code.

**Q18. What are your RLS rules?**
RLS is enabled on all tables. Signed-in users with a `viewer`, `agent` or `admin` profile can read them. A user can read their own profile. There are no insert, update or delete policies, so writes happen only through the backend's service-role key.

**Q19. How does the database know a user's role?**
A function, `current_support_role()`, looks up the `profiles` row matching the email in the JWT.

**Q20. Why is that function `SECURITY DEFINER`?**
So it can read `profiles` even though RLS limits a user to their own row, without recursive policy checks. A hardening step I would add is pinning its `search_path`.

**Q21. What happens if the service-role key leaks?**
It bypasses RLS, so the attacker gets full access. It must stay server-side, never in the browser or the repository, and be rotated if exposed.

**Q22. What does the `set_updated_at()` trigger add if the ORM already sets `updated_at`?**
It also covers changes made outside the application, such as manual SQL.

**Q23. How do you handle schema changes?**
Add a numbered migration, update the models and `schema.sql`, and never edit an applied migration. Current files are `0001_initial_schema.sql` and `0002_enable_rls.sql`. There is no migration runner such as Alembic yet; they are applied manually.

**Q24. Does `create_tables()` apply migrations?**
No. It creates missing tables only and never alters existing ones. If a model changes, an old SQLite demo file must be recreated.

---

## D. Repository layer (P2-3)

**Q25. What is the repository pattern and why use it?**
A layer that contains all database queries. Services ask for what they need without writing SQL, queries are tested in one place, and the database can change without touching business code.

**Q26. Why do repositories flush but never commit?**
One business action may touch several tables. The caller owns the transaction, so everything succeeds or fails together.

**Q27. What is the difference between flush and commit?**
Flush sends pending changes to the database inside the open transaction, so constraints are checked and defaults are available. Commit makes them permanent.

**Q28. What does `session_scope()` do?**
Opens an async session, commits if the block succeeds, rolls back on any error and re-raises.

**Q29. Why async database access?**
FastAPI is async; while one request waits on the database, the server can serve others. It required `greenlet`, installed through `sqlalchemy[asyncio]`.

**Q30. Why `expire_on_commit=False`?**
Objects stay readable after commit. Otherwise accessing an attribute would trigger a reload, which fails in async code outside the session.

**Q31. How do you avoid N+1 queries and async lazy-load errors?**
Queries that need related data use `selectinload`, for example ticket search loads customers in one extra query.

**Q32. Why switch on foreign keys for SQLite?**
SQLite does not enforce them by default. Enabling the pragma on every connection makes the demo reject orphan records, as Postgres would.

**Q33. How does search protect against injection and wildcards?**
SQLAlchemy binds values as parameters, which prevents SQL injection. A helper also escapes `%` and `_`, so a search for `%` matches a literal percent sign.

**Q34. How does pagination work?**
Offset and limit with a total count. Page is at least 1 and page size is clamped to 1–100. For very large tables, keyset pagination would perform better.

**Q35. Two agents approve and reject at the same time. What happens?**
`decide()` runs one `UPDATE ... WHERE id = ? AND status = 'pending'`. Only one update matches a row; the other returns `None`. The database settles the race, not a read-then-write check.

**Q36. How is the audit log protected?**
The audit repository refuses `update`, and RLS has no write policies for users. It is not tamper-proof: backend code with direct database access could still change rows.

**Q37. How are duplicate memory notes avoided?**
`add_note` looks for the same customer, type and content before inserting. There is no unique constraint, so two simultaneous writes could both insert.

**Q38. How are ticket numbers generated, and is it safe?**
It takes the highest numeric `CD-` number plus one. Concurrent requests could pick the same number; the unique constraint rejects the second, but there is no retry yet. A database sequence would be better.

**Q39. Where are secrets removed from memory notes?**
Not in the repository. That belongs to the memory layer in a later phase, and it is not built yet.

---

## E. Sample data and bootstrap (P2-4)

**Q40. What data is seeded?**
3 demo users, 8 customers, 8 subscriptions, 9 workspaces, 5 products, 2 incidents, 15 knowledge articles, 13 tickets with their first messages, and a few memory notes. All fictional.

**Q41. Why were these 13 tickets chosen?**
Each exercises a behaviour planned for later: refund approval, rate limits, storage quota, security, data loss, GDPR deletion, payment dispute, MFA recovery, and a prompt-injection attempt (`CD-1013`).

**Q42. When does seeding run?**
At startup and through `make seed`, only when `DEMO_MODE` is true and there are no customers.

**Q43. Why one transaction?**
A partial failure leaves the database empty rather than half-filled, so the next start can retry cleanly. A test forces a failure and checks this.

**Q44. How is it idempotent?**
The emptiness check skips a second load; a test starts the app twice and the counts stay the same.

**Q45. Is the emptiness check safe with several replicas?**
Not fully. Two instances could both see an empty database; the deterministic ids and unique constraints would make one fail at startup. A lock or a separate seed job would fix it.

**Q46. Why deterministic ids?**
`uuid5` from a natural key gives the same id on every run, so SQLite, `seed.sql` and tests agree.

**Q47. Can `seed.sql` be run twice?**
It is written to be safe with `ON CONFLICT (id) DO NOTHING`, inside a transaction. It has not been run against a real Postgres.

**Q48. How are knowledge articles loaded?**
Markdown files with YAML front matter. The file name is the slug, the category is validated against the enum, and `yaml.safe_load` avoids executing arbitrary content. Search and chunking come in a later phase.

**Q49. Why did you change an existing test?**
The readiness test points at an unreachable Postgres URL. Now that startup creates tables, running startup would try to connect, so the test calls the route without running startup.

**Q50. What happens if the database is down at startup?**
Startup fails. That is fail-fast behaviour: the app does not start in a broken state. Production would add connection retries and clear logging.

---

## F. Design, limitations and process

**Q51. Walk me through the layers.**
API, then services, then repositories, then models and the database. Today only health routes exist in the API; the seed service is the first service. The API holds no business rules and repositories call no language models.

**Q52. Why SQLite for the demo and Postgres for the cloud?**
SQLite needs no setup, which meets the offline requirement. Postgres adds concurrency, RLS and managed hosting. Behaviour differs, for example SQLite drops timezone information, so tests on SQLite alone are not enough.

**Q53. What would you improve?**
Use `Numeric` instead of `Float` for money, add a unique constraint on `subscriptions.customer_id` to match the one-to-one relationship, add database check constraints for enum values, adopt a migration tool, and test against real Postgres.

**Q54. How is personal data handled?**
Only invented data is seeded, using `.example` addresses. Deletion handling, secret scrubbing and access control through the API are later phases.

**Q55. How did you organise the work?**
One feature branch per sub-task with a pull request into the development branch: P2-1 first, then P2-2 and P2-3, then P2-4.
