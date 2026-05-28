from enum import Enum


class NodeLabel(str, Enum):
    FUNCTION = "Function"
    FILE = "File"
    MODULE = "Module"
    SERVICE = "Service"


class EdgeType(str, Enum):
    CALLS = "CALLS"
    DATA_FLOW = "DATA_FLOW"
    IMPORTS = "IMPORTS"
    DEFINED_IN = "DEFINED_IN"
    BELONGS_TO = "BELONGS_TO"
    CROSS_SERVICE = "CROSS_SERVICE"


# Idempotent (IF NOT EXISTS) Cypher statements run on every GraphClient startup.
SCHEMA_INIT_STATEMENTS: list[str] = [
    # Uniqueness constraints (each implicitly creates a backing index)
    "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File)     REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module)   REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service)  REQUIRE s.id IS UNIQUE",
    # Additional indexes for fast scan-start enumeration and parser upsert lookups
    "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.is_source)",
    "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.is_sink)",
    "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.file_path, f.name)",
    "CREATE INDEX IF NOT EXISTS FOR (f:File)     ON (f.last_parsed_commit)",
]
