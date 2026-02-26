from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawPost:
    id: str
    source: str
    subreddit: str | None
    title: str
    body: str
    upvotes: int
    comments: int
    created_at: str


class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self) -> list[RawPost]:
        ...
