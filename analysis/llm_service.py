import json
import time
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from core.config import config
from core.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a startup problem analyst. Given a post from an online community, extract the core business problem or pain point being described.

Respond ONLY with a valid JSON object. No markdown, no code fences, no extra text.

Schema:
{
  "problem_summary": "One concise sentence describing the problem",
  "target_group": "Who experiences this problem",
  "market_type": "B2B | Consumer | Tech | Hybrid",
  "buyer_type": "Who would pay for a solution",
  "pain_score": <integer 1-10>,
  "monetization_score": <integer 1-10>,
  "complexity_score": <integer 1-10>
}

If the post does not describe a clear problem or pain point, set all scores to 0 and problem_summary to "No clear problem identified"."""

REQUIRED_FIELDS = {
    "problem_summary": str,
    "target_group": str,
    "market_type": str,
    "buyer_type": str,
    "pain_score": (int, float),
    "monetization_score": (int, float),
    "complexity_score": (int, float),
}

VALID_MARKET_TYPES = {"B2B", "Consumer", "Tech", "Hybrid"}


class LLMService:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_TIMEOUT,
        )

    def extract_problem(self, title: str, body: str) -> dict[str, Any] | None:
        user_content = f"Title: {title}\n\nBody: {body[:3000]}" if body else f"Title: {title}"

        for attempt in range(1, config.OPENAI_MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.2,
                    max_tokens=500,
                )
                raw = response.choices[0].message.content.strip()
                parsed = self._parse_json(raw)
                if parsed:
                    return parsed
                log.warning("LLM returned invalid JSON on attempt %d", attempt)
            except (APITimeoutError, RateLimitError) as exc:
                wait = min(2 ** attempt, 60)
                log.warning("LLM %s on attempt %d, retrying in %ds", type(exc).__name__, attempt, wait)
                time.sleep(wait)
            except APIError as exc:
                log.error("LLM API error on attempt %d: %s", attempt, exc)
                wait = min(2 ** attempt, 60)
                time.sleep(wait)
            except Exception as exc:
                log.error("Unexpected LLM error: %s", exc)
                return None

        log.error("LLM extraction failed after %d attempts", config.OPENAI_MAX_RETRIES)
        return None

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        for field, expected_type in REQUIRED_FIELDS.items():
            if field not in data:
                return None
            if not isinstance(data[field], expected_type):
                return None

        for score_field in ("pain_score", "monetization_score", "complexity_score"):
            val = data[score_field]
            data[score_field] = max(0, min(10, int(val)))

        if data["market_type"] not in VALID_MARKET_TYPES:
            data["market_type"] = "Hybrid"

        return data
