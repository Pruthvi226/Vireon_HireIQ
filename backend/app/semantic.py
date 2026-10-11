from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_model():
    if os.getenv("ENABLE_EMBEDDINGS", "false").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"), device="cpu")
    except Exception:
        return None


@lru_cache(maxsize=512)
def _embedding(text: str):
    model = _load_model()
    if model is None:
        return None
    try:
        return model.encode(text, normalize_embeddings=True)
    except Exception:
        return None


def semantic_similarity(left: str, right: str, fallback) -> float:
    left_embedding = _embedding(left)
    right_embedding = _embedding(right)
    if left_embedding is None or right_embedding is None:
        return fallback(left, right)
    return float(left_embedding @ right_embedding)
