"""OpenSearch hybrid search — BM25 + k-NN vector retrieval."""
from __future__ import annotations

import threading
from typing import Any

import numpy as np
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

from app.core.config import settings

# ── Globals (lazy init) ──────────────────────────────────
_os_client: OpenSearch | None = None
_embedding_model: SentenceTransformer | None = None
_lock = threading.Lock()


def _get_os_client() -> OpenSearch:
    global _os_client
    if _os_client is None:
        with _lock:
            if _os_client is None:
                kwargs: dict[str, Any] = {
                    "hosts": [{"host": settings.opensearch_host, "port": settings.opensearch_port}],
                    "use_ssl": settings.opensearch_use_ssl,
                    "verify_certs": False,
                    "ssl_show_warn": False,
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_on_timeout": True,
                }
                if settings.opensearch_user and settings.opensearch_password:
                    kwargs["http_auth"] = (settings.opensearch_user, settings.opensearch_password)
                _os_client = OpenSearch(**kwargs)
    return _os_client


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        with _lock:
            if _embedding_model is None:
                _embedding_model = SentenceTransformer(settings.embedding_model_dir)
    return _embedding_model


def _ndarray_to_list(vec: np.ndarray) -> list[float]:
    return vec.tolist()  # type: ignore[no-any-return]


# ── Public API ───────────────────────────────────────────

def search_businesses(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """Hybrid search: vector similarity + BM25 text match on business index.

    Returns a list of business dicts, each with an added ``_score`` field.
    """
    top_k = top_k or settings.top_k
    min_score = min_score or settings.similarity_threshold

    model = _get_embedding_model()
    query_vector = _ndarray_to_list(model.encode(query, convert_to_numpy=True))

    client = _get_os_client()

    # ── Build hybrid search body ──
    body: dict[str, Any] = {
        "size": top_k,
        "query": {
            "hybrid": {
                "queries": [
                    {
                        "bool": {
                            "should": [
                                {"match": {"name": {"query": query, "boost": 2.0}}},
                                {"match": {"categories": {"query": query, "boost": 1.5}}},
                                {"match": {"text_for_embedding": {"query": query, "boost": 1.0}}},
                            ]
                        }
                    },
                    {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": top_k,
                            }
                        }
                    },
                ]
            }
        },
        "_source": {
            "excludes": ["embedding", "text_for_embedding"]
        },
    }

    try:
        res = client.search(index=settings.business_index, body=body)
    except Exception:
        # fallback: pure BM25 if hybrid not supported
        body = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "categories^1.5", "text_for_embedding"],
                }
            },
            "_source": {"excludes": ["embedding", "text_for_embedding"]},
        }
        try:
            res = client.search(index=settings.business_index, body=body)
        except Exception:
            return []

    hits = res.get("hits", {}).get("hits", [])
    results: list[dict[str, Any]] = []
    for h in hits:
        if h.get("_score", 0) >= min_score:
            doc = h["_source"]
            doc["_score"] = h["_score"]
            results.append(doc)

    return results


def search_reviews_for_business(
    business_id: str,
    query: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve top reviews for a business, optionally filtered by query relevance."""
    client = _get_os_client()

    if not client.indices.exists(index=settings.review_index):
        return []

    must_clauses: list[dict[str, Any]] = [
        {"term": {"business_id": business_id}}
    ]

    if query:
        must_clauses.append({
            "multi_match": {
                "query": query,
                "fields": ["text^2"],
            }
        })

    body: dict[str, Any] = {
        "size": top_k,
        "query": {"bool": {"must": must_clauses}},
        "sort": [{"useful": {"order": "desc"}}],
    }

    try:
        res = client.search(index=settings.review_index, body=body)
    except Exception:
        return []

    return [h["_source"] for h in res.get("hits", {}).get("hits", [])]


def get_business_by_id(business_id: str) -> dict[str, Any] | None:
    """Fetch a single business by its ID."""
    client = _get_os_client()
    try:
        res = client.get(index=settings.business_index, id=business_id)
        return res.get("_source")  # type: ignore[no-any-return]
    except Exception:
        return None
