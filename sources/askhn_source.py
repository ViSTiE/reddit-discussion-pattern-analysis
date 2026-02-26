from datetime import datetime, timezone

import requests

from core.config import config
from core.logger import get_logger
from sources.base_source import BaseSource, RawPost

log = get_logger(__name__)


class AskHNSource(BaseSource):
    name = "askhn"

    def fetch(self) -> list[RawPost]:
        posts: list[RawPost] = []
        try:
            page = 0
            collected = 0
            while collected < config.ASKHN_FETCH_LIMIT:
                resp = requests.get(
                    config.ASKHN_API_URL,
                    params={
                        "tags": "ask_hn",
                        "hitsPerPage": min(50, config.ASKHN_FETCH_LIMIT - collected),
                        "page": page,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("hits", [])
                if not hits:
                    break
                for hit in hits:
                    post = self._parse_hit(hit)
                    if post and post.upvotes >= config.MIN_UPVOTES:
                        posts.append(post)
                collected += len(hits)
                page += 1
        except Exception as exc:
            log.error("AskHN fetch error: %s", exc)

        log.info("AskHN: fetched %d posts", len(posts))
        return posts

    @staticmethod
    def _parse_hit(hit: dict) -> RawPost | None:
        object_id = hit.get("objectID")
        if not object_id:
            return None
        title = hit.get("title") or ""
        if not title:
            return None
        story_text = (hit.get("story_text") or "")[:4000]
        created_at_ts = hit.get("created_at_i")
        if created_at_ts:
            created_at = datetime.fromtimestamp(created_at_ts, tz=timezone.utc).isoformat()
        else:
            created_at = hit.get("created_at", datetime.now(timezone.utc).isoformat())

        return RawPost(
            id=f"askhn_{object_id}",
            source="askhn",
            subreddit=None,
            title=title,
            body=story_text,
            upvotes=hit.get("points") or 0,
            comments=hit.get("num_comments") or 0,
            created_at=created_at,
        )
