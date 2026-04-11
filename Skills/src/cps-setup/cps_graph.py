"""CPS Knowledge Graph Builder
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
