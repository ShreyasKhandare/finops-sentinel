## Session 002 — [Today's Date]

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