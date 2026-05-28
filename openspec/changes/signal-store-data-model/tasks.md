## 1. Setup

- [x] 1.1 Add `sqlalchemy` and `alembic` to project dependencies; add `psycopg2-binary` for Postgres support
- [x] 1.2 Create `fennec/signal/` package with `__init__.py`, `models.py`, `store.py`, `propagation.py`
- [x] 1.3 Configure Alembic with `alembic.ini` pointing to SQLite by default

## 2. Schema and Models

- [x] 2.1 Define `Verdict` ORM model in `models.py` with all required fields
- [x] 2.2 Define `SanitizerTrust` ORM model in `models.py`
- [x] 2.3 Write initial Alembic migration creating both tables with correct indexes
- [x] 2.4 Verify migration runs cleanly against both SQLite and Postgres

## 3. Signal Store CRUD

- [x] 3.1 Implement `SignalStore.write_verdict(verdict)` — inserts verdict record
- [x] 3.2 Implement `SignalStore.is_suppressed(path_hash)` — returns True if active `wont_fix` exists
- [x] 3.3 Implement `SignalStore.get_trust_scores(org_id)` — returns `Dict[pattern, trust_score]`, EXCLUDING `wont_fix`
- [x] 3.4 Write unit test: write `wont_fix` verdict → assert NOT returned by `get_trust_scores()`
- [x] 3.5 Write unit test: `is_suppressed()` returns True for known `path_hash`, False otherwise

## 4. Path Hash Utility

- [x] 4.1 Implement `compute_path_hash(function_ids: List[str]) -> str` using `sha256(sorted(ids))`
- [x] 4.2 Write tests: same IDs → same hash, different IDs → different hash, order-insensitive

## 5. Sanitizer Propagation

- [x] 5.1 Implement `PropagationJob.run(org_id, threshold=3)` — recomputes all `sanitizer_trust` rows
- [x] 5.2 Implement cross-service propagation logic: pattern with verdicts across ≥ 2 services → org-scoped trust
- [x] 5.3 Write integration test: 3 false_positive verdicts across 2 services → trust propagated; 3 from 1 service → not propagated
- [x] 5.4 Wire propagation job as a CLI command: `fennec propagate --org-id <id>`
