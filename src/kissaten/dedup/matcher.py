"""Farm matching logic using fuzzy string similarity and producer overlap."""

from rapidfuzz import fuzz

from kissaten.dedup.normalizer import extract_surnames, normalize_farm_name


def name_similarity(name1: str, name2: str) -> float:
    """
    Compute normalized similarity between two farm names using token set ratio.
    
    Token set ratio handles:
    - Word reordering
    - Partial matches
    - Extra/missing words
    
    Args:
        name1: First farm name (should be normalized)
        name2: Second farm name (should be normalized)
        
    Returns:
        Similarity score between 0.0 and 1.0
        
    Examples:
        >>> name_similarity("las flores", "flores")
        0.95  # High similarity despite one missing word
        >>> name_similarity("quebraditas", "quebraditas")
        1.0   # Exact match
    """
    return fuzz.token_set_ratio(name1, name2) / 100.0


def producer_overlap(surnames1: set[str], surnames2: set[str]) -> int:
    """
    Count shared surnames between two producer entries.
    
    Args:
        surnames1: Set of surnames from first producer (from extract_surnames)
        surnames2: Set of surnames from second producer (from extract_surnames)
        
    Returns:
        Number of shared surnames (0 if either set is empty)
        
    Examples:
        >>> s1 = {'edinson', 'argote', 'rojas'}
        >>> s2 = {'edinson', 'argote'}
        >>> producer_overlap(s1, s2)
        2
        >>> producer_overlap({'lasso'}, {'hernandez'})
        0
    """
    if not surnames1 or not surnames2:
        return 0
    return len(surnames1 & surnames2)


def should_merge(
    farm1: dict, farm2: dict, name_threshold: float = 0.90, exact_threshold: float = 0.99
) -> tuple[bool, float]:
    """
    Determine if two farm entries should be merged using conservative rules.
    
    Matching Rules:
    1. Primary: name_similarity ≥ 0.90 AND producer_overlap ≥ 1
    2. Exception: exact match (≥0.99) with one or both producers empty
    
    Args:
        farm1: First farm dict with 'farm_name' and 'producer_name' keys
        farm2: Second farm dict with 'farm_name' and 'producer_name' keys
        name_threshold: Minimum name similarity for match (default: 0.90)
        exact_threshold: Threshold for exact name match exception (default: 0.99)
        
    Returns:
        Tuple of (should_merge: bool, confidence_score: float)
        Confidence is 0.0 if no match, 0.5-1.0 if match
        
    Examples:
        >>> farm1 = {'farm_name': 'Quebraditas', 'producer_name': 'Edinson Argote'}
        >>> farm2 = {'farm_name': 'Finca Quebraditas', 'producer_name': 'Edinson Argote & Luz Angela'}
        >>> should_merge(farm1, farm2)
        (True, 0.95)  # High similarity + shared producer
        
        >>> farm3 = {'farm_name': 'Hamasho', 'producer_name': ''}
        >>> farm4 = {'farm_name': 'Adnan Hamasho', 'producer_name': 'Faysel A. Yonis'}
        >>> should_merge(farm3, farm4)
        (False, 0.0)  # Different operators, no producer overlap
    """
    # Normalize farm names
    norm1 = normalize_farm_name(farm1["farm_name"])
    norm2 = normalize_farm_name(farm2["farm_name"])
    
    # Calculate name similarity
    name_sim = name_similarity(norm1, norm2)
    
    # Extract producer surnames
    surnames1 = extract_surnames(farm1.get("producer_name", ""))
    surnames2 = extract_surnames(farm2.get("producer_name", ""))
    overlap = producer_overlap(surnames1, surnames2)
    
    # Primary matching rule: high similarity + producer overlap
    if name_sim >= name_threshold and overlap >= 1:
        # Confidence based on both name similarity and producer overlap
        # More shared surnames = higher confidence
        producer_confidence = min(overlap / 2.0, 1.0)  # Cap at 1.0
        confidence = (name_sim + producer_confidence) / 2.0
        return True, confidence
    
    # Exception: exact name match with empty producers
    # Lower confidence since we can't verify via producer
    if name_sim >= exact_threshold and (not surnames1 or not surnames2):
        return True, name_sim * 0.8  # 80% of name similarity
    
    return False, 0.0
