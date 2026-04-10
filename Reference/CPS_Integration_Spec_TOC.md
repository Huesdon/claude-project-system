# TOC — D3_CPS_Integration_Spec.md

| Line | Section |
|------|---------|
| 10 | 1. Purpose |
| 16 | 2. Design Principles |
| 28 | 3. Prerequisites |
| 32 | Detection Check (runs once per session) |
| 49 | 4. Integration by Tier |
| 51 | 4.1 Tier 1 — Augment (don't replace) |
| 69 | 4.2 Tier 2 — CPS-First, File-Fallback |
| 99 | 4.3 Tier 3 — No Change |
| 105 | 5. Token Savings Model |
| 107 | Baseline: Standard EM Startup (no CPS) |
| 117 | CPS-Enhanced EM Startup |
| 133 | Measurement |
| 144 | 6. EM CLAUDE.md Changes |
| 146 | 6.1 New Section: CPS Integration |
| 150 | 6.2 Startup Scan Modifications |
| 160 | 6.3 Haiku Gateway Addition |
| 168 | 7. Generalization Path (Post-EM Proving Ground) |
| 182 | 8. Config Requirements |
| 211 | 9. Phase 5.1 Enhancements (Implemented 2026-04-07) |
| 215 | 9.1 JSON Array Chunking (resolves OQ#1) |
| 224 | 9.2 Stale Chunk Purge (resolves OQ#2) |
| 233 | 9.3 Prime Query Personalization (resolves OQ#3) |
| 244 | 10. Remaining Open Questions |
| 248 | 11. Phase 7 — Open Question Resolutions (Designed 2026-04-07) |
| 252 | 11.1 Multi-Engagement Cache Isolation (resolves OQ#1) |
| 265 | 11.2 Persona Allowlist Dynamic Loading (resolves OQ#2) |
| 286 | 11.3 JSON Chunker Structural Repair (resolves OQ#3) |
