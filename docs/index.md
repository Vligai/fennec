# Fennec — Codebase Index

AI-powered security scanner. Finds multi-hop taint paths in source code, reasons about
sanitization with an LLM, and surfaces findings as SARIF / PR comments / Jira tickets.

---

## Package map

```
fennec/
├── graph/          Neo4j graph layer (nodes, edges, traversal)
├── signal/         SQLAlchemy verdict store + sanitizer propagation
├── llm/            Prompt templates, renderer, response parser, Anthropic client
├── engine/         Agent loop orchestrator + cost/token model
├── parsers/        tree-sitter AST parsers (Python, JS, TS, Go) + graph emitter
├── output/         Finding model, SARIF renderer, PR comment, Jira webhook
├── rules/          Custom rule schema (pydantic), loader, AI suggest, dry-run
├── sharing/        Multi-tenant org rule API (FastAPI) + client with TTL cache
├── ci/             GitHub/GitLab comment posting + fennec scan CLI glue
└── cli.py          Entry point: scan / propagate / rules {suggest,dry-run,activate,publish}
```

---

## Key types

| Type | Module | Notes |
|---|---|---|
| `TaintPath` | `fennec.graph.queries` | `nodes`, `edges`, `sanitized`, `hop_count` |
| `Finding` | `fennec.output.model` | canonical output record; `id = sha256(vuln_class+path_hash)[:16]` |
| `LLMVerdict` | `fennec.llm.response` | includes `needs_more_context`, `context_request` (agent loop fields) |
| `FunctionDef` | `fennec.parsers.base` | output of all parsers; feeds `GraphEmitter` |
| `ParseResult` | `fennec.parsers.base` | language-agnostic parser output |
| `CustomRules` | `fennec.rules.schema` | pydantic; has `sources`, `sinks`, `sanitizers`, `rules`, `overrides` |
| `OrgRule` | `fennec.sharing.client` | pattern-only (no code); fetched from org rule API |
| `ScanCostConfig` | `fennec.engine.cost` | `max_hops=5`, `path_token_budget=20k`, `scan_token_budget=500k`, `confidence_threshold=0.85` |

---

## Component interfaces

```
Parsers ──► GraphEmitter ──► GraphClient (Neo4j)
                                  │
                          graph.find_taint_paths()
                                  │
                             TaintPath list
                                  │
                         PromptRenderer.render()  ◄── FunctionSource (context)
                                  │
                           LLMClient.analyze()
                                  │
                         ResponseParser.parse()  ──► LLMVerdict
                                  │
                           AgentLoop / SingleShot
                         (terminates on confidence / hops / budget)
                                  │
                              LLMVerdict
                                  │
                           Finding (output model)
                                  │
              ┌───────────────────┼──────────────────┐
           SarifRenderer    PrCommentRenderer    JiraWebhookSender
```

---

## Database (SQLAlchemy + Alembic)

Default: `sqlite:///./fennec_signals.db`. Postgres in production via `DATABASE_URL`.

| Table | Model | Purpose |
|---|---|---|
| `verdicts` | `Verdict` | developer verdicts (real_vuln / false_positive / wont_fix) |
| `sanitizer_trust` | `SanitizerTrust` | pre-computed org-scoped trust scores |
| `org_rules` | `OrgRuleRow` | org-scoped shared rules (multi-tenant) |

Alembic migrations in `alembic/versions/`. Run: `alembic upgrade head`.

---

## Graph (Neo4j)

Default: `bolt://localhost:7687`, user `neo4j`, password `fennecpassword`.  
Start locally: `docker compose up neo4j`.

**Node labels:** `Function`, `File`, `Module`, `Service`  
**Edge types:** `CALLS`, `DATA_FLOW`, `IMPORTS`, `DEFINED_IN`, `BELONGS_TO`, `CROSS_SERVICE`

Key taint properties on `Function`: `is_source`, `is_sink`, `is_sanitizer`, `taint_types[]`.

---

## Parser coverage

| Language | Parser class | File |
|---|---|---|
| Python | `PythonParser` | `fennec/parsers/python_parser.py` |
| JavaScript | `JavaScriptParser` | `fennec/parsers/javascript_parser.py` |
| TypeScript | `TypeScriptParser` | `fennec/parsers/javascript_parser.py` |
| Go | `GoParser` | `fennec/parsers/go_parser.py` |

All parsers produce `ParseResult` → `GraphEmitter.emit()` → graph upsert calls.  
Cross-file `CALLS` edges are not resolved at parse time; inferred during traversal.

---

## Agent loop termination (priority order)

1. `confidence >= 0.85` → accept verdict
2. `needs_more_context == False` → accept verdict
3. `hop_count >= max_hops (5)` → cap confidence at 0.7, use last verdict
4. token budget exceeded → cap confidence at 0.7, use last verdict

`ScanRunner` switches all remaining paths to `SingleShot` when `scan_token_budget` is exhausted.

---

## CLI commands

```
fennec scan --diff|--full [--format sarif] [--output path] [--fail-on blocking|any|none]
fennec propagate --org-id <id> [--threshold 3] [--db-url ...]
fennec rules suggest  --field sanitizer --vuln-class cmdi
fennec rules dry-run  --rule-file candidate.yaml
fennec rules activate --rule-file candidate.yaml [--force]
fennec rules publish  --org --pattern "fn()" --type sanitizer --vuln-class cmdi
```

`FENNEC_ORG_ID` + `FENNEC_API_URL` + `FENNEC_API_KEY` env vars enable org rule fetching at scan startup.

---

## CI integration

**GitHub Actions:** `.github/actions/fennec-scan/action.yml` + `entrypoint.sh`  
Inputs: `fennec-api-key`, `scan-mode`, `fail-on`, `sarif-upload`, `post-comment`.  
SARIF upload via `github/codeql-action/upload-sarif@v3`.

**GitLab CI:** `ci/gitlab/fennec.gitlab-ci.yml` (catalog component).

**Exit code policy:**

| fail-on | advisory findings | blocking findings |
|---|---|---|
| `blocking` | 0 | 1 |
| `any` | 1 | 1 |
| `none` | 0 | 0 |

---

## Custom rules format (`custom_rules.yaml`)

```yaml
sources:
  - pattern: "self.rpc_handler.get_payload()"
    type: user_input
sinks:
  - pattern: "InternalORM.raw_execute()"
    type: sqli
sanitizers:
  - pattern: "internal_security.sanitize_cmd()"
    covers: cmdi
overrides:
  - pattern: "some_org_fn()"
    action: disable   # suppress inherited org-level rule
```

Org-level rules fetched from API are merged before scan; repo rules take precedence on conflict.

---

## Test setup

All tests live under `tests/`. Neo4j and live API tests are **opt-in** via:

```bash
FENNEC_INTEGRATION_TESTS=1  # enables live Neo4j + live LLM tests
```

Unit tests use SQLite in-memory and `unittest.mock`. Run all unit tests:

```bash
pytest tests/ -k "not integration"
```

---

## What is scaffolded (not yet wired)

- `fennec/ci/scanner.py` — `run_diff_scan()` and `run_full_scan()` return `[]`. The full pipeline (parsers → graph → taint tracker → LLM) is implemented in individual modules but not yet wired into a single scan orchestrator.
- `fennec rules publish --type` does **not** currently validate the pattern against the graph (task 4.2 note: same check as AI suggest, but skipped in the CLI stub).

---

## Dependency summary

| Package | Purpose |
|---|---|
| `neo4j` | Graph DB driver |
| `sqlalchemy` + `alembic` | Relational DB ORM + migrations |
| `anthropic` | LLM API client |
| `fastapi` | Org rule hosted API server |
| `httpx` | Async HTTP (Jira, GitHub/GitLab APIs, org rule client) |
| `pydantic` | Rule schema validation |
| `pyyaml` | YAML loading |
| `tree-sitter` + `tree-sitter-languages` | AST parsing (Python/JS/TS/Go) |
| `tiktoken` | Token estimation for cost model |

---

## OpenSpec archives

All 9 changes implemented and archived under `openspec/changes/archive/2026-05-28-*/`.  
Canonical capability specs are in `openspec/specs/` (22 spec files total).
