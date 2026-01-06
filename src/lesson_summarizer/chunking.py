from __future__ import annotations

import math


def chunk_text(text: str, *, chunk_size: int = 10_000, overlap: int = 0) -> list[str]:
    """
    Split text into character-based chunks (like the notebook approach).
    overlap: number of chars to repeat from previous chunk (optional).
    """
    text = text or ""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")

    n = len(text)
    if n == 0:
        return []

    if overlap == 0:
        no_of_chunks = math.ceil(n / chunk_size)
        parts: list[str] = []
        bottom = 0
        top = chunk_size
        for _ in range(no_of_chunks):
            parts.append(text[bottom:top])
            bottom += chunk_size
            top += chunk_size
        return parts

    parts = []
    start = 0
    step = chunk_size - overlap
    while start < n:
        end = min(start + chunk_size, n)
        parts.append(text[start:end])
        start += step
    return parts
