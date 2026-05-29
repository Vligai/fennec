# Fennec

## Vision

A security analysis tool that reasons about code the way a security engineer does — understanding context, business logic, and multi-hop taint flows — rather than matching patterns. The key differentiator over traditional SAST (Semgrep, CodeQL, Checkmarx) is that it understands *intent* and *data flow across services*, not just syntax.

---

## Core architecture

```
Code Repo
    │
    ├── [1] Code ingestion & parsing
    │       AST generation · language detection · chunking · incremental diff mode
    │
    ├── [2] Code graph index
    │       Call graph · data flow · import chains · cross-file edges
    │
    ├── [3] Taint & sink tracker          ← core engine
    │       Source → sink traversal · unsanitized path detection
    │
    ├── [4] Context assembler
    │       Pulls 5–20 relevant functions per candidate path
    │
    ├── [5] LLM reasoning engine
    │       Verdict · sanitization bypass analysis · fix generation
    │
    └── [6] Finding synthesizer
            Dedup · severity scoring · SARIF / PR comment / ticket output
```

---

## Must-have components

### 1. Code ingestion & parsing
- AST generation per language (not tokenization)
- Multi-language support from day one
- **Incremental mode** — re-parse only changed files on PR diff; full-repo parse is too slow for CI
- Semantic chunking: functions, classes, and files as units

### 2. Code graph index
- Call edges (A calls B)
- Data flow edges (variable `x` from function A reaches function B)
- Import / module edges
- Cross-file and cross-service edges
- This is a **graph problem**, not a vector similarity problem — primary store should be a graph DB, not a vector DB

> **On vector DBs:** Optional, not primary. Useful for: finding semantically similar historical vulns (CVE matching), fuzzy sink discovery across unconventional codebases, cross-repo knowledge transfer. Not the right tool for traversing call graphs.

### 3. Taint & sink tracker
Built-in source/sink taxonomy as the seed layer:

```python
SOURCES = {
  "http":  ["request.body", "req.params", "request.GET", "ctx.query"],
  "env":   ["os.environ", "process.env", "getenv()"],
  "file":  ["open()", "fs.readFile", "File.read()"],
  "db":    ["cursor.fetchone()"],          # second-order SQLi
}

SINKS = {
  "sqli":  ["cursor.execute()", "db.query()", ".raw()", "knex.raw()"],
  "cmdi":  ["subprocess.call()", "exec()", "child_process.exec()"],
  "xss":   ["innerHTML", "document.write()", "res.send(user_input)"],
  "ssrf":  ["requests.get(url)", "fetch(url)"],
  "deser": ["pickle.loads()", "yaml.load()", "JSON.parse()"],
}
```

Language-specific and maintained like a library. This is "where to start looking."

### 4. Context assembler
- Extracts the minimum meaningful code slice for a candidate taint path
- Typically 5–20 functions — must fit in LLM context window without losing sanitization logic
- Getting this wrong directly tanks LLM result quality

### 5. LLM reasoning engine
- Constrained prompt: "is there sanitization on this path, and is it bypassable?" — not the open-ended "find vulnerabilities"
- **Agent loop**: LLM can request more context when unsure — fetches additional functions and re-runs. Bounded at 3–5 hops max to control cost
- Single-shot mode as fallback for high-volume, lower-severity paths

Prompt structure:
```
You are a security engineer reviewing a potential [VULN CLASS] vulnerability.

Taint path:
  Source: [source] [file:line]
  → [intermediary functions with file:line]
  → Sink: [sink] [file:line]

Code context: [assembled slice]

Questions:
1. Is there sanitization or parameterization on this path?
2. If yes, can it be bypassed?
3. Severity: critical / high / medium / low / false positive
4. Suggested fix.
```

### 6. Finding synthesizer
- Deduplication: same vuln found via multiple paths = one finding
- Severity scoring
- Exploitability estimate
- Fix suggestion
- Output formats: SARIF (IDE / GitHub), PR comments, Jira tickets, dashboard

---

## Language support

### Tier 1 — Supported (full AST parsing, graph emission, taint traversal)

| Language | Version | Parser | Extensions |
|---|---|---|---|
| Python | 3.8 + | `tree-sitter-python` | `.py` |
| JavaScript | ES2022 + | `tree-sitter-javascript` | `.js` `.jsx` `.mjs` `.cjs` |
| TypeScript | 5.x | `tree-sitter-typescript` | `.ts` `.tsx` |
| Go | 1.18 + | `tree-sitter-go` | `.go` |

All Tier 1 parsers extract: function definitions, class/struct methods, call references, import statements, and nested function scoping. Minified JS/TS files (avg line > 500 chars) are skipped automatically.

### Tier 2 — Planned (tree-sitter grammars exist; parsers not yet implemented)

| Language | Priority | Rationale |
|---|---|---|
| Java | High | Dominant in enterprise backends; high-value SQLi/XXE targets |
| Kotlin | High | JVM successor to Java; shares security surface |
| C# | High | .NET services; prevalent in enterprise and government |
| Ruby | Medium | Rails apps; common source of mass-assignment and SQLi vulns |
| PHP | Medium | Largest share of legacy web backends; SSRF/RCE risk |
| Rust | Medium | Growing systems/web use; memory safety ≠ logic safety |
| Swift | Low | iOS backends (Vapor); lower server prevalence |
| C / C++ | Low | Primarily memory-safety issues outside Fennec's taint model |

Adding a Tier 2 language follows the same pattern as existing parsers:
1. Implement `XxxParser` in `fennec/parsers/xxx_parser.py` using `tree_sitter_languages.get_parser("xxx")`
2. Register extensions in `detector.py`'s `_EXTENSION_MAP` and add to `SUPPORTED_LANGUAGES`
3. Add the language to the built-in source/sink taxonomy in `fennec/rules/loader.py`

### Cross-language taint paths

Cross-language taint (e.g. Python service calls Go service via gRPC, passes user input to a shell call) is currently an open research problem. `CROSS_SERVICE` edges exist in the graph schema but are populated via manual custom rules, not static analysis.

---

## Agent knowledge sources

The agent draws from four layers, applied in order:

| Layer | What it provides | Maintained by |
|---|---|---|
| Built-in taxonomy | Source/sink seed patterns | Core team |
| LLM baseline | Vuln class reasoning (SQLi, SSRF, etc.) from training | Pre-trained |
| Agent loop | Pulls more context until confident | Runtime |
| Custom rules | Codebase-specific sources, sinks, sanitizers | Security team |

The agent does not need a rulebook for known vulnerability classes — it reasons from first principles. Custom rules are for patterns the generic taxonomy cannot know.

---

## Custom rule schema

```yaml
# custom_rules.yaml
sources:
  - pattern: "self.rpc_handler.get_payload()"
    type: user_input
  - pattern: "KafkaConsumer.poll()"
    type: external_data        # second-order: data from queue

sinks:
  - pattern: "InternalORM.raw_execute()"
    type: sqli
  - pattern: "render_template_string()"  # Jinja2 SSTI
    type: template_injection

sanitizers:                    # highest-leverage field — reduces FP rate
  - pattern: "shlex.quote()"
    covers: cmdi
  - pattern: "internal_security.sanitize_cmd()"
    covers: cmdi
  - pattern: "parameterize()"
    covers: sqli
```

**Sanitizers are the most important field.** Generic taxonomies cover ~80% of sources and sinks. They cannot know which internal functions are trustworthy in your codebase. Every sanitizer defined directly reduces false positive rate.

### Rule authoring UX requirements
- Source / sink / sanitizer fields with pattern input
- "AI suggest" per field — scans codebase and proposes candidates; human reviews and approves
- Scope: path glob + branch targeting + advisory vs blocking mode
- Dry-run against HEAD with live FP rate estimate before shipping
- FP rate target: surface a warning when estimated rate exceeds 10%

---

## Feedback loop

```
Finding generated (taint path + LLM verdict + severity)
    ↓
Dev reviews in PR / IDE (sees path, code context, explanation)
    ↓
Dev verdict
    ├── Real vuln      → reinforces path pattern as valid detection
    ├── False positive → teaches model this sanitizer/pattern is trustworthy
    └── Won't fix      → suppression only (never feeds model training)
    ↓
Signal store (path hash · verdict · reviewer · repo/service context)
    ↓ (async)
Model update (FP patterns · sanitizer trust scores)
    ↻ next scan improved
```

### Signal store schema (minimum viable)
| Field | Type | Notes |
|---|---|---|
| `path_hash` | string | Hash of taint path structure, not raw code |
| `verdict` | enum | `real_vuln` / `false_positive` / `wont_fix` |
| `reviewer_id` | string | For audit and weight calibration |
| `repo_id` | string | Scopes learning to codebase context |
| `service_id` | string | Enables cross-service sanitizer propagation |
| `pattern_fingerprint` | string | Sanitizer or source/sink pattern that triggered |
| `created_at` | timestamp | |

### Propagation rule
When a sanitizer is marked trusted in one service (e.g. `internal_security.sanitize_cmd()`), that trust should propagate to all services in the org using the same function — not just the PR where it was reviewed.

---

## What is not needed (and why)

| Thing | Decision |
|---|---|
| Vector DB as primary store | Graph DB is the right tool for call graph traversal. Vector DB is optional/augmenting. |
| Open-ended "find all vulns" prompt | Too noisy. Constrained prompts per vuln class perform better. |
| Full-repo re-scan on every PR | Incremental diff mode required from day one for CI speed. |
| "Won't fix" fed back to model | Silently corrupts FP rate. Suppression only. |

---

## Open research problems

1. **Automatic sink discovery** — the agent doesn't know what it doesn't know. If a codebase has a novel sink (internal RPC → shell command 3 services away), no taxonomy catches it. Frontier: use LLM to identify candidate sinks by reasoning about what functions *do*, not by name matching.

2. **Multi-language monorepos** — cross-language taint paths (Python service calls Go service via gRPC, passes user input to a shell call). Requires graph edges across language boundaries.

3. **PoC generation** — using the LLM to produce a proof-of-concept exploit for confirmed findings, enabling automatic exploitability verification (and reducing false positives further).

4. **Multi-tenant rule sharing** — how orgs share custom rules and sanitizer trust across repos / teams without leaking internal implementation details.

---

## Key design principles

- **False positive rate is the product's core metric.** Devs ignore scanners that cry wolf. Every design decision should be evaluated against FP impact.
- **Sanitizers are the moat.** After enough dev verdicts, the system learns your codebase's trust model. That data is the long-term competitive advantage.
- **Incremental by default.** Full-repo scans are for initial onboarding. PR-diff mode is the steady state.
- **Constrained prompts over open-ended ones.** Specific vuln class + specific taint path + structured output format = reliable LLM verdicts.
- **Agent loop is optional, not always-on.** Run single-shot first. Invoke the loop only when the LLM requests more context or confidence is below threshold.

---

## Implementation status

All core components are implemented. See `docs/index.md` for the full module map and interface guide.

| Component | Status | Package |
|---|---|---|
| Graph DB schema (Neo4j) | ✅ complete | `fennec/graph/` |
| Language parsers (Python, JS, TS, Go) | ✅ complete | `fennec/parsers/` |
| Signal store + propagation | ✅ complete | `fennec/signal/` |
| LLM prompt library | ✅ complete | `fennec/llm/` |
| Agent loop + cost model | ✅ complete | `fennec/engine/` |
| Output formats (SARIF, PR comment, Jira) | ✅ complete | `fennec/output/` |
| Custom rule authoring (AI suggest, dry-run) | ✅ complete | `fennec/rules/` |
| CI integration (GitHub Actions, GitLab CI) | ✅ complete | `fennec/ci/`, `.github/actions/` |
| Multi-tenant org rule sharing | ✅ complete | `fennec/sharing/` |
| Scan orchestrator (wiring all components) | 🔧 scaffolded | `fennec/ci/scanner.py` |
| Tier 2 language parsers (Java, Kotlin, C#…) | 📋 planned | — |
| Cross-language taint path inference | 📋 research | — |