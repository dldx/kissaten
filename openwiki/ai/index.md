# Files

- [AI Pipeline](ai-pipeline.md) - AI modules for extraction, categorization, search, validation, and region selection using PydanticAI and Google Gemini, including the keyword-based context filtering search architecture.
- [User Recommendation Curator](recommendation-curator.md) - Standalone script that builds a per-user taste profile from frontend/local.db, aggregates API recommendations across tasted beans, and curates final picks with a two-stage Gemini pipeline (flash-lite seed pruning + flash curation).
