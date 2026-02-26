from typing import Any

from analysis.llm_service import LLMService
from core.logger import get_logger
from core.utils import get_db, now_iso
from sources.base_source import RawPost

log = get_logger(__name__)


class ProblemExtractor:
    def __init__(self, llm: LLMService) -> None:
        self._llm = llm

    def extract_and_store(self, post: RawPost) -> int | None:
        result = self._llm.extract_problem(post.title, post.body)
        if not result:
            log.warning("No LLM result for post %s", post.id)
            return None

        if result.get("problem_summary") == "No clear problem identified":
            log.debug("No problem in post %s", post.id)
            return None

        return self._store_problem(post.id, result)

    @staticmethod
    def _store_problem(post_id: str, data: dict[str, Any]) -> int | None:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO problems
                    (post_id, problem_summary, target_group, market_type, buyer_type,
                     pain_score, monetization_score, complexity_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    data["problem_summary"],
                    data["target_group"],
                    data["market_type"],
                    data["buyer_type"],
                    data["pain_score"],
                    data["monetization_score"],
                    data["complexity_score"],
                    now_iso(),
                ),
            )
            problem_id = cursor.lastrowid
            log.debug("Stored problem %d for post %s", problem_id, post_id)
            return problem_id
