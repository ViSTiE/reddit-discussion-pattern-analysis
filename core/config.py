import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    BASE_DIR: Path = BASE_DIR
    DB_PATH: Path = BASE_DIR / "data" / "app.db"
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_FILE: Path = LOG_DIR / "pipeline.log"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TIMEOUT: int = 60
    OPENAI_MAX_RETRIES: int = 5

    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_SECRET: str = os.getenv("REDDIT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "business_idea_hunter/1.0")
    REDDIT_SUBREDDITS: list[str] = [
        s.strip()
        for s in os.getenv("REDDIT_SUBREDDITS", "SaaS,startups,Entrepreneur,smallbusiness,indiehackers").split(",")
    ]
    REDDIT_FETCH_LIMIT: int = 100

    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    MIN_UPVOTES: int = int(os.getenv("MIN_UPVOTES", "5"))

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    ASKHN_API_URL: str = "https://hn.algolia.com/api/v1/search_by_date"
    ASKHN_FETCH_LIMIT: int = 100

    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))


config = Config()
