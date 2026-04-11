"""CPS Document Chunker
Splits markdown and JSON files into semantically meaningful chunks.
Markdown chunking (original):
- Each ## or ### heading starts a new chunk
- Chunk metadata: source file, heading path, line range, word count
- Frontmatter extracted as separate metadata
- Chunks under 50 tokens merged with next chunk
- Chunks over 2000 tokens split at paragraph boundaries
JSON chunking (Phase 5.1):
- Top-level arrays: one chunk per array entry
- Top-level objects: one chunk per top-level key
- Nested structures serialized as pretty-printed JSON text
- Meta fields (keys starting with "meta" or "_meta") extracted as frontmatter
- Same Chunk dataclass, same ID scheme, same size constraints
Phase 7c: Structural repair for split JSON chunks.
- Oversized nested JSON split at line boundaries gets bracket-balance repair
- Unbalanced chunks get closing tokens appended + truncation comment prepended
- heading_path tagged with [truncated] for query-layer awareness
"""
import json as json_module
import re
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional
TOKENS_PER_WORD = 1.3
MIN_TOKENS = 50
MAX_TOKENS = 2000
MIN_WORDS = int(MIN_TOKENS / TOKENS_PER_WORD)
MAX_WORDS = int(MAX_TOKENS / TOKENS_PER_WORD)