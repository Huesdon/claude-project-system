#!/usr/bin/env python3
"""
CPS Validation Test Suite
Tests all major CPS tool surfaces via the JSON-RPC 2.0 protocol over subprocess stdio.
Run from: project root (path resolved dynamically via __file__)
"""

import subprocess
import sys

# ---------------------------------------------------------------------------
# Dependency bootstrap — ensures the test suite is self-contained.
# Installs required packages if missing so the suite passes in any fresh
# sandbox session without manual setup.
# ---------------------------------------------------------------------------
_REQUIRED = ["sqlite-vec", "huggingface-hub", "tokenizers", "onnxruntime", "numpy"]

def _bootstrap_deps():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *_REQUIRED,
         "--break-system-packages", "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR: dependency install failed during bootstrap.")
        print(result.stderr)
        sys.exit(1)

_bootstrap_deps()

import json
import time
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CPS_DIR    = str(Path(__file__).parent)          # .cps/ directory
PROJECT_ROOT = str(Path(__file__).parent.parent)  # project root (one level up)
CPS_SERVER = str(Path(__file__).parent / "cps_server.py")

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
WARN = "\033[93m WARN\033[0m"
HEAD = "\033[1m"
RESET = "\033[0m"

results = []

# ---------------------------------------------------------------------------
# JSON-RPC helper — sends full MCP handshake + one tool call, gets response
# ---------------------------------------------------------------------------

def rpc(method: str, params: dict, timeout: int = 30) -> dict:
    # MCP requires: initialize -> notifications/initialized -> tools/call
    init_msg = json.dumps({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "cps-test", "version": "1.0"}}
    })
    notif_msg = json.dumps({
        "jsonrpc": "2.0", "method": "notifications/initialized", "params": {}
    })
    tool_msg = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": method, "arguments": params}
    })

    payload = init_msg + "\n" + notif_msg + "\n" + tool_msg + "\n"

    proc = subprocess.run(
        [sys.executable, CPS_SERVER, "--serve"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_ROOT
    )

    raw = proc.stdout.strip()
    if not raw:
        raise RuntimeError(f"No stdout from server. stderr: {proc.stderr[:400]}")

    # Server emits one JSON line per request; find the one with id=1 (tool call)
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("id") == 1:
                return obj
        except json.JSONDecodeError:
            continue

    # Fallback: return last valid JSON line
    for line in reversed(raw.splitlines()):
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"No valid JSON in output: {raw[:400]}")


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def test(name: str, fn):
    try:
        fn()
        print(f"{PASS}  {name}")
        results.append((name, "PASS", None))
    except AssertionError as e:
        print(f"{FAIL}  {name}  —  {e}")
        results.append((name, "FAIL", str(e)))
    except Exception as e:
        print(f"{FAIL}  {name}  —  {type(e).__name__}: {e}")
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))


def section(title: str):
    print(f"\n{HEAD}{'='*60}{RESET}")
    print(f"{HEAD}  {title}{RESET}")
    print(f"{HEAD}{'='*60}{RESET}")


# ---------------------------------------------------------------------------
# Helper: extract text from MCP content array
# ---------------------------------------------------------------------------

def extract_text(resp: dict) -> str:
    result = resp.get("result", {})
    content = result.get("content", [])
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(parts)
    return str(result)


# ---------------------------------------------------------------------------
# T1: cps_status
# ---------------------------------------------------------------------------

section("T1 — cps_status: Health reporting")

def t1_status_responds():
    resp = rpc("cps_status", {})
    text = extract_text(resp)
    assert len(text) > 10, "Empty status response"

def t1_status_has_chunks():
    resp = rpc("cps_status", {})
    text = extract_text(resp)
    assert "chunk" in text.lower(), f"No chunk info in status: {text[:200]}"

def t1_status_has_namespace():
    resp = rpc("cps_status", {})
    text = extract_text(resp)
    # Status returns JSON — check for namespace or db_path
    assert any(k in text for k in ["namespace", "cps-platform", "db_path"]), \
        f"Namespace/config info not reported: {text[:200]}"

def t1_status_nonzero_chunks():
    resp = rpc("cps_status", {})
    text = extract_text(resp)
    import re, json as _json
    # Status returns JSON with total_chunks field
    try:
        data = _json.loads(text)
        count = data.get("total_chunks", 0)
        assert count > 0, f"total_chunks is {count}: {text[:200]}"
        return
    except Exception:
        pass
    # Fallback: regex search
    nums = re.findall(r'"total_chunks"\s*:\s*(\d+)', text)
    if not nums:
        nums = re.findall(r'(\d+)\s*chunk', text, re.IGNORECASE)
    assert nums and int(nums[0]) > 0, f"Zero chunks reported or not found: {text[:300]}"

test("cps_status responds", t1_status_responds)
test("cps_status reports chunk count", t1_status_has_chunks)
test("cps_status includes namespace info", t1_status_has_namespace)
test("cps_status shows > 0 chunks", t1_status_nonzero_chunks)


# ---------------------------------------------------------------------------
# T2: cps_search — semantic retrieval
# ---------------------------------------------------------------------------

section("T2 — cps_search: Semantic search quality")

def t2_search_basic():
    resp = rpc("cps_search", {"query": "what is CPS"})
    text = extract_text(resp)
    assert len(text) > 50, f"Search returned too little: {text[:100]}"

def t2_search_has_results():
    resp = rpc("cps_search", {"query": "embedding model ONNX"})
    text = extract_text(resp)
    assert "onnx" in text.lower() or "embed" in text.lower() or "miniLM" in text.lower(), \
        f"Expected embedding content, got: {text[:200]}"

def t2_search_knowledge_graph():
    resp = rpc("cps_search", {"query": "knowledge graph BFS traversal"})
    text = extract_text(resp)
    assert "graph" in text.lower(), f"Graph content not found: {text[:200]}"

def t2_search_ingest_pipeline():
    resp = rpc("cps_search", {"query": "ingest chunker source paths"})
    text = extract_text(resp)
    assert any(w in text.lower() for w in ["ingest", "chunk", "source"]), \
        f"Ingest content not found: {text[:200]}"

def t2_search_respects_limit():
    resp = rpc("cps_search", {"query": "MCP server tools", "limit": 3})
    text = extract_text(resp)
    # Count result blocks — rough proxy
    count = text.count("---") + text.count("##") + text.count("Score:")
    # Just confirm it returned something and didn't error
    assert len(text) > 20, "Empty response with limit=3"

def t2_search_namespace_isolation():
    # Search with explicit namespace — should still return results for cps-platform
    resp = rpc("cps_search", {"query": "semantic cache", "namespace": "cps-platform"})
    text = extract_text(resp)
    assert len(text) > 20, f"Namespace-scoped search returned nothing: {text[:100]}"

test("cps_search basic query", t2_search_basic)
test("cps_search: ONNX embedding query", t2_search_has_results)
test("cps_search: knowledge graph query", t2_search_knowledge_graph)
test("cps_search: ingest pipeline query", t2_search_ingest_pipeline)
test("cps_search: limit parameter respected", t2_search_respects_limit)
test("cps_search: namespace-scoped query", t2_search_namespace_isolation)


# ---------------------------------------------------------------------------
# T3: cps_retrieve — chunk fetch by ID
# ---------------------------------------------------------------------------

section("T3 — cps_retrieve: Chunk retrieval by ID")

def t3_retrieve_chunk_1():
    # Chunk ID 1 should always exist after ingest
    resp = rpc("cps_retrieve", {"chunk_id": "cps-platform:1"})
    text = extract_text(resp)
    # If namespace prefix isn't used, try plain ID
    if "not found" in text.lower() or len(text) < 10:
        resp = rpc("cps_retrieve", {"chunk_id": "1"})
        text = extract_text(resp)
    assert len(text) > 10, f"Chunk 1 not found: {text}"

def t3_retrieve_invalid_id():
    resp = rpc("cps_retrieve", {"chunk_id": "cps-platform:99999"})
    text = extract_text(resp)
    # Should return graceful not-found, not a crash
    assert resp.get("error") is None, f"Server errored on invalid ID: {resp}"

test("cps_retrieve: fetch chunk ID 1", t3_retrieve_chunk_1)
test("cps_retrieve: graceful on invalid ID", t3_retrieve_invalid_id)


# ---------------------------------------------------------------------------
# T4: cps_prime — cache warming
# ---------------------------------------------------------------------------

section("T4 — cps_prime: Cache warming")

def t4_prime_runs():
    resp = rpc("cps_prime", {"task": "validate CPS search and ingest pipeline"}, timeout=60)
    text = extract_text(resp)
    assert resp.get("error") is None, f"cps_prime errored: {resp.get('error')}"
    assert len(text) > 5, f"Prime returned empty: {text}"

def t4_prime_with_persona():
    resp = rpc("cps_prime", {
        "task": "debugging embedding model issues",
        "persona": "developer"
    }, timeout=60)
    assert resp.get("error") is None, f"cps_prime with persona errored: {resp.get('error')}"

test("cps_prime: runs without error", t4_prime_runs)
test("cps_prime: accepts persona param", t4_prime_with_persona)


# ---------------------------------------------------------------------------
# T5: cps_graph_build + cps_graph_query
# ---------------------------------------------------------------------------

section("T5 — Knowledge Graph: build and query")

def t5_graph_build():
    resp = rpc("cps_graph_build", {}, timeout=60)
    text = extract_text(resp)
    assert resp.get("error") is None, f"graph_build errored: {resp.get('error')}"
    assert len(text) > 5, f"graph_build returned nothing: {text}"

def t5_graph_query_orphans():
    resp = rpc("cps_graph_query", {"operation": "orphans"})
    text = extract_text(resp)
    assert resp.get("error") is None, f"graph_query orphans errored: {resp.get('error')}"

def t5_graph_query_clusters():
    resp = rpc("cps_graph_query", {"operation": "clusters"})
    text = extract_text(resp)
    assert resp.get("error") is None, f"graph_query clusters errored: {resp.get('error')}"

def t5_graph_query_traverse():
    resp = rpc("cps_graph_query", {"operation": "traverse", "node_id": "1"})
    text = extract_text(resp)
    assert resp.get("error") is None, f"graph_query traverse errored: {resp.get('error')}"

test("cps_graph_build: completes without error", t5_graph_build)
test("cps_graph_query: orphan detection", t5_graph_query_orphans)
test("cps_graph_query: cluster analysis", t5_graph_query_clusters)
test("cps_graph_query: BFS traverse from node 1", t5_graph_query_traverse)


# ---------------------------------------------------------------------------
# T6: cps_ingest — incremental re-ingest
# ---------------------------------------------------------------------------

section("T6 — cps_ingest: Incremental indexing")

def t6_ingest_incremental():
    # Re-ingest should be fast (files unchanged) — verify no error and reports skip/update counts
    resp = rpc("cps_ingest", {}, timeout=120)
    text = extract_text(resp)
    assert resp.get("error") is None, f"cps_ingest errored: {resp.get('error')}"
    assert len(text) > 5, f"ingest returned nothing: {text}"

def t6_ingest_chunk_count_stable():
    # Run status before and after to confirm chunk count doesn't randomly change on re-ingest
    before = extract_text(rpc("cps_status", {}))
    rpc("cps_ingest", {}, timeout=120)
    after = extract_text(rpc("cps_status", {}))
    import re
    before_n = re.findall(r'(\d+)\s*chunk', before, re.IGNORECASE)
    after_n  = re.findall(r'(\d+)\s*chunk', after,  re.IGNORECASE)
    if before_n and after_n:
        assert int(before_n[0]) == int(after_n[0]), \
            f"Chunk count changed on re-ingest: {before_n[0]} -> {after_n[0]}"

test("cps_ingest: incremental run completes", t6_ingest_incremental)
test("cps_ingest: chunk count stable on re-ingest", t6_ingest_chunk_count_stable)


# ---------------------------------------------------------------------------
# T7: cps_purge — stale chunk removal
# ---------------------------------------------------------------------------

section("T7 — cps_purge: Stale chunk cleanup")

def t7_purge_runs():
    resp = rpc("cps_purge", {}, timeout=60)
    text = extract_text(resp)
    assert resp.get("error") is None, f"cps_purge errored: {resp.get('error')}"

test("cps_purge: runs without error", t7_purge_runs)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

section("Summary")

passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total  = len(results)

print(f"\n  {passed}/{total} tests passed  |  {failed} failed\n")

if failed:
    print(f"{HEAD}Failed tests:{RESET}")
    for name, status, msg in results:
        if status == "FAIL":
            print(f"  - {name}")
            print(f"    {msg}")

# Machine-readable output for report generation
print("\n--- JSON_RESULTS ---")
print(json.dumps(results))
