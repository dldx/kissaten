# AI Varietal Categorization System

This module implements an AI-powered system for standardizing and categorizing coffee varietal names using Gemini Flash 3 and reference data.

## Overview

The varietal categorizer solves the problem of inconsistent coffee varietal naming across different roasters by:
- Normalizing spelling variations and typos
- Splitting compound varietals (e.g., "Caturra, Castillo & Bourbon")
- Mapping to canonical names from authoritative reference data
- Maintaining confidence scores for categorizations
- Detecting and resolving conflicts in mappings

## Architecture

### Components

1. **Reference Data Layer**: `coffee_varietals.json`
   - Authoritative source of canonical varietal names
   - Contains alternate names, descriptions, and metadata
   - Used for validation and normalization

2. **AI Agent Layer**: Three specialized pydantic-ai agents
   - **Categorization Agent**: Maps original names to canonical forms
   - **Merge Review Agent**: Consolidates similar canonical names
   - **Conflict Resolution Agent**: Resolves duplicate mappings

3. **Storage Layer**: `varietal_mappings.json`
   - Persistent store of original → canonical mappings
   - Includes metadata (confidence, compound status, separators)
   - Supports incremental updates

4. **Database Layer**: DuckDB integration
   - Reads raw varietal names from `kissaten.duckdb`
   - Provides source data for categorization

### Data Flow

```
┌─────────────────────┐
│ kissaten.duckdb     │
│ (raw varietal names)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐        ┌──────────────────────┐
│ VarietalCategorizer │◄───────┤ coffee_varietals.json│
│                     │        │ (reference data)     │
└──────────┬──────────┘        └──────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Gemini Flash 3      │
│ (categorization)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│varietal_mappings.json│
│ (output mappings)   │
└─────────────────────┘
```

## Data Models

### VarietalMapping

Core model representing a single varietal categorization:

```python
class VarietalMapping(BaseModel):
    original_name: str           # Original name from database
    canonical_names: list[str]   # Standardized name(s)
    confidence: float            # 0-1 confidence score
    is_compound: bool            # True if multiple varietals
    separator: str | None        # Separator for compounds (, & /)
```

**Example - Simple Varietal**:
```json
{
    "original_name": "caturra rojo",
    "canonical_names": ["Red Caturra"],
    "confidence": 0.95,
    "is_compound": false,
    "separator": null
}
```

**Example - Compound Varietal**:
```json
{
    "original_name": "Caturra, Castillo & Bourbon",
    "canonical_names": ["Caturra", "Castillo", "Bourbon"],
    "confidence": 0.98,
    "is_compound": true,
    "separator": ", &"
}
```

### VarietalBatch

Container for batch processing:

```python
class VarietalBatch(BaseModel):
    mappings: list[VarietalMapping]
    batch_number: int
    total_batches: int
```

### ConflictResolution

Used for resolving duplicate canonical name conflicts:

```python
class ConflictResolution(BaseModel):
    canonical_name: str          # The canonical name in question
    should_merge: bool           # Should variations merge?
    merged_name: str | None      # Final merged name if true
    reasoning: str               # Explanation of decision
```

## AI Agent Prompts

### Categorization Agent

**System Prompt**:
- Reference varietal names provided in context
- Rules for simple vs compound varietals
- Confidence scoring guidelines (0.9+ for exact matches, 0.7-0.9 for variations, <0.7 for uncertain)
- Special cases: color variants (Red/Yellow Bourbon), technical codes (JARC, SL, H varieties)
- Separator detection for compounds (, & /)

**Key Rules**:
1. Preserve color information (Red Caturra ≠ Yellow Caturra)
2. Respect technical naming (SL28 ≠ SL34)
3. Detect compound varietals by looking for separators
4. Return original name if no match found (confidence < 0.5)

### Merge Review Agent

**Purpose**: Consolidate canonical names that represent the same varietal

**System Prompt**:
- Review list of canonical names
- Identify case variations (Caturra vs caturra)
- Identify spelling variations (Typica vs Typica)
- Provide merged canonical name and reasoning

**Example Output**:
```json
{
    "merges": [
        {
            "original_names": ["caturra", "Caturra", "CATURRA"],
            "merged_name": "Caturra",
            "reasoning": "Case variations of same varietal"
        }
    ]
}
```

### Conflict Resolution Agent

**Purpose**: Determine if multiple original names should map to the same canonical name

**System Prompt**:
- Compare original names that map to same canonical
- Determine if they're truly the same (typos, abbreviations)
- Or if they're different varietals incorrectly mapped

**Example Output**:
```json
{
    "canonical_name": "Bourbon",
    "should_merge": true,
    "merged_name": "Bourbon",
    "reasoning": "Both 'Bourbon' and 'Burbon' are the same varietal (typo)"
}
```

## Processing Pipeline

### Phase 1: Initial Categorization

1. **Load Reference Data**: Parse `coffee_varietals.json` into lookup dictionary
2. **Query Database**: Extract unique varietal names from DuckDB
3. **Load Existing Mappings**: Check `varietal_mappings.json` for previous work
4. **Batch Processing**: Process new names in batches of 50
5. **AI Categorization**: Send batch to Gemini with reference context
6. **Save Incrementally**: Append new mappings to JSON file

**Command**:
```bash
uv run python -m kissaten.ai.varietal_categorizer categorize
```

**Progress Output**:
```
Loading reference varietals from coffee_varietals.json...
Loaded 156 varietal names from reference
Processing 1,234 unique varietals from database
Found 500 existing mappings, 734 new to process

Categorizing varietals: ████████████████ 100% 734/734
```

### Phase 2: Conflict Detection

Automatically runs after categorization to find duplicates:

1. **Group by Canonical**: Find all original names → same canonical
2. **Filter Conflicts**: Identify groups with 2+ original names
3. **Display Conflicts**: Show table of conflicts for review

**Example Conflict**:
```
Canonical: Bourbon
Originals: Bourbon (conf: 0.95), Burbon (conf: 0.85), Borbon (conf: 0.80)
```

### Phase 3: Conflict Resolution (Optional)

Uses AI to resolve detected conflicts:

1. **Load Conflicts**: Read from conflict detection
2. **AI Resolution**: Ask GPT-4o if names should merge
3. **Apply Decisions**: Update mappings based on AI recommendations
4. **Save Results**: Write resolved mappings back to JSON

**Interactive Prompt**:
```
Found 15 conflicts to resolve
Resolving conflicts: ████████████████ 100% 15/15

Summary:
- Merged: 12 conflicts
- Kept separate: 3 conflicts
```

### Phase 4: Merge Review (Optional)

Reviews canonical names for consolidation:

1. **Extract Canonical Names**: Get unique list from mappings
2. **AI Review**: Send to merge review agent in batches
3. **Apply Merges**: Update all mappings with merged names
4. **Save Results**: Write consolidated mappings

**Command**:
```bash
uv run python -m kissaten.ai.varietal_categorizer review
```

## Usage

### Basic Workflow

```bash
# 1. Initial categorization
uv run python -m kissaten.ai.varietal_categorizer categorize

# 2. Review results
cat src/kissaten/database/varietal_mappings.json | jq '.[] | select(.confidence < 0.7)'

# 3. Optional: Run merge review for further consolidation
uv run python -m kissaten.ai.varietal_categorizer categorize --review-and-merge
```

### Incremental Updates

The system supports incremental processing:

```bash
# First run: processes all 1,000 varietals
uv run python -m kissaten.ai.varietal_categorizer categorize

# Second run: only processes new varietals added since last run
uv run python -m kissaten.ai.varietal_categorizer categorize
```

**Output**:
```
Found 1,000 existing mappings, 25 new to process
Categorizing varietals: 100% 25/25
```

### Statistics and Validation

After categorization, review statistics:

```
Categorization complete!

Statistics:
- Total mappings: 1,234
- Simple varietals: 890 (72.1%)
- Compound varietals: 344 (27.9%)
- Average confidence: 0.87
- Conflicts detected: 15

High confidence (≥0.9): 980 (79.4%)
Medium confidence (0.7-0.9): 220 (17.8%)
Low confidence (<0.7): 34 (2.8%)

Example mappings:
  "caturra" → ["Caturra"] (0.95)
  "Castillo, Caturra" → ["Castillo", "Caturra"] (0.98)
  "bourbon rojo" → ["Red Bourbon"] (0.92)
```

## Configuration

### Environment Variables

Required in `.env`:

```bash
GEMINI_API_KEY=...
LOGFIRE_TOKEN=...  # Optional, for monitoring
```

### Database Path

Default: `data/kissaten.duckdb`

Override with environment variable:
```bash
DATABASE_PATH=path/to/custom.duckdb uv run python -m kissaten.ai.varietal_categorizer categorize
```

### Reference Data

Expected location: `src/kissaten/database/coffee_varietals.json`

**Format**:
```json
[
    {
        "name": "Caturra",
        "aliases": ["Red Caturra", "Yellow Caturra"],
        "description": "...",
        "wikidata_id": "Q123456"
    }
]
```

### Output Location

Default: `src/kissaten/database/varietal_mappings.json`

## Performance Considerations

### API Costs

- **Batch Processing**: 50 varietals per API call reduces costs
- **Caching**: Existing mappings prevent re-processing
- **Token Usage**: ~2K tokens per batch (input + output)

**Estimated Cost** (Gemini Flash 3 pricing):
- 1,000 varietals ≈ 20 batches × 2K tokens ≈ 40K tokens
- Cost: Free tier or minimal cost with Gemini Flash

### Processing Time

- **Categorization**: ~3-5 seconds per batch
- **Total Time**: 1,000 varietals ≈ 1-2 minutes
- **Conflict Resolution**: ~2-3 seconds per conflict
- **Merge Review**: ~5-10 seconds per 100 canonical names

### Rate Limiting

Built-in handling for Gemini rate limits:
- Automatic retry with exponential backoff
- Batch processing to stay under TPM limits
- Progress bars show current status

## Integration with Kissaten

### Database Schema

Reads from existing `coffee_beans` table:

```sql
SELECT DISTINCT varietal
FROM coffee_beans
WHERE varietal IS NOT NULL
  AND varietal != '';
```

### API Endpoints (Future)

Planned integration:

```python
# GET /api/v1/varietals/canonical
# Returns list of canonical varietal names

# GET /api/v1/varietals/{name}/mapping
# Returns canonical mapping for a varietal name

# GET /api/v1/varietals/stats
# Returns categorization statistics
```

### Frontend Display (Future)

Use canonical names for:
- Search filters (unified varietal selection)
- Coffee bean details (standardized display)
- Analytics (accurate varietal statistics)

## Maintenance

### Adding New Reference Varietals

1. Update `coffee_varietals.json` with new varietal
2. Re-run categorization (will only process unmapped names)
3. Review mappings for new varietals

### Handling Low Confidence Mappings

```bash
# Find low confidence mappings
cat src/kissaten/database/varietal_mappings.json | \
  jq '.[] | select(.confidence < 0.7) |
  {original_name, canonical_names, confidence}'

# Manual review and correction
# Edit varietal_mappings.json directly or
# Re-run with updated reference data
```

### Reprocessing All Varietals

To force reprocessing (e.g., after major reference data update):

```bash
# Backup existing mappings
cp src/kissaten/database/varietal_mappings.json \
   src/kissaten/database/varietal_mappings.backup.json

# Delete mappings file
rm src/kissaten/database/varietal_mappings.json

# Reprocess all
uv run python -m kissaten.ai.varietal_categorizer categorize --review-and-merge
```

## Troubleshooting

### Issue: API Rate Limit Errors

**Symptom**: Gemini API returns 429 errors

**Solution**:
- Reduce batch size (modify `BATCH_SIZE` constant)
- Add delay between batches (uncomment sleep in code)
- Check Gemini account rate limits

### Issue: Low Confidence Mappings

**Symptom**: Many mappings with confidence < 0.7

**Solution**:
- Review reference data for missing varietals
- Add aliases to `coffee_varietals.json`
- Manually verify and correct mappings

### Issue: Incorrect Compound Splitting

**Symptom**: Single varietal incorrectly split into multiple

**Solution**:
- Check separator detection logic
- Review AI prompt for compound detection
- Manually correct in `varietal_mappings.json`

### Issue: Merge Conflicts

**Symptom**: Different varietals incorrectly merged

**Solution**:
- Review conflict resolution decisions
- Update reference data with distinctions
- Manually separate in mappings file

## Future Enhancements

### Planned Features

1. **Active Learning**: User feedback loop for corrections
2. **Version Control**: Track mapping changes over time
3. **Confidence Tuning**: ML model for confidence calibration
4. **Bulk Operations**: CLI tools for bulk mapping edits
5. **API Integration**: Real-time categorization endpoint
6. **Quality Metrics**: Precision/recall tracking with ground truth

### Advanced Features

1. **Hierarchical Categorization**: Group varietals by species (Arabica/Robusta)
2. **Geographic Clustering**: Region-specific varietal associations
3. **Temporal Analysis**: Track varietal popularity over time
4. **Cross-Roaster Analysis**: Identify roaster-specific naming patterns

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Google Gemini API](https://ai.google.dev/)
- [Coffee Varietal Database](https://varieties.worldcoffeeresearch.org/)
- [Kissaten Project Structure](../AGENTS.md)
