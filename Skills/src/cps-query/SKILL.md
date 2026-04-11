---
name: cps-query
description: >
  Shared skill — searches the project's CPS knowledge base and returns cited answers.
  Takes a natural-language question, calls cps_server.py via subprocess CLI (no MCP required),
  explores related content via graph traversal, and returns a cited answer with source links.
  Falls back to TOC-based reads when confidence is low. Leverages semantic cache for repeat
  queries. Triggers on: "cps query", "what do I know about", "search knowledge base",
  "cps search", "ask the knowledge base", "cps-query", "find in docs".
---

# cps-query — Search the Project Knowledge Base

## Purpose

Human-facing retrieval interface for CPS. Accepts a natural-language question, runs semantic
search against the indexed knowledge base via subprocess CLI, and returns a concise cited answer.
No MCP server or `.mcp.json` wiring required.

## Prerequisites

- CPS must be initialized: `.cps/` directory exists with `cps_server.py` and `cps.db`
- If `.cps/cps_server.py` is not found: "CPS isn't set up in this project. Run the `cps-setup`
  skill to deploy it."

## Finding the Project Root

Use Glob to find `.cps/cps_server.py` in the workspace. The parent of the `.cps/` directory is
the project root. All subprocess commands run from this directory via the Bash tool.

## Execution Flow

### Step 1: Accept the Query

The user's question is the input. It can come from:
- Direct invocation: "cps query: what fields does flags.json have?"
- Natural trigger: "what do I know about the handoff pattern?"
- Skill argument: invoked with args containing the question

If no question is provided, ask: "What do you want to search the knowledge base for?"

### Step 2: Determine Context

Check for persona context. If a persona ID (ARC, BPC, TC, EM) is available from the current
session, note it for use in Step 3.

### Step 3: Search via Subprocess

Run from the project root using the Bash tool:

```bash
python .cps/cps_server.py search --query="<user's question>" --limit=5
```

With persona (if available):
```bash
python .cps/cps_server.py search --query="<user's question>" --limit=5 --persona=<persona_id>
```

Parse the JSON output from stdout. Result shape:
```json
{
  "results": [
    {
      "chunk_id": "...",
      "source_file": "path/to/file.md",
      "heading_path": "Section > Subsection",
      "text": "chunk content",
      "score": 0.72,
      "word_count": 120,
      "cache_hit": false
    }
  ],
  "query": "...",
  "count": 5,
  "cache_hit": false
}
```

On non-zero exit code: parse `{"error": "..."}` from stdout and go to Error Handling.

### Step 4: Evaluate Confidence

Check the top result's score:

- **Score >= 0.35:** High confidence — proceed to Step 5 with all results scoring >= 0.25
- **Score 0.25–0.35:** Medium confidence — proceed to Step 5, add caveat: "These results are
  a partial match. The full source docs may have more complete information."
- **Score < 0.25:** Low confidence — fall back to Step 7

### Step 5: Graph Enrichment (Optional)

If the top result scores >= 0.35, enrich with related content:

```bash
python .cps/cps_server.py graph_query --node_id="<source_file of top result>" --depth=1
```

If the graph query returns relevant neighbors not already in the search results, surface them:

```
**Related content:**
- [neighbor_file] — referenced by/references [source_file]
```

Skip silently on error or empty response. Graph enrichment is additive — never replaces primary results.

### Step 6: Format Cited Answer

Synthesize matching chunks into a concise answer:

```
[Answer synthesized from matching chunks]

**Sources:**
- [heading_path](computer:///absolute/path/to/source_file) — [one-line relevance note]
```

Rules:
- Synthesize — don't concatenate. Write a coherent answer.
- Cite every source chunk used in the answer.
- Group multiple chunks from the same file under one citation.
- Keep the answer under 500 tokens. Summarize and point to the source for detail.
- Use `computer://` links so the user can open source files directly.
- Cache hits are transparent — don't mention them.

### Step 7: Low-Confidence Fallback

1. Tell the user: "CPS didn't find a strong match. Let me check the doc index directly."
2. Glob for `*_TOC.md` in `Documentation/md/` and `Reference/`
3. Scan headings for keyword matches against the user's question
4. If a heading match is found: read the targeted section (offset/limit) and answer from it
5. If no match: "I couldn't find information about that in the indexed docs or the doc structure.
   The topic may not be documented yet, or try rephrasing the question."

### Step 8: Log Query (Optional)

If `cps_config.json` has `"log_queries": true`, append to `.cps/cps_query_log.json`:

```json
{
  "timestamp": "<ISO 8601>",
  "query": "<user's question>",
  "top_score": 0.0,
  "result_count": 0,
  "confidence": "high|medium|low|fallback",
  "cache_hit": false,
  "persona": null
}
```

Skip silently if the config key is absent.

## Error Handling

- **`.cps/cps_server.py` not found:** "CPS isn't set up. Run the `cps-setup` skill to deploy it."
- **Non-zero exit / `{"error": "..."}` in stdout:** Report the error message. Common causes:
  database empty (run `cps-refresh`), database locked (another process is using it).
- **`graph_query` fails:** Skip enrichment silently. Primary search results are still valid.
- **Empty results list:** "The knowledge base returned no results. Try running `cps-refresh` to
  re-index your docs."