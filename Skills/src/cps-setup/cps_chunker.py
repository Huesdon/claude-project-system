"""
CPS Document Chunker
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


def _generate_chunk_id(source_file: str, heading_path: str, line_start: int, namespace: str = "") -> str:
    """Deterministic chunk ID from source + heading + position.

    If namespace is provided, prefixes the hash: "{namespace}:{hash}".
    This prevents chunk ID collisions when multiple projects share a cross-project
    query layer or are registered in the same ProjectRegistry.
    """
    raw = f"{source_file}::{heading_path}::{line_start}"
    hash_val = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{namespace}:{hash_val}" if namespace else hash_val


def _word_count(text: str) -> int:
    return len(text.split())


def _estimate_tokens(text: str) -> int:
    return int(_word_count(text) * TOKENS_PER_WORD)


def _extract_frontmatter(lines: list[str]) -> tuple[Optional[dict], int]:
    """Extract YAML-like frontmatter from --- delimited blocks.
    Returns (metadata_dict, first_content_line_index).
    """
    if not lines or lines[0].strip() != '---':
        return None, 0

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return None, 0

    fm = {}
    for line in lines[1:end_idx]:
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip()

    return fm, end_idx + 1


def _split_at_paragraphs(text: str, max_words: int) -> list[str]:
    """Split oversized text at paragraph boundaries (double newlines)."""
    paragraphs = re.split(r'\n\n+', text)
    parts = []
    current = []
    current_wc = 0

    for para in paragraphs:
        wc = _word_count(para)
        if current_wc + wc > max_words and current:
            parts.append('\n\n'.join(current))
            current = [para]
            current_wc = wc
        else:
            current.append(para)
            current_wc += wc

    if current:
        parts.append('\n\n'.join(current))

    return parts


def _heading_level(line: str) -> Optional[int]:
    """Return heading level (2 or 3) if line is a ## or ### heading, else None."""
    match = re.match(r'^(#{2,3})\s+', line)
    if match:
        return len(match.group(1))
    return None


def _heading_text(line: str) -> str:
    """Strip markdown heading markers."""
    return re.sub(r'^#{1,6}\s+', '', line).strip()


def chunk_markdown(file_path: str, source_label: Optional[str] = None, namespace: str = "") -> list[Chunk]:
    """
    Chunk a markdown file by heading structure.

    Args:
        file_path: Path to the markdown file
        source_label: Optional label for the source file (defaults to relative path)

    Returns:
        List of Chunk objects
    """
    path = Path(file_path)
    if not path.exists():
        return []

    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    source = source_label or str(path)

    # Extract frontmatter
    frontmatter, content_start = _extract_frontmatter(lines)

    # Parse heading structure into raw sections
    sections: list[dict] = []
    heading_stack: list[str] = []  # tracks current heading path
    current_section = {
        'heading_path': path.stem,   # file name as root if no heading yet
        'heading_level': 1,
        'line_start': content_start + 1,  # 1-indexed
        'lines': [],
    }

    for i in range(content_start, len(lines)):
        line = lines[i]
        level = _heading_level(line)

        if level is not None:
            # Save current section if it has content
            if current_section['lines']:
                sections.append(current_section)

            # Update heading stack
            h_text = _heading_text(line)
            # Pop stack back to parent level
            while heading_stack and len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(h_text)

            current_section = {
                'heading_path': ' > '.join(heading_stack),
                'heading_level': level,
                'line_start': i + 1,  # 1-indexed
                'lines': [line],
            }
        else:
            current_section['lines'].append(line)

    # Don't forget the last section
    if current_section['lines']:
        sections.append(current_section)

    # Convert sections to chunks, handling min/max size constraints
    raw_chunks: list[Chunk] = []
    for sec in sections:
        text_block = '\n'.join(sec['lines']).strip()
        if not text_block:
            continue

        wc = _word_count(text_block)
        line_end = sec['line_start'] + len(sec['lines']) - 1

        if wc > MAX_WORDS:
            # Split oversized chunks at paragraph boundaries
            parts = _split_at_paragraphs(text_block, MAX_WORDS)
            offset = 0
            for idx, part in enumerate(parts):
                part_lines = part.count('\n') + 1
                chunk = Chunk(
                    chunk_id=_generate_chunk_id(source, sec['heading_path'], sec['line_start'] + offset, namespace=namespace),
                    source_file=source,
                    heading_path=sec['heading_path'] + (f' (part {idx+1})' if len(parts) > 1 else ''),
                    text=part,
                    line_start=sec['line_start'] + offset,
                    line_end=sec['line_start'] + offset + part_lines - 1,
                    word_count=_word_count(part),
                    estimated_tokens=_estimate_tokens(part),
                    frontmatter=frontmatter if idx == 0 else None,
                )
                raw_chunks.append(chunk)
                offset += part_lines
        else:
            chunk = Chunk(
                chunk_id=_generate_chunk_id(source, sec['heading_path'], sec['line_start'], namespace=namespace),
                source_file=source,
                heading_path=sec['heading_path'],
                text=text_block,
                line_start=sec['line_start'],
                line_end=line_end,
                word_count=wc,
                estimated_tokens=_estimate_tokens(text_block),
                frontmatter=frontmatter if not raw_chunks else None,
            )
            raw_chunks.append(chunk)

    # Merge undersized chunks with their successor
    merged: list[Chunk] = []
    i = 0
    while i < len(raw_chunks):
        current = raw_chunks[i]
        if current.word_count < MIN_WORDS and i + 1 < len(raw_chunks):
            nxt = raw_chunks[i + 1]
            combined_text = current.text + '\n\n' + nxt.text
            merged_chunk = Chunk(
                chunk_id=_generate_chunk_id(source, current.heading_path, current.line_start, namespace=namespace),
                source_file=source,
                heading_path=current.heading_path,
                text=combined_text,
                line_start=current.line_start,
                line_end=nxt.line_end,
                word_count=_word_count(combined_text),
                estimated_tokens=_estimate_tokens(combined_text),
                frontmatter=current.frontmatter or nxt.frontmatter,
            )
            merged.append(merged_chunk)
            i += 2
        else:
            merged.append(current)
            i += 1

    return merged


def chunk_json(file_path: str, source_label: Optional[str] = None, namespace: str = "") -> list[Chunk]:
    """
    Chunk a JSON file by structure.

    Strategy:
    - Top-level arrays: one chunk per array entry (keyed by index)
    - Top-level objects: one chunk per top-level key
    - Meta fields (keys matching "meta" or "_meta") are extracted as frontmatter,
      not chunked separately
    - Oversized entries are split at the same paragraph-boundary logic as markdown
    - Undersized entries are merged with their successor

    Args:
        file_path: Path to the JSON file
        source_label: Optional label for the source file (defaults to relative path)

    Returns:
        List of Chunk objects
    """
    path = Path(file_path)
    if not path.exists():
        return []

    raw_text = path.read_text(encoding='utf-8')
    try:
        data = json_module.loads(raw_text)
    except json_module.JSONDecodeError:
        # Not valid JSON - fall back to markdown chunker
        return chunk_markdown(file_path, source_label)

    source = source_label or str(path)
    raw_lines = raw_text.splitlines()

    # Determine structure type and extract entries
    entries: list[tuple[str, str]] = []  # (heading_path, serialized_text)
    frontmatter: Optional[dict] = None

    if isinstance(data, list):
        # Top-level array: one chunk per entry
        for idx, item in enumerate(data):
            label = _json_entry_label(item, idx)
            heading = f"{path.stem}[{idx}] {label}"
            text = json_module.dumps(item, indent=2, default=str)
            entries.append((heading, text))

    elif isinstance(data, dict):
        # Extract meta fields as frontmatter
        meta_keys = [k for k in data if k.lower() in ('meta', '_meta', 'metadata')]
        if meta_keys:
            frontmatter = {}
            for mk in meta_keys:
                if isinstance(data[mk], dict):
                    frontmatter.update(data[mk])
                else:
                    frontmatter[mk] = data[mk]

        # One chunk per non-meta top-level key
        for key in data:
            if key.lower() in ('meta', '_meta', 'metadata'):
                continue
            value = data[key]
            heading = f"{path.stem} > {key}"

            if isinstance(value, list):
                # Array value: sub-chunk per entry
                for idx, item in enumerate(value):
                    label = _json_entry_label(item, idx)
                    sub_heading = f"{heading}[{idx}] {label}"
                    text = json_module.dumps(item, indent=2, default=str)
                    entries.append((sub_heading, text))
            else:
                text = json_module.dumps(value, indent=2, default=str)
                entries.append((heading, text))
    else:
        # Scalar top-level (rare) - single chunk
        entries.append((path.stem, json_module.dumps(data, indent=2, default=str)))

    # Convert entries to Chunk objects with size constraints
    raw_chunks: list[Chunk] = []
    for heading_path, text in entries:
        wc = _word_count(text)
        et = _estimate_tokens(text)

        if wc > MAX_WORDS:
            # Split oversized JSON entries at line boundaries
            # Phase 7c: parts are (text, truncated) tuples with bracket repair
            parts = _split_json_text(text, MAX_WORDS)
            for idx, (part_text, truncated) in enumerate(parts):
                suffix = f' (part {idx+1})' if len(parts) > 1 else ''
                if truncated:
                    suffix += ' [truncated]'
                chunk = Chunk(
                    chunk_id=_generate_chunk_id(source, heading_path, idx, namespace=namespace),
                    source_file=source,
                    heading_path=heading_path + suffix,
                    text=part_text,
                    line_start=0,   # JSON chunks don't map cleanly to source lines
                    line_end=0,
                    word_count=_word_count(part_text),
                    estimated_tokens=_estimate_tokens(part_text),
                    frontmatter=frontmatter if not raw_chunks and idx == 0 else None,
                )
                raw_chunks.append(chunk)
        else:
            chunk = Chunk(
                chunk_id=_generate_chunk_id(source, heading_path, len(raw_chunks), namespace=namespace),
                source_file=source,
                heading_path=heading_path,
                text=text,
                line_start=0,
                line_end=0,
                word_count=wc,
                estimated_tokens=et,
                frontmatter=frontmatter if not raw_chunks else None,
            )
            raw_chunks.append(chunk)

    # Merge undersized chunks with successor (same logic as markdown)
    merged: list[Chunk] = []
    i = 0
    while i < len(raw_chunks):
        current = raw_chunks[i]
        if current.word_count < MIN_WORDS and i + 1 < len(raw_chunks):
            nxt = raw_chunks[i + 1]
            combined_text = current.text + '\n\n' + nxt.text
            merged_chunk = Chunk(
                chunk_id=_generate_chunk_id(source, current.heading_path, i, namespace=namespace),
                source_file=source,
                heading_path=current.heading_path,
                text=combined_text,
                line_start=0,
                line_end=0,
                word_count=_word_count(combined_text),
                estimated_tokens=_estimate_tokens(combined_text),
                frontmatter=current.frontmatter or nxt.frontmatter,
            )
            merged.append(merged_chunk)
            i += 2
        else:
            merged.append(current)
            i += 1

    return merged


def _json_entry_label(item: Any, index: int) -> str:
    """Generate a human-readable label for a JSON array entry.
    Tries common identifier fields before falling back to index."""
    if isinstance(item, dict):
        for key in ('title', 'name', 'id', 'label', 'key', 'slug'):
            if key in item and isinstance(item[key], str):
                return item[key][:60]
    return f"entry_{index}"


def _balance_json_brackets(text: str) -> tuple[str, bool]:
    """
    Phase 7c: Check if a JSON text fragment has balanced braces/brackets.
    If unbalanced, append closing tokens to make it parseable and prepend
    a truncation comment. Returns (repaired_text, was_truncated).

    This prevents downstream confusion when split chunks are returned to
    personas for context. Embedding quality is not affected either way -
    this is purely for readability of returned chunks.
    """
    opens = 0
    open_brackets = 0
    for ch in text:
        if ch == '{':
            opens += 1
        elif ch == '}':
            opens -= 1
        elif ch == '[':
            open_brackets += 1
        elif ch == ']':
            open_brackets -= 1

    if opens == 0 and open_brackets == 0:
        return text, False

    # Append closing tokens to balance
    closers = ']' * max(open_brackets, 0) + '}' * max(opens, 0)
    repaired = f"// [truncated from parent structure]\n{text}\n{closers}"
    return repaired, True


def _split_json_text(text: str, max_words: int) -> list[tuple[str, bool]]:
    """Split oversized JSON text at line boundaries.
    Phase 7c: Returns list of (text, truncated) tuples.
    Each part is bracket-balanced for readability when returned to personas."""
    lines = text.splitlines()
    raw_parts: list[str] = []
    current_lines: list[str] = []
    current_wc = 0

    for line in lines:
        wc = _word_count(line)
        if current_wc + wc > max_words and current_lines:
            raw_parts.append('\n'.join(current_lines))
            current_lines = [line]
            current_wc = wc
        else:
            current_lines.append(line)
            current_wc += wc

    if current_lines:
        raw_parts.append('\n'.join(current_lines))

    # Phase 7c: repair bracket balance on each part
    return [_balance_json_brackets(part) for part in raw_parts]


def chunk_file(file_path: str, source_label: Optional[str] = None, namespace: str = "") -> list[Chunk]:
    """
    Universal dispatcher: routes to chunk_markdown or chunk_json based on extension.
    This is the primary entry point for the ingest pipeline.

    namespace: project namespace prefix for chunk IDs (prevents cross-project collisions).
    """
    ext = Path(file_path).suffix.lower()
    if ext == '.json':
        return chunk_json(file_path, source_label, namespace=namespace)
    else:
        return chunk_markdown(file_path, source_label, namespace=namespace)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cps_chunker.py <file>")
        sys.exit(1)

    chunks = chunk_file(sys.argv[1])
    for c in chunks:
        print(f"[{c.chunk_id}] {c.heading_path} | {c.word_count}w ~{c.estimated_tokens}t")
        print(f"  {c.text[:120]}...")
        print()
