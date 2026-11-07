# Architecture Decision Records (ADRs)

This document records the key architectural choices, trade-offs, and design rationales for the Personal Finance Tracker API.

---

## ADR 1: Web Framework — FastAPI
* **Context**: Need a modern, high-throughput asynchronous REST API with auto-generated OpenAPI documentation, strict request validation, and clean dependency injection.
* **Decision**: Adopted **FastAPI** on Python 3.12+.
* **Rationale**:
  - Native asynchronous ASGI request handling paired with Uvicorn.
  - Seamless integration with Pydantic v2 for data parsing, schema validation, and OpenAPI 3.1 generation at `/docs`.
  - Type-safe dependency injection simplifies database sessions, Redis connections, and authentication checks.
* **Trade-offs**: Requires ASGI deployment architecture and attention to avoiding blocking I/O calls within event loop handlers.

---

## ADR 2: Asynchronous ORM — SQLAlchemy 2.0 with asyncpg
* **Context**: The database layer must handle concurrent queries asynchronously without blocking the event loop while retaining full relational data modeling and migration support.
* **Decision**: Adopted **SQLAlchemy 2.0** async with `Mapped[...]` typed declarative mappings and the `asyncpg` PostgreSQL driver.
* **Rationale**:
  - `asyncpg` is the fastest PostgreSQL driver for Python.
  - SQLAlchemy 2.0 provides static type checking support (`Mapped[T]`, `mapped_column()`) which eliminates runtime typing bugs.
  - Complete control over SQL generation, bulk upserts via `on_conflict_do_update`, and precise control over relationship loading.
* **Trade-offs**: Async ORMs require explicit eager loading (`selectinload` / `joinedload`) because lazy loading raises `MissingGreenlet` errors in async contexts.

---

## ADR 3: Monetary Representation — Decimal and NUMERIC(14, 2)
* **Context**: Financial transactions require exact numeric precision. Floating point arithmetic (`float`) causes rounding inaccuracies (e.g. `0.1 + 0.2 != 0.3`).
* **Decision**: Enforce Python's standard `Decimal` everywhere in code, mapped to PostgreSQL `NUMERIC(14, 2)` columns. Never use `float`.
* **Rationale**:
  - Fixed-point representation prevents financial drift and floating-point errors.
  - `NUMERIC(14, 2)` supports currency values up to 999,999,999,999.99 with exact cent precision.
  - Database-level check constraints (`amount > 0` on transactions, `amount >= 0` on budgets) guarantee domain validity.
* **Trade-offs**: Slightly higher memory overhead and serialization considerations, cleanly resolved via Pydantic v2's native `Decimal` serialization.

---

## ADR 4: Password Hashing — Argon2id via pwdlib
* **Context**: User passwords must be protected against brute-force and hardware-accelerated attacks (GPUs/ASICs).
* **Decision**: Adopted **Argon2id** using `pwdlib[argon2]`.
* **Rationale**:
  - Argon2id won the Password Hashing Competition (PHC) and is recommended by OWASP.
  - Provides dual resistance against side-channel timing attacks (Argon2i component) and GPU-assisted memory cracking (Argon2d component).
  - Configured with memory-hard cost parameters.
* **Trade-offs**: Higher CPU and memory consumption per login attempt compared to older algorithms like bcrypt or PBKDF2; mitigated by Redis-backed rate limiting on auth endpoints.

---

## ADR 5: Idempotency Storage — Redis with Payload Hashing
* **Context**: Network failures during `POST /transactions` could cause duplicate financial deductions. Replaying requests requires idempotent guarantees with conflict detection.
* **Decision**: Implemented an atomic Redis-based idempotency layer with SHA-256 request payload hashing and a 24-hour TTL.
* **Rationale**:
  - High write throughput with microsecond lookup speeds.
  - Ephemeral nature: transaction idempotency is crucial within minutes/hours of creation; Redis TTL automatically reclaims memory without background cleanup jobs.
  - Conflict detection: Replays with the identical payload hash return the original HTTP response; requests reusing the same `Idempotency-Key` with a mutated payload trigger an immediate `409 Conflict`.
* **Trade-offs**: If Redis suffers cold restarts without persistence, in-flight idempotency keys could be lost; however, Redis AOF/RDB persistence mitigates this.

---

## ADR 6: Report Caching and Invalidation Strategy — Redis TTL with Write Invalidation
* **Context**: Calculating monthly financial summaries requires scanning all transactions for a user and month, aggregating sums, and computing percentages. Repeated requests should not hit the database.
* **Decision**: Cache `GET /reports/monthly-summary` in Redis under `cache:reports:monthly-summary:{user_id}:{month}` with a 300-second TTL, coupled with proactive cache invalidation on transaction/budget writes.
* **Rationale**:
  - Sub-millisecond response times for dashboard overview requests.
  - Proactive write invalidation: Whenever a user creates, updates, or deletes a transaction or budget, the cache key corresponding to that user and month is evicted immediately.
  - 300s TTL serves as a safety fallback against any unexpected cache drift.
* **Trade-offs**: Invalidation logic must be called across all mutating endpoints (transactions create/update/delete, budgets upsert/delete).

---

## ADR 7: Background Task Worker — ARQ over Celery
* **Context**: Needs background scheduled jobs (e.g. daily flagging of stale accounts) with minimal operational complexity.
* **Decision**: Adopted **ARQ** (async Redis queue) instead of Celery.
* **Rationale**:
  - ARQ is built specifically for `asyncio` and Python 3.
  - Shares the existing Redis instance; requires no RabbitMQ or complex broker topology.
  - Direct async connection sharing allows database sessions in background workers to reuse the same async SQLAlchemy models without sync/async bridge overhead.
* **Trade-offs**: Does not possess the massive ecosystem of Celery plugins, but is lighter, faster, and simpler to deploy and debug.

---

## ADR 8: Pagination Paradigm — Offset-Based with Metadata Envelope
* **Context**: Collection endpoints (accounts, transactions, admin users) require pagination.
* **Decision**: Standardized on offset pagination returning `{items: [...], total: int, limit: int, offset: int, next_offset: int | None}`.
* **Rationale**:
  - Financial dashboards and management tables require jump-to-page navigation, exact total counts, and multi-column sorting (e.g. sort by date vs amount).
  - Straightforward client integration with standard data grid components.
* **Trade-offs**: High offsets on millions of rows can suffer database seek overhead. Given per-user data scoping, user transaction counts remain well within efficient execution boundaries.

---

## ADR 9: Resource Ownership and Information Leakage — 404 Not Found vs 403 Forbidden
* **Context**: When User B attempts to access or modify a resource owned by User A, returning `403 Forbidden` confirms the resource exists, exposing an existence leakage vulnerability (enumeration).
* **Decision**: Return `404 Not Found` whenever a user requests an ID they do not own.
* **Rationale**:
  - OWASP API Security Top 10 compliance: Prevents Broken Object Level Authorization (BOLA) enumeration attacks.
  - User B cannot differentiate between a non-existent UUID and a resource belonging to another user.
* **Trade-offs**: Slightly more obscure debugging during local development, resolved via structured application logs containing the internal failure reason.

---

## ADR 10: Relationship Loading — Explicit Eager Loading to Eliminate N+1
* **Context**: Serializing transactions with their assigned categories or budgets with categories in async SQLAlchemy can cause the "N+1 query problem" or throw `MissingGreenlet` exceptions.
* **Decision**: Mandate `selectinload` on all repository queries that return entities whose nested relationships are exposed in Pydantic response schemas.
* **Rationale**:
  - Executes exactly two SQL queries regardless of item count: one for the primary records and one batch query for related entities.
  - Eliminates lazy loading exceptions in async SQLAlchemy 2.0.
* **Trade-offs**: Slightly higher initial query construction complexity in repositories.
