from __future__ import annotations

import re
from typing import List, Tuple

from readability import Document


def extract_visible_text(html: str) -> str:
    try:
        doc = Document(html)
        summary = doc.summary(html_partial=True)
    except Exception:
        summary = html
    return _strip_tags(summary)


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def simhash(text: str, hash_bits: int = 64) -> int:
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return 0
    v = [0] * hash_bits
    for token in tokens:
        h = hash(token)
        for i in range(hash_bits):
            bitmask = 1 << i
            v[i] += 1 if h & bitmask else -1
    fingerprint = 0
    for i in range(hash_bits):
        if v[i] >= 0:
            fingerprint |= 1 << i
    return fingerprint


def simhash_similarity(a: int, b: int, hash_bits: int = 64) -> float:
    x = a ^ b
    dist = bin(x).count("1")
    return 1 - dist / hash_bits


def cluster_simhash(urls: List[str], texts: List[str], threshold: float) -> List[Tuple[List[str], float]]:
    hashes = [simhash(text) for text in texts]
    clusters: List[Tuple[List[str], float]] = []
    used = set()
    for i, base_hash in enumerate(hashes):
        if i in used:
            continue
        group = [urls[i]]
        similarities = []
        for j in range(i + 1, len(hashes)):
            if j in used:
                continue
            similarity = simhash_similarity(base_hash, hashes[j])
            if similarity >= threshold:
                group.append(urls[j])
                similarities.append(similarity)
                used.add(j)
        if len(group) > 1:
            avg = sum(similarities) / len(similarities) if similarities else threshold
            clusters.append((group, avg))
    return clusters
