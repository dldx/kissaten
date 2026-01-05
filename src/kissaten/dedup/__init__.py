"""Farm name deduplication utilities for Kissaten."""

from kissaten.dedup.clusterer import UnionFind, cluster_farms, select_canonical_name
from kissaten.dedup.matcher import name_similarity, producer_overlap, should_merge
from kissaten.dedup.normalizer import extract_surnames, normalize_farm_name

__all__ = [
    "normalize_farm_name",
    "extract_surnames",
    "name_similarity",
    "producer_overlap",
    "should_merge",
    "UnionFind",
    "cluster_farms",
    "select_canonical_name",
]
