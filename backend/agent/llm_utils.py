"""Helpers for reading Anthropic Messages API responses."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def response_text(message: Any) -> str:
    """
    Join the text blocks of a Messages API response.

    Newer models can put a thinking block before the answer, so reading
    ``content[0].text`` is not safe. Thinking tokens count towards
    ``max_tokens``, so a truncated answer is logged.
    """
    if getattr(message, "stop_reason", None) == "max_tokens":
        logger.warning("Claude response was cut off at max_tokens; consider raising the limit")
    blocks = getattr(message, "content", None) or []
    return "".join(
        block.text for block in blocks if isinstance(getattr(block, "text", None), str)
    )
