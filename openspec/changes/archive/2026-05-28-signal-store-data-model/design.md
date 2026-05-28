## Context

The signal store is a relational store for developer verdicts on findings. It needs to be queryable by path hash, repo, service, and pattern fingerprint. It must support the propagation rule (sanitizer trust spreading across services) and strictly prevent "won't fix" data from entering training pipelines.

## Goals / Non-Goals

**Goals:**
- SQLite for local/dev, Postgres for production (same schema, different driver)
- Store all fields from the README's signal store schema
- Implement the propagation rule as an async query
- Expose sanitizer trust scores to the scan engine at query time

**Non-Goals:**
- Model training pipeline
- Real-time propagation (async batch job is sufficient)
- Cross-org sharing

## Decisions

**Decision 1: SQLite + Postgres via SQLAlchemy**

SQLAlchemy with a swappable connection string. SQLite for single-developer local use (no server); Postgres for team/hosted deployments. Same ORM models, different engine. Migration via Alembic.

**Decision 2: Schema**

```sql
-- Core verdict table
CREATE TABLE verdicts (
    id              TEXT PRIMARY KEY,       -- UUID
    path_hash       TEXT NOT NULL,          -- hash of taint path structure
    verdict         TEXT NOT NULL,          -- 'real_vuln' | 'false_positive' | 'wont_fix'
    reviewer_id     TEXT NOT NULL,
    repo_id         TEXT NOT NULL,
    service_id      TEXT NOT NULL,
    pattern_fingerprint TEXT NOT NULL,      -- sanitizer or source/sink pattern
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sanitizer trust derived table (populated by propagation job)
CREATE TABLE sanitizer_trust (
    id              TEXT PRIMARY KEY,
    pattern         TEXT NOT NULL,          -- e.g. "internal_security.sanitize_cmd()"
    taint_type      TEXT NOT NULL,          -- 'cmdi' | 'sqli' | etc.
    org_id          TEXT NOT NULL,
    trust_score     REAL NOT NULL DEFAULT 0.0,  -- 0.0–1.0
    verdict_count   INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP NOT NULL
);
```

**Decision 3: "Won't fix" firewall**

`verdict = 'wont_fix'` is stored in `verdicts` for suppression lookup but EXCLUDED from all queries that feed trust scores or training signals. Enforced at the query layer — no application-layer filtering. Any query that reads `verdicts` for non-suppression purposes MUST include `WHERE verdict != 'wont_fix'`.

**Decision 4: Propagation rule implementation**

Async batch job (runs every N minutes or on demand):
1. Query all `false_positive` verdicts grouped by `pattern_fingerprint`
2. For each pattern with ≥ threshold verdicts (default: 3) across multiple services in the same org
3. Upsert `sanitizer_trust` with updated `trust_score = fp_verdict_count / total_verdict_count`

The graph engine reads `sanitizer_trust` at scan start to pre-annotate function nodes with `is_sanitizer=true`.

**Decision 5: Path hash**

`path_hash = sha256(sorted(function_ids_on_path))` — structure-based, not code-content-based. Stable across whitespace changes. Two paths with the same functions in the same order produce the same hash.

## Cross-Component Interfaces

- **Finding synthesizer → Signal store**: writes `Verdict` on developer review
- **LLM reasoning engine → Signal store**: reads `sanitizer_trust` at scan start
- **Propagation job → Signal store**: reads `verdicts`, writes `sanitizer_trust`
- **Feedback loop UI → Signal store**: reads finding + verdict history per `path_hash`

## Risks / Trade-offs

- **"Won't fix" leakage** → Most critical risk. Mitigation: query-layer enforcement + integration test that asserts `wont_fix` verdicts are never returned by trust score queries.
- **Path hash collisions** → Different vulnerabilities with the same function set produce the same hash. Acceptable for FP learning; finding dedup uses a richer key.
- **Propagation threshold** → Too low = noisy trust; too high = slow learning. Start at 3, make configurable.

## Open Questions

- Should `sanitizer_trust` be a materialized view or a separate table? (Lean toward separate table — easier to inspect and debug.)
- Should the propagation job be a cron or triggered on each verdict write? (Cron initially; trigger after we understand write volume.)
