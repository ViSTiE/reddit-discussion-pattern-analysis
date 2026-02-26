import numpy as np
from sentence_transformers import SentenceTransformer

from core.config import config
from core.logger import get_logger
from core.utils import get_db, vector_to_blob

log = get_logger(__name__)


class EmbeddingService:
    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        if self._model is None:
            log.info("Loading embedding model: %s", config.EMBEDDING_MODEL)
            self._model = SentenceTransformer(config.EMBEDDING_MODEL)
            log.info("Embedding model loaded")

    def embed(self, text: str) -> np.ndarray:
        self._load_model()
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32)

    def embed_and_store(self, problem_id: int, problem_summary: str, target_group: str) -> np.ndarray:
        text = f"{problem_summary} {target_group}".strip()
        vec = self.embed(text)
        blob = vector_to_blob(vec)
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (problem_id, vector) VALUES (?, ?)",
                (problem_id, blob),
            )
        log.debug("Stored embedding for problem %d", problem_id)
        return vec
