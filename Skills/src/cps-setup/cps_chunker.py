import json as json_module
import re
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional


# Rough token estimate: ~1.3 tokens per word for English prose
TOKENS_PER_WORD = 1.3
MIN_TOKENS = 50
MAX_TOKENS = 2000
MIN_WORDS = int(MIN_TOKENS / TOKENS_PER_WORD)   # ~38
MAX_WORDS = int(MAX_TOKENS / TOKENS_PER_WORD)    # ~1538


@dataclass
class Chunk:
    chunk_id: str
    source_file: str
    heading_path: str          # e.g. "Schema Definitions > flags.json > Fields"
    text: str
    line_start: int
    line_end: int
    word_count: int
    estimated_tokens: int
    frontmatter: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)