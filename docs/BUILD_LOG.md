## Session 002 — [Today's Date e.g. 21 March 2026]

**Phase:** Phase 1 — Basic Compliance RAG  
**Branch:** main  
**Duration:** [X hours today]

### Work Completed
- Created compliance_ingestor.py — full PDF parsing pipeline
- Ingested PCI-DSS v4.0.1 (360 pages) into ChromaDB
- 413 chunks created (512 word chunks, 50 word overlap)
- Embeddings: all-MiniLM-L6-v2 (local, zero API cost)
- Created Streamlit UI (ui/app.py) with sidebar corpus stats
- Added LLM answer generation using GPT-4o-mini
- Full end-to-end RAG working: query → retrieve → generate → cite

### Official Phase 1 Metrics
- Chunks ingested: 413
- Top result distance: 0.6060 (improved from 0.8385 baseline)
- Answer quality: correct regulation sections (Req 3.2, 3.2.1, 9.4)
- Page citations: correct (Pages 81, 214, 225)
- Hallucination: none detected on manual review

### Errors Encountered & Fixes
- Script ran silently — loguru not displaying in Git Bash
  Fix: used direct print() statements to debug
- ImportError on function names — file not saved in Cursor
  Fix: Ctrl+S to save, verified with grep
- OpenAI 429 error — no credits on account
  Fix: added $10 credit at platform.openai.com/billing

### Decisions Made
- Temperature 0.0 for LLM — deterministic answers for compliance
- GPT-4o-mini over GPT-4o — 15x cheaper, sufficient for Phase 1
- Local embeddings (all-MiniLM-L6-v2) — zero API cost during dev
- 512 word chunks — baseline to tune in Phase 2

### Next Session Goal (Phase 2)
- Run RAGAS evaluation — get 4 official benchmark scores
- Implement BM25 hybrid retrieval
- Add Cohere Rerank v3
- Add DORA document to compliance corpus
- Target: top distance < 0.40

### Current Status
- Phase 1: ✅ COMPLETE
- Phase 2: ⏳ Not started
- Live URL: local only (Streamlit localhost:8501)## Session 002 — [Today's Date]

**Phase:** Phase 1 — Basic Compliance RAG
**Branch:** main
**Duration:** [X hours]

### Work Completed
- Created compliance_ingestor.py — full PDF parsing pipeline
- Ingested PCI-DSS v4.0.1 (360 pages) into Chroma vector store
- 413 chunks created using 512-word chunking with 50-word overlap
- Embeddings: all-MiniLM-L6-v2 (local, zero API cost)
- Test query returning results with page citations

### Metrics Established (Phase 1 Baseline)
- Chunks in compliance corpus: 413
- Top result distance on test query: 0.8385
- Embedding model: all-MiniLM-L6-v2
- Chunk size: 512 words, overlap: 50 words

### Errors Encountered & Fixes
- Script ran silently — loguru output not showing in Git Bash
  Fix: used direct print() statements for debugging
- ImportError on function names — file not saved correctly in Cursor
  Fix: verified file saved with Ctrl+S, re-ran script
- ChromaDB telemetry warning — harmless, ignored

### Decisions Made
- 512 word chunks chosen as Phase 1 baseline — will tune in Phase 2
- Local embeddings (all-MiniLM-L6-v2) over OpenAI embeddings
  Reason: zero API cost during development, switch in Phase 2 if quality insufficient

### Next Session Goal
- Fix loguru output display in Git Bash
- Build basic Streamlit UI to query the compliance corpus
- Add query interface with source citation display

### Current Metrics
- Compliance corpus: 413 chunks (PCI-DSS v4.0.1)
- Query working: YES
- Distance score: 0.8385 (baseline — lower is better)