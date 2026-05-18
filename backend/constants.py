"""
Constants used throughout the backend application
"""
import os

# API Configuration
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
CORS_ALLOW_ORIGINS = [x.strip() for x in _cors_origins.split(",") if x.strip()] or ["*"]
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# LLM Configuration
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
MAX_TOKENS_GENERATION = 2000
MAX_TOKENS_MATCHING = 500
# Max LangGraph steps for metadata ReAct subgraph (includes model + tool nodes).
MAX_METADATA_REACT_RECURSION = 25

# Similarity Thresholds
HIGH_SIMILARITY_THRESHOLD = 0.80
LOW_SIMILARITY_THRESHOLD = 0.50
CONFIDENCE_THRESHOLD = 0.50

# Error Messages
ERROR_EMPTY_DESCRIPTION = "Description cannot be empty"
ERROR_API_KEY_MISSING_ANTHROPIC = "ANTHROPIC_API_KEY environment variable is not set"
ERROR_API_KEY_MISSING_OPENAI = "OPENAI_API_KEY environment variable is not set"
ERROR_GENERATION_FAILED = "Failed to generate rules"
ERROR_METADATA_CHECK_FAILED = "Failed to check metadata"
ERROR_JSON_PARSE_FAILED = "Could not parse JSON from LLM response"

