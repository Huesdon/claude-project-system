"""
CPS Knowledge Graph Builder
Scans indexed chunks for cross-references and builds a relationship graph.

Node types: file, skill, schema, concept, task
Edge types: references_file, uses_schema, invokes_skill, shares_concept, task_reference

Phase 4 additions: task ingestion from tasks.json — creates task nodes
and task_reference edges to files, schemas, skills, and other tasks.

Stored in the same SQLite DB as chunks (cps.db) in graph_nodes + graph_edges tables.
"""

import re
import json
import sqlite3
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cps.graph")

# ─── Reference Patterns ─────────────────────────────────────────────────

# File path references (relative paths in markdown)
FILE_REF_PATTERN = re.compile(
    r'(?:^|\s|`)'
    r'((?:Reference|Documentation|Output|Documentation/md)/'
    r'[A-Za-z0-9_/.@-]+\.(?:md|json|yaml|html|py|js|skill))'
    r'(?:\s|`|$|[),\\]])',
    re.MULTILINE,
)

# Schema references (JSON filenames like flags.json, ridac.json)
SCHEMA_REF_PATTERN = re.compile(
    r'\b([a-z][a-z0-9_]*\.json)\b'
)

# Skill references (kebab-case names in skill context or backticks)
# Matches: `flag-issue`, skill: flag-issue, flag-issue skill, "the flag-issue skill"
SKILL_REF_PATTERN = re.compile(
    r'(?:skill[:\s]+|`|(?<=\s))'
    r'([a-z][a-z0-9]+-[a-z0-9-]+)'
    r'(?:`|\s+skill\b|\s|$|[),.])',
    re.IGNORECASE,
)

# Known D3 schemas (used to filter false positives from generic .json mentions)
KNOWN_SCHEMAS = {
    "flags.json", "scope_flags.json", "handoffs.json", "availability.json",
    "ridac.json", "decision_risk_log.json", "rtm.json", "exceptions.json",
    "staffing.json", "engagement_config.json", "cp_manifest.json",
    "last_session.json", "project_index.json", "activity_log.json",
}

# Known D3 skills (prefix set for fuzzy matching)
KNOWN_SKILL_PREFIXES = {
    "flag-", "handoff-", "request-", "respond-", "log-", "micro-",
    "standup-", "async-", "help", "contextual-", "methodology",
    "hld", "as-built", "runbook", "decision-risk", "architecture-",
    "mermaid-", "instance-", "process-", "uat-", "workshop", "rtm",
    "story-", "unit-", "update-set", "defect-", "smoke-", "sprint-",
    "em-", "project-", "ridac", "status-", "schedule", "closure",
    "deployment-", "consultant-", "cps-", "activity-", "cp-setup",
    "project-query",
}


# ─── Graph Storage ───────────────────────────────────────────────────────

class KnowledgeGraph:
    """Builds and queries a knowledge graph from indexed chunks."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                metadata TEXT,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                context TEXT,
                source_chunk TEXT,
                FOREIGN KEY (from_node) REFERENCES graph_nodes(node_id),
                FOREIGN KEY (to_node) REFERENCES graph_nodes(node_id)
            );

            CREATE INDEX IF NOT EXISTS idx_edges_from
                ON graph_edges(from_node);
            CREATE INDEX IF NOT EXISTS idx_edges_to
                ON graph_edges(to_node);
            CREATE INDEX IF NOT EXISTS idx_edges_type
                ON graph_edges(edge_type);
            CREATE INDEX IF NOT EXISTS idx_nodes_type
                ON graph_nodes(node_type);
        """)
        self.conn.commit()

    def clear(self):
        """Drop all graph data for a full rebuild."""
        self.conn.execute("DELETE FROM graph_edges")
        self.conn.execute("DELETE FROM graph_nodes")
        self.conn.commit()

    def _upsert_node(self, node_id: str, node_type: str, label: str,
                     metadata: Optional[dict] = None):
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conn.execute(
            """INSERT INTO graph_nodes (node_id, node_type, label, metadata, last_updated)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(node_id) DO UPDATE SET
                   label = excluded.label,
                   metadata = excluded.metadata,
                   last_updated = excluded.last_updated""",
            (node_id, node_type, label, json.dumps(metadata) if metadata else None, now),
        )

    def _add_edge(self, from_node: str, to_node: str, edge_type: str,
                  context: str = "", source_chunk: str = "") -> bool:
        """Insert an edge and return True if created, False if it already existed.

        Callers should only increment their "edges_created" stat on True so
        duplicate (from, to, type) triples — common when the same cross-reference
        appears in multiple chunks of the same source file — don't inflate counts.
        """
        # Avoid duplicate edges
        existing = self.conn.execute(
            """SELECT 1 FROM graph_edges
               WHERE from_node = ? AND to_node = ? AND edge_type = ?""",
            (from_node, to_node, edge_type),
        ).fetchone()
        if existing:
            return False

        self.conn.execute(
            """INSERT INTO graph_edges (from_node, to_node, edge_type, context, source_chunk)
               VALUES (?, ?, ?, ?, ?)""",
            (from_node, to_node, edge_type, context, source_chunk),
        )
        return True

    # ─── Phase 4: Task Ingestion ────────────────────────────────────

    def _ingest_tasks(self, project_root: str = "") -> dict:
        """
        Scan tasks.json for references to files, schemas, and skills.
        Creates task: nodes and task_reference edges.
        Edges are tagged source: tasks.json so they can be cleanly rebuilt.

        Searches multiple known locations for tasks.json:
        - Reference/Claude/tasks.json (D3 project backlog)
        - tasks.json (workspace root)
        """
        stats = {"task_nodes": 0, "task_edges": 0}

        root = Path(project_root) if project_root else Path(".")
        candidates = [
            root / "Reference" / "Claude" / "tasks.json",
            root / "tasks.json",
        ]

        tasks_data = None
        tasks_path = None
        for candidate in candidates:
            if candidate.exists():
                try:
                    tasks_data = json.loads(candidate.read_text())
                    tasks_path = str(candidate)
                    break
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to read {candidate}: {e}")
                    continue

        if tasks_data is None:
            logger.info("No tasks.json found — skipping task ingestion")
            return stats

        tasks = tasks_data.get("tasks", [])
        if not tasks:
            return stats

        logger.info(f"Ingesting {len(tasks)} tasks from {tasks_path}")

        for task in tasks:
            task_id = task.get("id", "")
            title = task.get("title", "")
            description = task.get("description", "")
            tier = task.get("tier", "")
            status = task.get("status", "pending")

            if not task_id:
                continue

            # Create task node
            node_id = f"task:{task_id}"
            self._upsert_node(
                node_id=node_id,
                node_type="task",
                label=title,
                metadata={
                    "tier": tier,
                    "status": status,
                    "description": description,
                },
            )
            stats["task_nodes"] += 1

            # Scan title + description for references
            combined_text = f"{title} {description}"

            # File path references
            for match in FILE_REF_PATTERN.finditer(combined_text):
                ref_path = match.group(1)
                to_node = f"file:{ref_path}"
                self._upsert_node(to_node, "file", Path(ref_path).stem,
                                  {"path": ref_path})
                if self._add_edge(node_id, to_node, "task_reference",
                                  context=f"task:{task_id}", source_chunk="tasks.json"):
                    stats["task_edges"] += 1

            # Schema references
            for match in SCHEMA_REF_PATTERN.finditer(combined_text):
                schema_name = match.group(1)
                if schema_name not in KNOWN_SCHEMAS:
                    continue
                to_node = f"schema:{schema_name}"
                self._upsert_node(to_node, "schema", schema_name)
                if self._add_edge(node_id, to_node, "task_reference",
                                  context=f"task:{task_id}", source_chunk="tasks.json"):
                    stats["task_edges"] += 1

            # Skill references
            for match in SKILL_REF_PATTERN.finditer(combined_text):
                skill_name = match.group(1).lower()
                if not any(skill_name.startswith(p) for p in KNOWN_SKILL_PREFIXES):
                    continue
                to_node = f"skill:{skill_name}"
                self._upsert_node(to_node, "skill", skill_name)
                if self._add_edge(node_id, to_node, "task_reference",
                                  context=f"task:{task_id}", source_chunk="tasks.json"):
                    stats["task_edges"] += 1

            # depends_on / unblocks → task-to-task edges
            for dep_id in task.get("depends_on", []):
                if dep_id:
                    dep_node = f"task:{dep_id}"
                    # Don't create the dep node here — it'll be created when
                    # we process that task. Just add the edge; orphan edges
                    # are handled gracefully.
                    self._upsert_node(dep_node, "task", dep_id)
                    if self._add_edge(node_id, dep_node, "task_reference",
                                      context="depends_on", source_chunk="tasks.json"):
                        stats["task_edges"] += 1

        return stats

    # ─── Build ───────────────────────────────────────────────────────

    def build(self, conn: sqlite3.Connection, project_root: str = "") -> dict:
        """
        Scan all chunks and extract cross-references to build the graph.
        conn: the same DB connection that has the chunks table.
        project_root: workspace root for locating tasks.json (Phase 4).
        Returns build stats.
        """
        self.clear()

        stats = {
            "nodes_created": 0,
            "edges_created": 0,
            "files_scanned": 0,
            "orphaned_nodes": 0,
        }

        # Get all chunks grouped by source file
        rows = conn.execute(
            "SELECT chunk_id, source_file, heading_path, text FROM chunks"
        ).fetchall()

        # Track all source files as nodes
        source_files = set()
        for _, source_file, _, _ in rows:
            source_files.add(source_file)

        # Create file nodes for all indexed sources
        for sf in source_files:
            self._upsert_node(
                node_id=f"file:{sf}",
                node_type="file",
                label=Path(sf).stem,
                metadata={"path": sf},
            )
            stats["nodes_created"] += 1
            stats["files_scanned"] += 1

        # Scan each chunk for references
        for chunk_id, source_file, heading_path, text in rows:
            from_node = f"file:{source_file}"

            # 1. File path references
            for match in FILE_REF_PATTERN.finditer(text):
                ref_path = match.group(1)
                if ref_path == source_file:
                    continue  # skip self-references

                to_node = f"file:{ref_path}"
                # Create target node if it doesn't exist yet
                self._upsert_node(to_node, "file", Path(ref_path).stem,
                                  {"path": ref_path})

                if self._add_edge(from_node, to_node, "references_file",
                                  context=heading_path, source_chunk=chunk_id):
                    stats["edges_created"] += 1

            # 2. Schema references
            for match in SCHEMA_REF_PATTERN.finditer(text):
                schema_name = match.group(1)
                if schema_name not in KNOWN_SCHEMAS:
                    continue

                to_node = f"schema:{schema_name}"
                self._upsert_node(to_node, "schema", schema_name)
                if self._add_edge(from_node, to_node, "uses_schema",
                                  context=heading_path, source_chunk=chunk_id):
                    stats["edges_created"] += 1

            # 3. Skill references
            for match in SKILL_REF_PATTERN.finditer(text):
                skill_name = match.group(1).lower()
                # Validate against known prefixes
                if not any(skill_name.startswith(p) for p in KNOWN_SKILL_PREFIXES):
                    continue

                to_node = f"skill:{skill_name}"
                self._upsert_node(to_node, "skill", skill_name)
                if self._add_edge(from_node, to_node, "invokes_skill",
                                  context=heading_path, source_chunk=chunk_id):
                    stats["edges_created"] += 1

        # Phase 4: ingest task metadata as graph edges
        task_stats = self._ingest_tasks(project_root)
        stats["task_nodes"] = task_stats.get("task_nodes", 0)
        stats["task_edges"] = task_stats.get("task_edges", 0)
        stats["edges_created"] += task_stats.get("task_edges", 0)

        self.conn.commit()

        # Count orphaned nodes (no incoming or outgoing edges)
        orphans = conn.execute("""
            SELECT COUNT(*) FROM graph_nodes n
            WHERE NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.from_node = n.node_id)
            AND NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.to_node = n.node_id)
        """).fetchone()[0]
        stats["orphaned_nodes"] = orphans

        # Node count from DB (includes targets created during scan)
        stats["nodes_created"] = conn.execute(
            "SELECT COUNT(*) FROM graph_nodes"
        ).fetchone()[0]

        return stats

    # ─── Query ───────────────────────────────────────────────────────

    def query_node(self, node_id: str) -> Optional[dict]:
        """Get a node and all its edges."""
        row = self.conn.execute(
            "SELECT node_id, node_type, label, metadata FROM graph_nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if not row:
            return None

        outgoing = self.conn.execute(
            "SELECT to_node, edge_type, context FROM graph_edges WHERE from_node = ?",
            (node_id,),
        ).fetchall()
        incoming = self.conn.execute(
            "SELECT from_node, edge_type, context FROM graph_edges WHERE to_node = ?",
            (node_id,),
        ).fetchall()

        return {
            "node_id": row[0],
            "node_type": row[1],
            "label": row[2],
            "metadata": json.loads(row[3]) if row[3] else None,
            "outgoing": [{"to": r[0], "type": r[1], "context": r[2]} for r in outgoing],
            "incoming": [{"from": r[0], "type": r[1], "context": r[2]} for r in incoming],
        }

    def query_neighbors(self, node_id: str, depth: int = 1) -> dict:
        """BFS traversal up to `depth` hops from a node."""
        visited = set()
        frontier = {node_id}
        result_nodes = []
        result_edges = []

        for _ in range(depth):
            next_frontier = set()
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)

                node = self.query_node(nid)
                if node:
                    result_nodes.append({
                        "node_id": node["node_id"],
                        "node_type": node["node_type"],
                        "label": node["label"],
                    })
                    for edge in node["outgoing"]:
                        result_edges.append({"from": nid, **edge})
                        next_frontier.add(edge["to"])
                    for edge in node["incoming"]:
                        result_edges.append({"to": nid, **edge})
                        next_frontier.add(edge["from"])

            frontier = next_frontier - visited

        return {
            "root": node_id,
            "depth": depth,
            "nodes": result_nodes,
            "edges": result_edges,
        }

    def find_orphans(self) -> list[dict]:
        """Nodes with zero edges (indexed but nothing references them)."""
        rows = self.conn.execute("""
            SELECT n.node_id, n.node_type, n.label FROM graph_nodes n
            WHERE NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.from_node = n.node_id)
            AND NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.to_node = n.node_id)
        """).fetchall()
        return [{"node_id": r[0], "type": r[1], "label": r[2]} for r in rows]

    def find_clusters(self, min_size: int = 3) -> list[list[str]]:
        """Connected components using union-find. Returns clusters of min_size or more."""
        # Load all nodes
        nodes = [r[0] for r in self.conn.execute(
            "SELECT node_id FROM graph_nodes"
        ).fetchall()]
        parent = {n: n for n in nodes}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        edges = self.conn.execute(
            "SELECT from_node, to_node FROM graph_edges"
        ).fetchall()
        for from_n, to_n in edges:
            if from_n in parent and to_n in parent:
                union(from_n, to_n)

        # Group by root
        clusters: dict[str, list[str]] = {}
        for n in nodes:
            root = find(n)
            clusters.setdefault(root, []).append(n)

        return [c for c in clusters.values() if len(c) >= min_size]

    def stats(self) -> dict:
        """Graph summary stats."""
        node_count = self.conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
        edge_count = self.conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]

        type_counts = {}
        for row in self.conn.execute(
            "SELECT node_type, COUNT(*) FROM graph_nodes GROUP BY node_type"
        ).fetchall():
            type_counts[row[0]] = row[1]

        edge_type_counts = {}
        for row in self.conn.execute(
            "SELECT edge_type, COUNT(*) FROM graph_edges GROUP BY edge_type"
        ).fetchall():
            edge_type_counts[row[0]] = row[1]

        orphan_count = self.conn.execute("""
            SELECT COUNT(*) FROM graph_nodes n
            WHERE NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.from_node = n.node_id)
            AND NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.to_node = n.node_id)
        """).fetchone()[0]

        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "orphaned_nodes": orphan_count,
        }
