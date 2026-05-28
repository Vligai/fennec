## 1. Setup

- [ ] 1.1 Add `sqlalchemy` and `alembic` to project dependencies; add `psycopg2-binary` for Postgres support
- [ ] 1.2 Create `fennec/signal/` package with `__init__.py`, `models.py`, `store.py`, `propagation.py`
- [ ] 1.3 Configure Alembic with `alembic.ini` pointing to SQLite by default

## 2. Schema and Models

- [ ] 2.1 Define `Verdict` ORM model in `models.py` with all required fields
- [ ] 2.2 Define `SanitizerTrust` ORM model in `models.py`
- [ ] 2.3 Write initial Alembic migration creating both tables with correct indexes
- [ ] 2.4 Verify migration runs cleanly against both SQLite and Postgres

## 3. Signal Store CRUD

- [ ] 3.1 Implement `SignalStore.write_verdict(verdict)` — inserts verdict record
- [ ] 3.2 Implement `SignalStore.is_suppressed(path_hash)` — returns True if active `wont_fix` exists
- [ ] 3.3 Implement `SignalStore.get_trust_scores(org_id)` — returns `Dict[pattern, trust_score]`, EXCLUDING `wont_fix`
- [ ] 3.4 Write unit test: write `wont_fix` verdict → assert NOT returned by `get_trust_scores()`
- [ ] 3.5 Write unit test: `is_suppressed()` returns True for known `path_hash`, False otherwise

## 4. Path Hash Utility

- [ ] 4.1 Implement `compute_path_hash(function_ids: List[str]) -> str` using `sha256(sorted(ids))`
- [ ] 4.2 Write tests: same IDs → same hash, different IDs → different hash, order-insensitive

## 5. Sanitizer Propagation

- [ ] 5.1 Implement `PropagationJob.run(org_id, threshold=3)` — recomputes all `sanitizer_trust` rows
- [ ] 5.2 Implement cross-service propagation logic: pattern with verdicts across ≥ 2 services → org-scoped trust
- [ ] 5.3 Write integration test: 3 false_positive verdicts across 2 services → trust propagated; 3 from 1 service → not propagated
- [ ] 5.4 Wire propagation job as a CLI command: `fennec propagate --org-id <id>`
