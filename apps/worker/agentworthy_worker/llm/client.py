"""Unified LLM client with retries and cost logging."""

import logging
import time
import uuid
from typing import Any

from agentworthy.database import SessionLocal
from agentworthy.models import LLMUsage

from agentworthy_worker.llm.config import BACKOFF_BASE_SECONDS, HAIKU_MODEL, MAX_RETRIES

logger = logging.getLogger(__name__)


class LLMClient:
  def __init__(self, api_key: str | None = None, scan_id: str | None = None) -> None:
    self.scan_id = scan_id
    self._api_key = api_key
    self._client: Any = None

  @property
  def client(self) -> Any:
    if self._client is None:
      import os
      import anthropic

      key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
      if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
      self._client = anthropic.Anthropic(api_key=key)
    return self._client

  def _log_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
    db = SessionLocal()
    try:
      scan_uuid = uuid.UUID(self.scan_id) if self.scan_id else None
      db.add(
        LLMUsage(
          scan_id=scan_uuid,
          model=model,
          input_tokens=input_tokens,
          output_tokens=output_tokens,
        )
      )
      db.commit()
    finally:
      db.close()
    logger.info(
      "LLM usage",
      extra={
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "scan_id": self.scan_id,
      },
    )

  def complete(
    self,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 256,
  ) -> str:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
      try:
        response = self.client.messages.create(
          model=model,
          max_tokens=max_tokens,
          system=system,
          messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        self._log_usage(model, response.usage.input_tokens, response.usage.output_tokens)
        return text
      except Exception as e:
        last_error = e
        if attempt < MAX_RETRIES:
          time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
    raise last_error  # type: ignore[misc]


def classify_site_type(
  title: str,
  homepage_text: str,
  scan_id: str | None = None,
  llm: LLMClient | None = None,
) -> str:
  """Classify site type using haiku. Returns one of: ecommerce, restaurant, local, saas, lead-gen, other."""
  client = llm or LLMClient(scan_id=scan_id)
  system = (
    "You classify websites into exactly one category. "
    "Reply with only one word from: ecommerce, restaurant, local, saas, lead-gen, other."
  )
  user = f"Title: {title}\n\nHomepage text (truncated):\n{homepage_text[:3000]}"
  try:
    result = client.complete(HAIKU_MODEL, system, user, max_tokens=16).strip().lower()
    valid = {"ecommerce", "restaurant", "local", "saas", "lead-gen", "other"}
    return result if result in valid else "other"
  except RuntimeError:
    return "other"
