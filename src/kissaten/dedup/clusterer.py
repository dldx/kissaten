"""Clustering algorithms for grouping duplicate farms."""

from collections import defaultdict

from kissaten.dedup.matcher import should_merge


class UnionFind:
    """
    Disjoint set data structure for clustering with path compression and union by rank.
    
    Used to efficiently group elements that are connected (i.e., should be merged).
    """
    
    def __init__(self, n: int):
        """
        Initialize Union-Find structure.
        
        Args:
            n: Number of elements (indexed 0 to n-1)
        """
        self.parent = list(range(n))  # Each element is its own parent initially
        self.rank = [0] * n  # Rank for union by rank optimization
    
    def find(self, x: int) -> int:
        """
        Find the root/representative of the set containing x.
        
        Uses path compression to flatten the tree structure.
        
        Args:
            x: Element to find root for
            
        Returns:
            Root element index
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]
    
    def union(self, x: int, y: int) -> None:
        """
        Merge the sets containing x and y.
        
        Uses union by rank to keep trees shallow.
        
        Args:
            x: First element
            y: Second element
        """
        px, py = self.find(x), self.find(y)
        if px == py:
            return  # Already in same set
        
        # Union by rank: attach smaller tree under larger tree
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


def cluster_farms(farms: list[dict], name_threshold: float = 0.90) -> list[dict]:
    """
    Group farms into clusters based on merge rules.
    
    Uses Union-Find to efficiently group farms that should be merged together.
    Each cluster represents a set of farm entries that refer to the same farm.
    
    Args:
        farms: List of farm dicts with 'farm_name', 'producer_name', 'bean_count', etc.
        name_threshold: Minimum name similarity threshold (default: 0.90)
        
    Returns:
        List of cluster dicts, each containing:
        - 'entries': List of farm dicts in this cluster
        - 'canonical_name': Selected representative name
        - 'total_bean_count': Sum of bean counts
        - 'confidence': Average confidence of merges in this cluster
        
    Example:
        >>> farms = [
        ...     {'farm_name': 'Quebraditas', 'producer_name': 'Edinson Argote', 'bean_count': 12},
        ...     {'farm_name': 'Finca Quebraditas', 'producer_name': 'Edinson Argote', 'bean_count': 1},
        ... ]
        >>> clusters = cluster_farms(farms)
        >>> len(clusters)
        1
        >>> clusters[0]['canonical_name']
        'Quebraditas'
        >>> clusters[0]['total_bean_count']
        13
    """
    n = len(farms)
    if n == 0:
        return []
    
    uf = UnionFind(n)
    merge_confidences = defaultdict(list)  # Track confidence per cluster
    
    # O(n²) pairwise comparison
    for i in range(n):
        for j in range(i + 1, n):
            should, confidence = should_merge(farms[i], farms[j], name_threshold=name_threshold)
            if should:
                # Merge the sets
                root_before_i = uf.find(i)
                root_before_j = uf.find(j)
                uf.union(i, j)
                
                # Track confidence for the resulting cluster
                new_root = uf.find(i)
                merge_confidences[new_root].append(confidence)
                
                # If we merged two existing clusters, combine their confidences
                if root_before_i != root_before_j:
                    if root_before_i != new_root and root_before_i in merge_confidences:
                        merge_confidences[new_root].extend(merge_confidences[root_before_i])
                        del merge_confidences[root_before_i]
                    if root_before_j != new_root and root_before_j in merge_confidences:
                        merge_confidences[new_root].extend(merge_confidences[root_before_j])
                        del merge_confidences[root_before_j]
    
    # Group by root to form clusters
    cluster_map = defaultdict(list)
    for i, farm in enumerate(farms):
        root = uf.find(i)
        cluster_map[root].append(farm)
    
    # Build cluster results
    clusters = []
    for root, entries in cluster_map.items():
        canonical_name = select_canonical_name(entries)
        total_bean_count = sum(e.get("bean_count", 0) for e in entries)
        
        # Calculate average confidence for this cluster
        confidences = merge_confidences.get(root, [1.0])  # Singleton gets 1.0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        
        clusters.append(
            {
                "canonical_name": canonical_name,
                "entries": entries,
                "total_bean_count": total_bean_count,
                "confidence": avg_confidence,
            }
        )
    
    # Sort by bean count (most popular first)
    clusters.sort(key=lambda c: c["total_bean_count"], reverse=True)
    
    return clusters


def select_canonical_name(entries: list[dict]) -> str:
    """
    Select the most representative farm name from a cluster.
    
    Selection criteria (in order):
    1. Prefer the entry with highest bean count
    2. If tie, prefer the longest name (more complete/formal)
    
    Args:
        entries: List of farm dicts with 'farm_name' and 'bean_count'
        
    Returns:
        Selected canonical farm name
        
    Examples:
        >>> entries = [
        ...     {'farm_name': 'Quebraditas', 'bean_count': 12},
        ...     {'farm_name': 'Finca Quebraditas', 'bean_count': 5},
        ... ]
        >>> select_canonical_name(entries)
        'Quebraditas'  # Higher bean count wins
    """
    if not entries:
        return ""
    
    # Sort by bean count (desc), then by length (desc)
    sorted_entries = sorted(entries, key=lambda e: (e.get("bean_count", 0), len(e["farm_name"])), reverse=True)
    
    return sorted_entries[0]["farm_name"]
