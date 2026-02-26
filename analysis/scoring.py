import math
from datetime import datetime, timedelta, timezone

from core.logger import get_logger
from core.utils import get_db

log = get_logger(__name__)


class ScoringService:
    def score_problem(self, problem_id: int) -> float:
        with get_db() as conn:
            problem = conn.execute(
                "SELECT * FROM problems WHERE id = ?", (problem_id,)
            ).fetchone()
            if not problem:
                return 0.0

            post = conn.execute(
                "SELECT * FROM raw_posts WHERE id = ?", (problem["post_id"],)
            ).fetchone()

            cluster_row = conn.execute(
                "SELECT cluster_id FROM problem_clusters WHERE problem_id = ?",
                (problem_id,),
            ).fetchone()

            cluster_size = 1
            cluster_id = None
            if cluster_row:
                cluster_id = cluster_row["cluster_id"]
                c = conn.execute(
                    "SELECT size FROM clusters WHERE id = ?", (cluster_id,)
                ).fetchone()
                if c:
                    cluster_size = c["size"]

            engagement = self._engagement_score(
                post["upvotes"] if post else 0,
                post["comments"] if post else 0,
            )
            pain = self._pain_score(problem["pain_score"])
            monetization = self._monetization_score(problem["monetization_score"])
            frequency = self._frequency_score(cluster_size)
            momentum = self._momentum_score(conn, cluster_id)

            final = engagement + pain + monetization + frequency + momentum
            final = max(0.0, min(100.0, final))

            conn.execute(
                """
                UPDATE problems
                SET engagement_score = ?, frequency_score = ?, momentum_score = ?, final_score = ?
                WHERE id = ?
                """,
                (engagement, frequency, momentum, final, problem_id),
            )

        log.debug(
            "Scored problem %d: E=%.1f P=%.1f M=%.1f F=%.1f Mo=%.1f → %.1f",
            problem_id, engagement, pain, monetization, frequency, momentum, final,
        )
        return final

    @staticmethod
    def _engagement_score(upvotes: int, comments: int) -> float:
        raw = math.log1p(upvotes) * 2 + math.log1p(comments) * 1.5
        return min(20.0, raw)

    @staticmethod
    def _pain_score(pain: float) -> float:
        return min(20.0, pain * 2.0)

    @staticmethod
    def _monetization_score(monetization: float) -> float:
        return min(20.0, monetization * 2.0)

    @staticmethod
    def _frequency_score(cluster_size: int) -> float:
        raw = math.log1p(cluster_size) * 6.0
        return min(20.0, raw)

    @staticmethod
    def _momentum_score(conn, cluster_id: int | None) -> float:
        if not cluster_id:
            return 0.0

        now = datetime.now(timezone.utc)
        seven_days_ago = (now - timedelta(days=7)).isoformat()

        row = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM problem_clusters pc
            JOIN problems p ON p.id = pc.problem_id
            WHERE pc.cluster_id = ? AND p.created_at >= ?
            """,
            (cluster_id, seven_days_ago),
        ).fetchone()

        recent_count = row["cnt"] if row else 0
        raw = math.log1p(recent_count) * 8.0
        return min(20.0, raw)
