from dataclasses import dataclass, field


@dataclass
class TaintPath:
    """A taint propagation path from a source to a sink function."""
    nodes: list[dict]
    edges: list[dict]
    sanitized: bool
    hop_count: int


# --- Node upserts ---

UPSERT_FUNCTION = (
    "MERGE (f:Function {id: $id}) "
    "SET f += $props "
    "RETURN f"
)

UPSERT_FILE = (
    "MERGE (f:File {id: $id}) "
    "SET f += $props "
    "RETURN f"
)

UPSERT_MODULE = (
    "MERGE (m:Module {id: $id}) "
    "SET m += $props "
    "RETURN m"
)

UPSERT_SERVICE = (
    "MERGE (s:Service {id: $id}) "
    "SET s += $props "
    "RETURN s"
)

# --- Edge operations ---

# Edge type is injected via str.format() in client.py; value is always an EdgeType enum member.
ADD_EDGE_TEMPLATE = (
    "MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
    "MERGE (a)-[r:{edge_type}]->(b) "
    "SET r += $props"
)

DELETE_FILE_EDGES = (
    "MATCH (fn:Function {{file_path: $file_path}})-[r:CALLS|DATA_FLOW]->() "
    "DELETE r"
)

PRUNE_ORPHAN_FUNCTIONS = (
    "MATCH (f:Function) "
    "WHERE NOT (f)-[:DEFINED_IN]->() "
    "DELETE f"
)

# --- Incremental update ---

GET_FILE_COMMIT = (
    "MATCH (f:File {path: $path}) "
    "RETURN f.last_parsed_commit AS commit"
)

CLEAR_GRAPH = "MATCH (n) DETACH DELETE n"

# --- Traversal ---

# max_hops and depth are ints injected via str.format(); safe since they come from typed parameters.
FIND_TAINT_PATHS_TEMPLATE = (
    "MATCH path = (source:Function)-[:DATA_FLOW|CALLS*1..{max_hops}]->(sink:Function) "
    "WHERE source.id IN $source_ids AND sink.id IN $sink_ids "
    "RETURN path "
    "LIMIT 100"
)

GET_NEIGHBORS_TEMPLATE = (
    "MATCH (f:Function {{id: $function_id}})-[:CALLS|DATA_FLOW*1..{depth}]-(n:Function) "
    "RETURN DISTINCT n"
)
