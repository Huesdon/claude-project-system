"""
CPS MCP Server
Semantic search over project documents via sqlite-vec.

MCP protocol: JSON-RPC 2.0 over stdio.
Tools exposed: cps_search, cps_retrieve, cps_status, cps_ingest,
               cps_graph_build, cps_graph_query, cps_prime, cps_purge.

Phase 3 additions: semantic cache, knowledge graph, enhanced status.
Phase 4 additions: cps_prime (task-aware priming), targeted file refresh
                   (cps_ingest files param), task metadata graph edges.
Phase 5.1 additions: JSON array chunking (chunk_json + chunk_file dispatcher),
                     stale chunk purge (cps_purge tool + purge_stale method),
                     prime query delta injection (last_session_deltas fold).
Single-tenant addition: Removed multi-tenant namespace prefix logic and ProjectRegistry.
                        Namespace is now informational only (for cps_status display).
D3 strip: Removed engagement_id cache isolation and persona allowlist boosting (Phase 7a/7b).
Phase 8.7 addition: Self-bootstrapping dependency installer at module import.
                   Cowork sandbox resets pip-installed packages between sessions,
                   so the server must reinstall sqlite-vec, huggingface-hub, and
                   tokenizers on every cold boot or the MCP handshake silently
                   fails before any tool is registered. Mirrors the pattern in
                   cps_test_suite.py._bootstrap_deps().
"""

import os
import sys
import json
import hashlib
import logging
import sqlite3
import subprocess
import time
from glob import glob
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Dependency bootstrap (Phase 8.7) — runs before any third-party imports.
# ---------------------------------------------------------------------------
_REQUIRED_DEPS = ["sqlite-vec", "huggingface-hub", "tokenizers", "onnxruntime", "numpy"]


def _bootstrap_deps() -> None:
    _IMPORT_NAMES = ["sqlite_vec", "huggingface_hub", "tokenizers", "onnxruntime", "numpy"]

    def _try_imports() -> bool:
        try:
            import sqlite_vec  # noqa: F401
            import huggingface_hub  # noqa: F401
            import tokenizers  # noqa: F401
            import onnxruntime  # noqa: F401
            import numpy  # noqa: F401
            return True
        except ImportError:
            return False

    if _try_imports():
        return

    print("[CPS] bootstrapping missing dependencies...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *_REQUIRED_DEPS,
         "--break-system-packages", "-q"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("[CPS] FATAL: dependency bootstrap failed.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    import importlib
    import site
    for mod_name in _IMPORT_NAMES:
        sys.modules.pop(mod_name, None)
    importlib.invalidate_caches()
    for sp in site.getsitepackages():
        if sp not in sys.path:
            sys.path.insert(0, sp)

    if not _try_imports():
        print(
            "[CPS] FATAL: pip install succeeded but imports still fail. "
            "Check sandbox site-packages or dependency conflicts.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("[CPS] dependency bootstrap complete.", file=sys.stderr)


_bootstrap_deps()

import numpy as np
import sqlite_vec

from cps_chunker import chunk_markdown, chunk_json, chunk_file, Chunk
from cps_embedder import Embedder, download_model
from cps_graph import KnowledgeGraph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CPS] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("cps")

EMBEDDING_DIM = 384
CACHE_COSINE_THRESHOLD = 0.05


class SearchCache:
    def __init__(self, conn: sqlite3.Connection, threshold: float = CACHE_COSINE_THRESHOLD):
        self.conn = conn
        self.threshold = threshold
        self._hits = 0
        self._misses = 0
        self._token_savings = 0
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                query_embedding BLOB NOT NULL,
                results_json TEXT NOT NULL,
                result_chunk_ids TEXT NOT NULL,
                estimated_tokens INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def lookup(self, query_embedding: np.ndarray, query_text: str = "") -> Optional[list[dict]]:
        rows = self.conn.execute(
            "SELECT cache_id, query_embedding, results_json, estimated_tokens "
            "FROM search_cache"
        ).fetchall()

        for cache_id, stored_emb_bytes, results_json, est_tokens in rows:
            stored_emb = np.frombuffer(stored_emb_bytes, dtype=np.float32)
            distance = 1.0 - float(np.dot(query_embedding, stored_emb))
            if distance <= self.threshold:
                self._hits += 1
                self._token_savings += est_tokens
                self.conn.execute(
                    "UPDATE search_cache SET hit_count = hit_count + 1 WHERE cache_id = ?",
                    (cache_id,),
                )
                self.conn.commit()
                return json.loads(results_json)

        self._misses += 1
        return None

    def store(self, query_text: str, query_embedding: np.ndarray,
              results: list[dict], estimated_tokens: int = 0):
        chunk_ids = json.dumps([r.get("chunk_id", "") for r in results])
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conn.execute(
            """INSERT INTO search_cache
               (query_text, query_embedding, results_json, result_chunk_ids,
                estimated_tokens, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (query_text, query_embedding.tobytes(), json.dumps(results),
             chunk_ids, estimated_tokens, now),
        )
        self.conn.commit()

    def invalidate_chunks(self, chunk_ids: set[str]):
        if not chunk_ids:
            return 0
        rows = self.conn.execute(
            "SELECT cache_id, result_chunk_ids FROM search_cache"
        ).fetchall()
        removed = 0
        for cache_id, stored_ids_json in rows:
            stored_ids = set(json.loads(stored_ids_json))
            if stored_ids & chunk_ids:
                self.conn.execute(
                    "DELETE FROM search_cache WHERE cache_id = ?", (cache_id,)
                )
                removed += 1
        if removed:
            self.conn.commit()
        return removed

    def clear(self):
        self.conn.execute("DELETE FROM search_cache")
        self.conn.commit()
        self._hits = 0
        self._misses = 0
        self._token_savings = 0

    def stats(self) -> dict:
        total_entries = self.conn.execute(
            "SELECT COUNT(*) FROM search_cache"
        ).fetchone()[0]
        total_db_hits = self.conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) FROM search_cache"
        ).fetchone()[0]
        total_queries = self._hits + self._misses
        hit_rate = (self._hits / total_queries * 100) if total_queries > 0 else 0.0
        return {
            "cache_entries": total_entries,
            "session_hits": self._hits,
            "session_misses": self._misses,
            "session_hit_rate_pct": round(hit_rate, 1),
            "lifetime_hits": total_db_hits,
            "estimated_token_savings": self._token_savings,
        }


class VectorStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                source_file TEXT NOT NULL,
                heading_path TEXT NOT NULL,
                text TEXT NOT NULL,
                line_start INTEGER,
                line_end INTEGER,
                word_count INTEGER,
                estimated_tokens INTEGER,
                frontmatter TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_file)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_chunk_id ON chunks(chunk_id)"
        )
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "chunks_vec" not in tables:
            self.conn.execute(
                "CREATE VIRTUAL TABLE chunks_vec USING vec0(embedding float[384])"
            )
        self.conn.commit()

    def insert_chunk(self, chunk: Chunk, embedding: np.ndarray):
        cur = self.conn.execute(
            """INSERT OR REPLACE INTO chunks
               (chunk_id, source_file, heading_path, text, line_start, line_end,
                word_count, estimated_tokens, frontmatter)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chunk.chunk_id, chunk.source_file, chunk.heading_path,
                chunk.text, chunk.line_start, chunk.line_end,
                chunk.word_count, chunk.estimated_tokens,
                json.dumps(chunk.frontmatter) if chunk.frontmatter else None,
            ),
        )
        rowid = cur.lastrowid
        self.conn.execute("DELETE FROM chunks_vec WHERE rowid = ?", (rowid,))
        self.conn.execute(
            "INSERT INTO chunks_vec(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.tobytes()),
        )

    def delete_by_source(self, source_file: str):
        rows = self.conn.execute(
            "SELECT rowid FROM chunks WHERE source_file = ?", (source_file,)
        ).fetchall()
        for (rowid,) in rows:
            self.conn.execute("DELETE FROM chunks_vec WHERE rowid = ?", (rowid,))
        self.conn.execute(
            "DELETE FROM chunks WHERE source_file = ?", (source_file,)
        )

    def search(
        self, query_embedding: np.ndarray, limit: int = 5, source_filter: Optional[str] = None
    ) -> list[dict]:
        rows = self.conn.execute(
            "SELECT rowid, distance FROM chunks_vec WHERE embedding MATCH ? AND k = ?",
            (query_embedding.tobytes(), limit * 3 if source_filter else limit),
        ).fetchall()
        results = []
        for rowid, distance in rows:
            chunk_row = self.conn.execute(
                """SELECT chunk_id, source_file, heading_path, text,
                          word_count, estimated_tokens, line_start, line_end
                   FROM chunks WHERE rowid = ?""",
                (rowid,),
            ).fetchone()
            if chunk_row is None:
                continue
            if source_filter and source_filter not in chunk_row[1]:
                continue
            results.append({
                "chunk_id": chunk_row[0],
                "source_file": chunk_row[1],
                "heading_path": chunk_row[2],
                "text": chunk_row[3],
                "word_count": chunk_row[4],
                "estimated_tokens": chunk_row[5],
                "line_start": chunk_row[6],
                "line_end": chunk_row[7],
                "distance": round(distance, 4),
                "score": round(1.0 - distance, 4),
            })
            if len(results) >= limit:
                break
        return results

    def retrieve(self, chunk_id: str) -> Optional[dict]:
        row = self.conn.execute(
            """SELECT chunk_id, source_file, heading_path, text,
                      line_start, line_end, word_count, estimated_tokens, frontmatter
               FROM chunks WHERE chunk_id = ?""",
            (chunk_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "chunk_id": row[0], "source_file": row[1], "heading_path": row[2],
            "text": row[3], "line_start": row[4], "line_end": row[5],
            "word_count": row[6], "estimated_tokens": row[7],
            "frontmatter": json.loads(row[8]) if row[8] else None,
        }

    def stats(self) -> dict:
        total_chunks = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        total_files = self.conn.execute(
            "SELECT COUNT(DISTINCT source_file) FROM chunks"
        ).fetchone()[0]
        total_tokens = self.conn.execute(
            "SELECT COALESCE(SUM(estimated_tokens), 0) FROM chunks"
        ).fetchone()[0]
        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "total_tokens_indexed": total_tokens,
        }

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


class IngestPipeline:
    def __init__(self, store: VectorStore, embedder: Embedder, manifest_path: str, namespace: str = ""):
        self.store = store
        self.embedder = embedder
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
        self.namespace = namespace

    def _load_manifest(self) -> dict:
        path = Path(self.manifest_path)
        if path.exists():
            return json.loads(path.read_text())
        return {"files": {}, "last_ingest": None}

    def _save_manifest(self):
        Path(self.manifest_path).write_text(json.dumps(self.manifest, indent=2))

    @staticmethod
    def _file_hash(path: str) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def ingest(self, source_paths: list[str], project_root: str = "") -> dict:
        root = Path(project_root) if project_root else Path(".")
        all_files: list[str] = []
        for pattern in source_paths:
            full_pattern = str(root / pattern)
            matched = sorted(glob(full_pattern, recursive=True))
            all_files.extend(f for f in matched if Path(f).is_file())
        all_files = sorted(set(all_files))

        stats = {
            "files_scanned": len(all_files), "files_new": 0, "files_changed": 0,
            "files_unchanged": 0, "files_deleted": 0, "chunks_created": 0, "chunks_removed": 0,
        }
        current_files = set()

        for fpath in all_files:
            rel_path = str(Path(fpath).relative_to(root)) if project_root else fpath
            current_files.add(rel_path)
            file_hash = self._file_hash(fpath)
            prev_hash = self.manifest["files"].get(rel_path, {}).get("hash")

            if prev_hash == file_hash:
                stats["files_unchanged"] += 1
                continue
            if prev_hash is None:
                stats["files_new"] += 1
            else:
                stats["files_changed"] += 1

            self.store.delete_by_source(rel_path)
            chunks = chunk_file(fpath, source_label=rel_path, namespace=self.namespace)
            if not chunks:
                continue
            texts = [c.text for c in chunks]
            embeddings = self.embedder.embed_batch(texts)
            for chunk, emb in zip(chunks, embeddings):
                self.store.insert_chunk(chunk, emb)
                stats["chunks_created"] += 1

            entry = {"hash": file_hash, "chunks": len(chunks), "last_ingest": time.strftime("%Y-%m-%dT%H:%M:%S")}
            if Path(fpath).suffix.lower() == ".md":
                try:
                    entry["size"] = fpath.stat().st_size
                    entry["lines"] = sum(1 for _ in fpath.open("r", encoding="utf-8", errors="ignore"))
                except Exception:
                    pass
            self.manifest["files"][rel_path] = entry

        manifest_files = set(self.manifest["files"].keys())
        deleted = manifest_files - current_files
        for rel_path in deleted:
            self.store.delete_by_source(rel_path)
            del self.manifest["files"][rel_path]
            stats["files_deleted"] += 1

        self.store.commit()
        self.manifest["last_ingest"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_manifest()
        return stats

    def ingest_files(self, file_paths: list[str], project_root: str = "") -> dict:
        root = Path(project_root) if project_root else Path(".")
        stats = {
            "files_scanned": len(file_paths), "files_new": 0, "files_changed": 0,
            "files_unchanged": 0, "files_deleted": 0, "chunks_created": 0,
            "chunks_removed": 0, "targeted": True,
        }

        for fpath in file_paths:
            abs_path = Path(fpath)
            if not abs_path.is_absolute():
                abs_path = root / fpath
            if not abs_path.exists():
                rel_path = str(Path(fpath).relative_to(root)) if project_root and Path(fpath).is_absolute() else fpath
                if rel_path in self.manifest["files"]:
                    self.store.delete_by_source(rel_path)
                    del self.manifest["files"][rel_path]
                    stats["files_deleted"] += 1
                continue

            rel_path = str(abs_path.relative_to(root)) if project_root else fpath
            file_hash = self._file_hash(str(abs_path))
            prev_hash = self.manifest["files"].get(rel_path, {}).get("hash")

            if prev_hash == file_hash:
                stats["files_unchanged"] += 1
                continue
            if prev_hash is None:
                stats["files_new"] += 1
            else:
                stats["files_changed"] += 1

            self.store.delete_by_source(rel_path)
            chunks = chunk_file(str(abs_path), source_label=rel_path, namespace=self.namespace)
            if not chunks:
                continue
            texts = [c.text for c in chunks]
            embeddings = self.embedder.embed_batch(texts)
            for chunk, emb in zip(chunks, embeddings):
                self.store.insert_chunk(chunk, emb)
                stats["chunks_created"] += 1

            entry = {"hash": file_hash, "chunks": len(chunks), "last_ingest": time.strftime("%Y-%m-%dT%H:%M:%S")}
            if abs_path.suffix.lower() == ".md":
                try:
                    entry["size"] = abs_path.stat().st_size
                    entry["lines"] = sum(1 for _ in abs_path.open("r", encoding="utf-8", errors="ignore"))
                except Exception:
                    pass
            self.manifest["files"][rel_path] = entry

        self.store.commit()
        self.manifest["last_ingest"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_manifest()
        return stats

    _RUNTIME_FILES = (
        "cps_server.py", "cps_chunker.py", "cps_embedder.py",
        "cps_graph.py", "cps_test_suite.py",
    )

    def sync_runtime_to_cps(self, project_root: str) -> dict:
        result = {"ran": False, "files_checked": 0, "files_promoted": [], "files_unchanged": 0}
        if not project_root:
            return result
        root = Path(project_root)
        runtime_dir = root / "Runtime"
        deployed_dir = root / ".cps"
        if not runtime_dir.is_dir() or not deployed_dir.is_dir():
            return result
        result["ran"] = True
        for fname in self._RUNTIME_FILES:
            src = runtime_dir / fname
            dst = deployed_dir / fname
            if not src.is_file() or not dst.is_file():
                continue
            result["files_checked"] += 1
            src_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            dst_hash = hashlib.sha256(dst.read_bytes()).hexdigest()
            if src_hash == dst_hash:
                result["files_unchanged"] += 1
                continue
            try:
                dst.write_bytes(src.read_bytes())
                result["files_promoted"].append(fname)
                logger.info(f"sync_runtime_to_cps: promoted {fname} (src={src_hash[:8]} dst={dst_hash[:8]})")
            except OSError as e:
                logger.warning(f"sync_runtime_to_cps: failed to promote {fname}: {e}")
        return result

    def purge_stale(self, project_root: str = "", max_age_days: Optional[int] = None) -> dict:
        root = Path(project_root) if project_root else Path(".")
        stats = {
            "purged_missing": 0, "purged_stale": 0, "chunks_removed": 0,
            "manifest_entries_before": len(self.manifest["files"]),
        }
        to_remove: list[str] = []
        for rel_path, entry in self.manifest["files"].items():
            abs_path = root / rel_path
            if not abs_path.exists():
                to_remove.append(rel_path)
                stats["purged_missing"] += 1
                continue
            if max_age_days is not None and "last_ingest" in entry:
                try:
                    ingest_time = time.strptime(entry["last_ingest"][:19], "%Y-%m-%dT%H:%M:%S")
                    age_days = (time.time() - time.mktime(ingest_time)) / 86400
                    if age_days > max_age_days:
                        to_remove.append(rel_path)
                        stats["purged_stale"] += 1
                except (ValueError, KeyError):
                    pass
        for rel_path in to_remove:
            chunk_count = self.manifest["files"].get(rel_path, {}).get("chunks", 0)
            self.store.delete_by_source(rel_path)
            del self.manifest["files"][rel_path]
            stats["chunks_removed"] += chunk_count
        if to_remove:
            self.store.commit()
            self.manifest["last_ingest"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._save_manifest()
        stats["manifest_entries_after"] = len(self.manifest["files"])
        return stats


class CPSServer:
    def __init__(self, config: dict):
        self.config = config
        cps_dir = Path(config.get("cps_dir", ".cps"))
        project_root = config.get("project_root", "")
        self.namespace = config.get("namespace", "") or (Path(project_root).name if project_root else "")
        self.cps_dir = cps_dir
        self.project_root = project_root
        self.embedder = Embedder()
        self.store = VectorStore(str(cps_dir / "cps.db"))
        self.pipeline = IngestPipeline(
            self.store, self.embedder, str(cps_dir / "cps_manifest.json"), namespace=""
        )
        self.cache = SearchCache(self.store.conn)
        self.graph = KnowledgeGraph(self.store.conn)
        self.tools = {
            "cps_search": self._tool_search,
            "cps_retrieve": self._tool_retrieve,
            "cps_status": self._tool_status,
            "cps_ingest": self._tool_ingest,
            "cps_graph_build": self._tool_graph_build,
            "cps_graph_query": self._tool_graph_query,
            "cps_prime": self._tool_prime,
            "cps_purge": self._tool_purge,
        }

    def _tool_search(self, args: dict) -> Any:
        query = args.get("query", "")
        limit = int(args.get("limit", 5))
        source_filter = args.get("source_filter")
        skip_cache = args.get("skip_cache", False)
        if not query:
            return {"error": "query is required"}
        query_vec = self.embedder.embed_text(query)
        cached = None
        if not skip_cache and not source_filter:
            cached = self.cache.lookup(query_vec, query_text=query)
        if cached is not None:
            return {"results": cached[:limit], "query": query, "count": min(len(cached), limit), "cache_hit": True}
        results = self.store.search(query_vec, limit=limit, source_filter=source_filter)
        if not source_filter and results:
            total_tokens = sum(r.get("estimated_tokens", 0) for r in results)
            self.cache.store(query, query_vec, results, estimated_tokens=total_tokens)
        return {"results": results, "query": query, "count": len(results), "cache_hit": False}

    def _tool_retrieve(self, args: dict) -> Any:
        chunk_id = args.get("chunk_id", "")
        if not chunk_id:
            return {"error": "chunk_id is required"}
        result = self.store.retrieve(chunk_id)
        if result is None:
            return {"error": f"Chunk {chunk_id} not found"}
        return result

    def _compute_needs_refresh(self) -> dict:
        manifest = self.pipeline.manifest
        manifest_files = manifest.get("files", {})
        root = Path(self.config.get("project_root", "."))
        new_files = []
        large_md_updates = []
        source_paths = self.config.get("source_paths", [])
        for pattern in source_paths:
            full_pattern = str(root / pattern)
            try:
                for fp in glob(full_pattern, recursive=True):
                    if not Path(fp).is_file():
                        continue
                    try:
                        rel = str(Path(fp).relative_to(root))
                    except ValueError:
                        continue
                    if rel not in manifest_files:
                        new_files.append(rel)
                        continue
                    if Path(fp).suffix.lower() != ".md":
                        continue
                    try:
                        current_size = Path(fp).stat().st_size
                        current_lines = sum(1 for _ in Path(fp).open("r", encoding="utf-8", errors="ignore"))
                    except Exception:
                        continue
                    rec = manifest_files[rel]
                    old_size = rec.get("size", 0)
                    old_lines = rec.get("lines", 0)
                    if old_size == 0 or old_lines == 0:
                        continue
                    size_delta_pct = abs(current_size - old_size) / max(old_size, 1)
                    line_delta = abs(current_lines - old_lines)
                    if size_delta_pct >= 0.20 or line_delta >= 500:
                        large_md_updates.append({"path": rel, "size_delta_pct": round(size_delta_pct, 3), "line_delta": line_delta})
            except Exception:
                continue
        if new_files:
            return {"needs_refresh": True, "reason": "new_files", "details": {"new_files": new_files, "count": len(new_files)}}
        if large_md_updates:
            return {"needs_refresh": True, "reason": "large_md_updates", "details": {"updates": large_md_updates, "count": len(large_md_updates)}}
        return {"needs_refresh": False, "reason": None, "details": {}}

    def _tool_status(self, args: dict) -> Any:
        detail = args.get("detail", "summary")
        db_stats = self.store.stats()
        manifest = self.pipeline.manifest
        result = {**db_stats, "last_ingest": manifest.get("last_ingest"), "db_path": str(Path(self.config.get("cps_dir", ".cps")) / "cps.db")}
        result["cache"] = self.cache.stats()
        try:
            result["graph"] = self.graph.stats()
        except Exception:
            result["graph"] = {"status": "not built yet"}
        stale_files = []
        root = Path(self.config.get("project_root", "."))
        for rel_path, info in manifest.get("files", {}).items():
            abs_path = root / rel_path
            if abs_path.exists():
                current_hash = hashlib.sha256(abs_path.read_bytes()).hexdigest()
                if current_hash != info.get("hash"):
                    stale_files.append(rel_path)
        result["stale_files"] = stale_files
        result["stale_count"] = len(stale_files)
        total_configured = 0
        for pattern in self.config.get("source_paths", []):
            full_pattern = str(root / pattern)
            total_configured += len(glob(full_pattern, recursive=True))
        indexed_count = len(manifest.get("files", {}))
        result["coverage_pct"] = round((indexed_count / total_configured * 100) if total_configured > 0 else 0, 1)
        recs = []
        if stale_files:
            recs.append(f"{len(stale_files)} file(s) need re-indexing. Run cps_ingest.")
        graph_stats = result.get("graph", {})
        if isinstance(graph_stats, dict) and graph_stats.get("orphaned_nodes", 0) > 0:
            recs.append(f"Graph has {graph_stats['orphaned_nodes']} orphaned node(s).")
        if result["cache"]["cache_entries"] > 500:
            recs.append("Cache is large (>500 entries). Consider clearing stale entries.")
        result["recommendations"] = recs
        if detail == "full":
            result["indexed_files"] = list(manifest.get("files", {}).keys())
        result["needs_refresh"] = self._compute_needs_refresh()
        return result

    def _tool_ingest(self, args: dict) -> Any:
        files = args.get("files")
        source_paths = args.get("source_paths", self.config.get("source_paths", []))
        project_root = args.get("project_root", self.config.get("project_root", ""))
        runtime_sync = self.pipeline.sync_runtime_to_cps(project_root)
        if files:
            stats = self.pipeline.ingest_files(files, project_root)
        elif source_paths:
            stats = self.pipeline.ingest(source_paths, project_root)
        else:
            return {"error": "No source_paths configured and no files specified."}
        if runtime_sync.get("ran"):
            stats["runtime_sync"] = runtime_sync
        if stats.get("files_changed", 0) > 0 or stats.get("files_deleted", 0) > 0 or stats.get("files_new", 0) > 0:
            self.cache.clear()
            stats["cache_cleared"] = True
        else:
            stats["cache_cleared"] = False
        return stats

    def _tool_purge(self, args: dict) -> Any:
        project_root = args.get("project_root", self.config.get("project_root", ""))
        max_age_days = args.get("max_age_days")
        if max_age_days is not None:
            try:
                max_age_days = int(max_age_days)
            except (ValueError, TypeError):
                return {"error": "max_age_days must be an integer"}
        stats = self.pipeline.purge_stale(project_root, max_age_days)
        if stats.get("chunks_removed", 0) > 0:
            self.cache.clear()
            stats["cache_cleared"] = True
        else:
            stats["cache_cleared"] = False
        return stats

    def _tool_graph_build(self, args: dict) -> Any:
        project_root = args.get("project_root", self.config.get("project_root", ""))
        stats = self.graph.build(self.store.conn, project_root=project_root)
        return stats

    def _tool_graph_query(self, args: dict) -> Any:
        action = args.get("action", "node")
        node_id = args.get("node_id", "")
        if action == "node":
            if not node_id:
                return {"error": "node_id is required for node queries"}
            result = self.graph.query_node(node_id)
            if result is None:
                return {"error": f"Node {node_id} not found"}
            return result
        elif action == "neighbors":
            if not node_id:
                return {"error": "node_id is required for neighbor queries"}
            depth = args.get("depth", 1)
            return self.graph.query_neighbors(node_id, depth=min(depth, 3))
        elif action == "orphans":
            return {"orphans": self.graph.find_orphans()}
        elif action == "clusters":
            min_size = args.get("min_size", 3)
            clusters = self.graph.find_clusters(min_size=min_size)
            return {"cluster_count": len(clusters), "clusters": [{"size": len(c), "nodes": c[:10]} for c in sorted(clusters, key=len, reverse=True)[:20]]}
        elif action == "stats":
            return self.graph.stats()
        else:
            return {"error": f"Unknown action: {action}. Use: node, neighbors, orphans, clusters, stats"}

    def _tool_prime(self, args: dict) -> Any:
        task_description = args.get("task_description", "")
        task_id = args.get("task_id", "")
        include_graph = args.get("include_graph", True)
        limit = int(args.get("limit", 8))
        last_session_deltas = args.get("last_session_deltas", "")
        if not task_description:
            return {"error": "task_description is required"}
        query_text = task_description
        if last_session_deltas:
            query_text = f"{task_description}\n\nRecent changes: {last_session_deltas[:300]}"
        query_vec = self.embedder.embed_text(query_text)
        results = self.store.search(query_vec, limit=limit)
        results = [r for r in results if r.get("score", 0) >= 0.3]
        graph_chunks = []
        if include_graph and results:
            try:
                matched_files = {r["source_file"] for r in results}
                neighbor_files = set()
                for source_file in matched_files:
                    node_data = self.graph.query_node(f"file:{source_file}")
                    if node_data:
                        for edge in node_data.get("outgoing", []):
                            if edge["to"].startswith("file:"):
                                neighbor_files.add(edge["to"].replace("file:", ""))
                        for edge in node_data.get("incoming", []):
                            if edge["from"].startswith("file:"):
                                neighbor_files.add(edge["from"].replace("file:", ""))
                neighbor_files -= matched_files
                for nf in list(neighbor_files)[:3]:
                    for nr in self.store.search(query_vec, limit=1, source_filter=nf):
                        if nr.get("score", 0) >= 0.3:
                            nr["graph_adjacent"] = True
                            graph_chunks.append(nr)
            except Exception as e:
                logger.warning(f"Graph enrichment failed (non-fatal): {e}")
        all_results = results + graph_chunks
        total_tokens = sum(r.get("estimated_tokens", 0) for r in all_results)
        return {
            "task_id": task_id, "task_description": task_description,
            "delta_injected": bool(last_session_deltas),
            "results": all_results, "count": len(all_results),
            "direct_hits": len(results), "graph_adjacent_hits": len(graph_chunks),
            "total_tokens": total_tokens, "primed": len(all_results) > 0,
        }

    def _tool_definitions(self) -> list[dict]:
        return [
            {"name": "cps_search", "description": "Semantic search over indexed project documents.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}, "source_filter": {"type": "string"}, "skip_cache": {"type": "boolean", "default": False}}, "required": ["query"]}},
            {"name": "cps_retrieve", "description": "Retrieve a chunk by ID.", "inputSchema": {"type": "object", "properties": {"chunk_id": {"type": "string"}}, "required": ["chunk_id"]}},
            {"name": "cps_status", "description": "CPS health report.", "inputSchema": {"type": "object", "properties": {"detail": {"type": "string", "enum": ["summary", "full"], "default": "summary"}}}},
            {"name": "cps_ingest", "description": "Index or re-index project documents.", "inputSchema": {"type": "object", "properties": {"source_paths": {"type": "array", "items": {"type": "string"}}, "files": {"type": "array", "items": {"type": "string"}}, "project_root": {"type": "string"}}}},
            {"name": "cps_graph_build", "description": "Build knowledge graph.", "inputSchema": {"type": "object", "properties": {"project_root": {"type": "string"}}}},
            {"name": "cps_graph_query", "description": "Query knowledge graph.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["node", "neighbors", "orphans", "clusters", "stats"]}, "node_id": {"type": "string"}, "depth": {"type": "integer", "default": 1}, "min_size": {"type": "integer", "default": 3}}}},
            {"name": "cps_prime", "description": "Task-aware context priming.", "inputSchema": {"type": "object", "properties": {"task_description": {"type": "string"}, "task_id": {"type": "string"}, "include_graph": {"type": "boolean", "default": True}, "limit": {"type": "integer", "default": 8}, "last_session_deltas": {"type": "string"}}, "required": ["task_description"]}},
            {"name": "cps_purge", "description": "Purge stale chunks.", "inputSchema": {"type": "object", "properties": {"project_root": {"type": "string"}, "max_age_days": {"type": "integer"}}}},
        ]

    def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "cps", "version": "0.1.0"}}}
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self._tool_definitions()}}
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            handler = self.tools.get(tool_name)
            if handler is None:
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}}
            try:
                result = handler(tool_args)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
            except Exception as e:
                logger.exception(f"Error in tool {tool_name}")
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}}
        else:
            if req_id is not None:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
            return None

    def run(self):
        logger.info("CPS MCP Server starting...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON: {line[:100]}")
                continue
            response = self.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def run_direct(config_path: Optional[str] = None, command: str = "status", **kwargs):
    config = _load_config(config_path)
    server = CPSServer(config)
    handler = server.tools.get(f"cps_{command}")
    if handler is None:
        available = [k.replace("cps_", "") for k in server.tools]
        print(json.dumps({"error": f"Unknown command: {command}", "available": available}))
        sys.exit(1)
    try:
        result = handler(kwargs)
    except Exception as exc:
        logger.exception("Handler %s raised an unhandled exception", command)
        print(json.dumps({"error": str(exc), "command": command}))
        sys.exit(1)
    print(json.dumps(result, indent=2))


def _load_config(config_path: Optional[str] = None) -> dict:
    path = config_path or os.environ.get("CPS_CONFIG_PATH", ".cps/cps_config.json")
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {}


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--serve":
        config = _load_config()
        server = CPSServer(config)
        server.run()
    elif args:
        command = args[0]
        kwargs = {}
        config_path = None
        for arg in args[1:]:
            if arg.startswith("--config="):
                config_path = arg.split("=", 1)[1]
            elif arg.startswith("--"):
                k, _, v = arg[2:].partition("=")
                if "," in v:
                    kwargs[k] = v.split(",")
                else:
                    kwargs[k] = v
        run_direct(config_path, command, **kwargs)
    else:
        print("Usage:")
        print("  python cps_server.py --serve              # Run as MCP server")
        print("  python cps_server.py ingest --source_paths=docs/**/*.md --project_root=/path")
        print("  python cps_server.py search --query='schema fields'")
        print("  python cps_server.py status")
        print("  python cps_server.py retrieve --chunk_id=abc123")
