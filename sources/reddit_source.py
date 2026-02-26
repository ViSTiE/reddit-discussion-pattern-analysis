from datetime import datetime, timezone

import praw

from core.config import config
from core.logger import get_logger
from sources.base_source import BaseSource, RawPost

log = get_logger(__name__)


class RedditSource(BaseSource):
    name = "reddit"

    def __init__(self) -> None:
        self._reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
        )

    def fetch(self) -> list[RawPost]:
        posts: list[RawPost] = []
        for sub_name in config.REDDIT_SUBREDDITS:
            try:
                posts.extend(self._fetch_subreddit(sub_name))
            except Exception as exc:
                log.error("Failed to fetch r/%s: %s", sub_name, exc)
        log.info("Reddit: fetched %d posts total", len(posts))
        return posts

    def _fetch_subreddit(self, sub_name: str) -> list[RawPost]:
        subreddit = self._reddit.subreddit(sub_name)
        results: list[RawPost] = []
        for submission in subreddit.new(limit=config.REDDIT_FETCH_LIMIT):
            if submission.score < config.MIN_UPVOTES:
                continue
            body = (submission.selftext or "")[:4000]
            post = RawPost(
                id=f"reddit_{submission.id}",
                source="reddit",
                subreddit=sub_name,
                title=submission.title,
                body=body,
                upvotes=submission.score,
                comments=submission.num_comments,
                created_at=datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                ).isoformat(),
            )
            results.append(post)
        log.info("Reddit: r/%s → %d posts (min upvotes: %d)", sub_name, len(results), config.MIN_UPVOTES)
        return results
