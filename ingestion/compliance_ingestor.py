"""
FinOps Sentinel — Compliance Document Ingestion Pipeline
Phase 1: Ingest regulatory PDFs into Chroma vector store

Handles: PDF parsing, text chunking, embedding, storage
Corpus: 'compliance' namespace in Chroma
"""

from pathlib import Path
from typing import Optional
import os

import chromadb
import fitz  # PyMuPDF
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
CHROMA_PATH = Path("chroma_db")
COLLECTION_NAME = "compliance"
CHUNK_SIZE = 512        # tokens approx — we'll tune this in Phase 2
CHUNK_OVERLAP = 50      # overlap between chunks to preserve context


# ── CHUNKING ──────────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by word count.

    Args:
        text: Raw text to split
        chunk_size: Approximate words per chunk
        overlap: Number of words to overlap between chunks

    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    logger.debug(f"Created {len(chunks)} chunks from {len(words)} words")
    return chunks


# ── PDF PARSING ───────────────────────────────────────────────────────────────
def parse_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text from PDF page by page using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dicts with keys: text, page_number, source
    """
    logger.info(f"Parsing PDF: {pdf_path.name}")
    pages = []

    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():  # skip empty pages
                pages.append({
                    "text": text,
                    "page_number": page_num + 1,
                    "source": pdf_path.name,
                })
        doc.close()
        logger.success(f"Parsed {len(pages)} pages from {pdf_path.name}")

    except Exception as e:
        logger.error(f"Failed to parse {pdf_path.name}: {e}")
        raise

    return pages


# ── CHROMA SETUP ──────────────────────────────────────────────────────────────
def get_chroma_collection(chroma_path: Path = CHROMA_PATH) -> chromadb.Collection:
    """
    Get or create the compliance collection in Chroma.

    Args:
        chroma_path: Directory to persist Chroma data

    Returns:
        Chroma collection object
    """
    chroma_path.mkdir(exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_path))

    # Use sentence-transformers for local embeddings — no API cost
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Financial regulatory compliance documents"},
    )

    logger.info(f"Chroma collection '{COLLECTION_NAME}' ready — {collection.count()} existing docs")
    return collection


# ── MAIN INGESTION ────────────────────────────────────────────────────────────
def ingest_pdf(
    pdf_path: Path,
    collection: chromadb.Collection,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> int:
    """
    Full pipeline: parse PDF → chunk → embed → store in Chroma.

    Args:
        pdf_path: Path to PDF file
        collection: Chroma collection to store chunks
        chunk_size: Words per chunk
        overlap: Overlap between chunks

    Returns:
        Number of chunks ingested
    """
    logger.info(f"Starting ingestion: {pdf_path.name}")

    # Step 1: Parse PDF into pages
    pages = parse_pdf(pdf_path)

    # Step 2: Chunk each page and build records
    documents = []
    metadatas = []
    ids = []

    for page in pages:
        chunks = chunk_text(page["text"], chunk_size, overlap)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{pdf_path.stem}_p{page['page_number']}_c{i}"
            documents.append(chunk)
            metadatas.append({
                "source": page["source"],
                "page_number": page["page_number"],
                "chunk_index": i,
                "document_type": "regulatory",
            })
            ids.append(chunk_id)

    # Step 3: Store in Chroma (batch to avoid memory issues)
    batch_size = 100
    total_ingested = 0

    for batch_start in range(0, len(documents), batch_size):
        batch_end = batch_start + batch_size
        collection.add(
            documents=documents[batch_start:batch_end],
            metadatas=metadatas[batch_start:batch_end],
            ids=ids[batch_start:batch_end],
        )
        total_ingested += len(documents[batch_start:batch_end])
        logger.debug(f"Ingested batch {batch_start}–{batch_end}")

    logger.success(f"Ingestion complete: {total_ingested} chunks from {pdf_path.name}")
    return total_ingested


# ── QUERY TEST ────────────────────────────────────────────────────────────────
def query_compliance(
    query: str,
    collection: chromadb.Collection,
    n_results: int = 5,
) -> list[dict]:
    """
    Query the compliance corpus with a natural language question.

    Args:
        query: Natural language question
        collection: Chroma collection to query
        n_results: Number of results to return

    Returns:
        List of result dicts with text, source, page, distance
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    formatted = []
    for i in range(len(results["documents"][0])):
        formatted.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "page": results["metadatas"][0][i]["page_number"],
            "distance": results["distances"][0][i],
        })

    return formatted


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # Setup
    logger.info("FinOps Sentinel — Compliance Ingestion Pipeline")
    logger.info("=" * 50)

    # Find PDF
    pdf_dir = Path("evaluation/test_datasets")
    pdfs = list(pdf_dir.glob("*.pdf"))

    if not pdfs:
        logger.error(f"No PDFs found in {pdf_dir}")
        logger.info("Please add a PDF to evaluation/test_datasets/ and run again")
        sys.exit(1)

    # Ingest all PDFs found
    collection = get_chroma_collection()

    total = 0
    for pdf in pdfs:
        count = ingest_pdf(pdf, collection)
        total += count

    logger.success(f"Total chunks in compliance corpus: {collection.count()}")

    # Run 3 test queries to verify ingestion worked
    logger.info("\nRunning test queries...")
    logger.info("-" * 40)

    test_queries = [
        "What are the requirements for password security?",
        "What are the encryption requirements for cardholder data?",
        "What are the access control requirements?",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: {query}")
        results = query_compliance(query, collection)
        for j, r in enumerate(results[:2]):  # show top 2
            logger.info(f"  Result {j+1} | Page {r['page']} | Distance: {r['distance']:.4f}")
            logger.info(f"  Text: {r['text'][:200]}...")