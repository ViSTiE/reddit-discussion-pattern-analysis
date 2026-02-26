import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.clustering import ClusteringService
from analysis.llm_service import LLMService
from analysis.problem_extractor import ProblemExtractor
from analysis.scoring import ScoringService
from core.logger import get_logger
from core.utils import get_db, init_db, now_iso, post_exists
from embeddings.embedding_service import EmbeddingService
from sources.askhn_source import AskHNSource
from sources.base_source import BaseSource, RawPost
from sources.reddit_source import RedditSource

log = get_logger("pipeline")


def get_enabled_sources() -> list[BaseSource]:
    sources: list[BaseSource] = []
    try:
        sources.append(RedditSource())
        log.info("Reddit source enabled")
    except Exception as exc:
        log.warning("Reddit source unavailable: %s", exc)
    try:
        sources.append(AskHNSource())
        log.info("AskHN source enabled")
    except Exception as exc:
        log.warning("AskHN source unavailable: %s", exc)
    return sources


def store_raw_post(post: RawPost) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO raw_posts
                (id, source, subreddit, title, body, upvotes, comments, created_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.id, post.source, post.subreddit, post.title,
                post.body, post.upvotes, post.comments, post.created_at, now_iso(),
            ),
        )


def run_pipeline() -> None:
    start = time.time()
    log.info("=" * 60)
    log.info("Pipeline started")

    init_db()

    sources = get_enabled_sources()
    if not sources:
        log.error("No sources available, aborting")
        return

    llm = LLMService()
    extractor = ProblemExtractor(llm)
    embedder = EmbeddingService()
    clusterer = ClusteringService()
    scorer = ScoringService()

    all_posts: list[RawPost] = []
    for source in sources:
        try:
            posts = source.fetch()
            all_posts.extend(posts)
        except Exception as exc:
            log.error("Source %s failed: %s", source.name, exc)

    log.info("Total posts fetched: %d", len(all_posts))

    new_posts = [p for p in all_posts if not post_exists(p.id)]
    log.info("New posts to process: %d", len(new_posts))

    processed = 0
    errors = 0

    for post in new_posts:
        try:
            store_raw_post(post)

            problem_id = extractor.extract_and_store(post)
            if not problem_id:
                continue

            with get_db() as conn:
                problem = conn.execute(
                    "SELECT problem_summary, target_group FROM problems WHERE id = ?",
                    (problem_id,),
                ).fetchone()

            embedding = embedder.embed_and_store(
                problem_id,
                problem["problem_summary"],
                problem["target_group"] or "",
            )

            clusterer.assign_cluster(problem_id, embedding)

            scorer.score_problem(problem_id)

            processed += 1
            if processed % 10 == 0:
                log.info("Processed %d/%d posts", processed, len(new_posts))

        except Exception as exc:
            errors += 1
            log.error("Error processing post %s: %s", post.id, exc)

    elapsed = time.time() - start
    log.info("Pipeline complete: %d processed, %d errors, %.1fs elapsed", processed, errors, elapsed)
    log.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
