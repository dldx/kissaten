"""Text normalization utilities for farm and producer names."""

import re
import unicodedata


# Prefixes and suffixes to strip from farm names (order matters - longer first)
FARM_PREFIXES = [
    "finca ",
    "hacienda ",
    "fazenda ",
]

FARM_SUFFIXES = [
    " coffee processing center",
    " coffee farm",
    " washing station",
    " drying station",
    " community farmers",
    " coffee",
    " station",
    " farm",
    " village",
]

# Words to ignore when extracting producer surnames
PRODUCER_STOPWORDS = {
    "and",
    "&",
    "family",
    "families",
    "brothers",
    "sisters",
    "smallholder",
    "smallholders",
    "farmers",
    "producers",
    "various",
    "regional",
    "lot",
    "collective",
    "community",
    "cooperative",
    "coop",
    "coffee",
    "farm",
    "finca",
    "proyecto",
    "project",
    "small",
    "farming",
}


def normalize_farm_name(name: str) -> str:
    """
    Normalize farm name for comparison.
    
    Normalization steps:
    1. Remove accents/diacritics (NFD decomposition)
    2. Convert to lowercase
    3. Strip common prefixes (Finca, Hacienda, etc.)
    4. Strip common suffixes (Farm, Station, Village, etc.)
    5. Strip whitespace
    
    Args:
        name: Farm name to normalize
        
    Returns:
        Normalized farm name suitable for comparison
        
    Examples:
        >>> normalize_farm_name("Finca Las Flores")
        'las flores'
        >>> normalize_farm_name("Quebraditas Coffee Farm")
        'quebraditas'
        >>> normalize_farm_name("Elora Washing Station")
        'elora'
    """
    if not name:
        return ""
    
    # NFD decomposition to separate base characters from combining marks (accents)
    name = unicodedata.normalize("NFD", name)
    # Remove combining marks (category Mn = Mark, nonspacing)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    
    # Convert to lowercase
    name = name.lower().strip()
    
    # Strip prefixes
    for prefix in FARM_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break  # Only strip one prefix
    
    # Strip suffixes
    for suffix in FARM_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break  # Only strip one suffix
    
    return name.strip()


def extract_surnames(producer: str) -> set[str]:
    """
    Extract likely surnames from producer string.
    
    Extracts words (≥3 characters) that are likely to be names,
    filtering out common stopwords like "family", "brothers", "smallholder", etc.
    
    Args:
        producer: Producer name string (may contain multiple names, families, etc.)
        
    Returns:
        Set of extracted surname strings (lowercased)
        
    Examples:
        >>> extract_surnames("Edinson Argote & Luz Ángela Rojas")
        {'edinson', 'argote', 'luz', 'angela', 'rojas'}
        >>> extract_surnames("Lasso Brothers")
        {'lasso'}
        >>> extract_surnames("Various smallholder farmers")
        set()
    """
    if not producer:
        return set()
    
    # Normalize accents first
    producer = unicodedata.normalize("NFD", producer)
    producer = "".join(c for c in producer if unicodedata.category(c) != "Mn")
    
    # Extract words that look like names (letters, ≥3 chars)
    # Include common name characters across languages
    words = re.findall(r"\b[A-Za-z]{3,}\b", producer.lower())
    
    # Filter out stopwords
    return {w for w in words if w not in PRODUCER_STOPWORDS}
