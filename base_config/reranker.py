"""Reranker service — re-ranks search results using bge-base-zh-v1.5 embeddings.

The hybrid search in ``retrieve.py`` combines vector + BM25 scores with fixed
boosts (2.0 vs 1.0). This module re-ranks candidates by computing pure cosine
similarity between the query embedding and each document's text embedding,
using the **same** ``bge-base-zh-v1.5`` model already loaded for indexing/search.

This gives a cleaner semantic relevance signal than the hybrid score fusion,
without requiring a separate cross-encoder model.

Architecture:
    hybrid_search() → top-N candidates → embed & score → top-K final
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any

from retrieve import ModelSingleton

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def rerank(
    query: str,
    documents: list[dict],
    top_k: int | None = None,
    batch_size: int = 32,
) -> list[dict]:
    """Re-rank candidate documents by embedding cosine similarity.

    Computes the query embedding once, then encodes all candidate document
    texts in a single batch and scores each via cosine similarity (dot product
    on L2-normalized vectors).

    Args:
        query: The user's search query.
        documents: Candidate documents from ``hybrid_search()``. Each dict
                   must contain at least ``text_for_embedding`` (used as
                   the document text for embedding).
        top_k: If set, return only the top-K documents after reranking.
               Defaults to returning all candidates.
        batch_size: Batch size for document embedding.

    Returns:
        The same document dicts with ``_score`` updated to the cosine
        similarity (0–1) and ``_rerank_score`` preserving the original
        hybrid score. Sorted by new ``_score`` descending.
    """
    if not documents:
        return []

    model = ModelSingleton.get_model()

    # --- 1. Encode query ---
    query_vec = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )  # shape: (768,)

    # --- 2. Extract document texts ---
    doc_texts = [_extract_doc_text(doc) for doc in documents]

    # --- 3. Batch-encode documents ---
    try:
        doc_vecs = model.encode(
            doc_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False,
        )  # shape: (n_docs, 768)
    except Exception as e:
        logger.error(f"Document embedding failed: {e}")
        return documents

    # --- 4. Cosine similarity (dot product, since vectors are normalized) ---
    # query_vec: (768,)  doc_vecs: (n, 768)  → scores: (n,)
    scores = np.dot(doc_vecs, query_vec)  # cosine similarity ∈ [-1, 1]

    # --- 5. Attach scores and sort ---
    for doc, score in zip(documents, scores):
        doc["_rerank_score"] = doc.get("_score", 0.0)  # preserve original
        doc["_score"] = float(score)  # cosine similarity as new score

    documents.sort(key=lambda d: d.get("_score", 0), reverse=True)

    if top_k is not None and top_k > 0:
        return documents[:top_k]

    return documents


# ────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────

def _extract_doc_text(doc: dict) -> str:
    """Extract a representative text string from a document for embedding.

    Prefers ``text_for_embedding`` (the flattened representation used at
    index time — best semantic match), falling back to combining the most
    informative fields.
    """
    text = doc.get("text_for_embedding", "")
    if text:
        return str(text)

    parts: list[str] = []
    for field in ("name", "categories", "city", "address", "state"):
        val = doc.get(field, "")
        if val:
            parts.append(str(val))
    return " | ".join(parts)
