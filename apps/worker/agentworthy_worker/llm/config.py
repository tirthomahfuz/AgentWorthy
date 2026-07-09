"""LLM model configuration — single source of truth for model names."""

# Classification and cheap steps
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Agent simulation and fix generation (Stage 3+)
SONNET_MODEL = "claude-sonnet-4-6"

MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 1.0
