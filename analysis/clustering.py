import numpy as np

from core.config import config
from core.logger import get_logger
from core.utils import get_db, vector_to_blob, blob_to_vector, now_iso

log = get_logger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class ClusteringService:
    def __init__(self, threshold: float | None = None) -> None:
        self._threshold = threshold or config.SIMILARITY_THRESHOLD

    def assign_cluster(self, problem_id: int, embedding: np.ndarray) -> int:
        clusters = self._load_clusters()

        best_cluster_id: int | None = None
        best_similarity: float = -1.0

        for cluster_id, centroid, size in clusters:
            sim = cosine_similarity(embedding, centroid)
            if sim >= self._threshold and sim > best_similarity:
                best_similarity = sim
                best_cluster_id = cluster_id

        if best_cluster_id is not None:
            self._add_to_cluster(best_cluster_id, problem_id, embedding)
            log.debug("Problem %d → cluster %d (sim=%.3f)", problem_id, best_cluster_id, best_similarity)
            return best_cluster_id
        else:
            new_id = self._create_cluster(problem_id, embedding)
            log.debug("Problem %d → new cluster %d", problem_id, new_id)
            return new_id

    @staticmethod
    def _load_clusters() -> list[tuple[int, np.ndarray, int]]:
        with get_db() as conn:
            rows = conn.execute("SELECT id, centroid, size FROM clusters").fetchall()
        return [(row["id"], blob_to_vector(row["centroid"]), row["size"]) for row in rows]

    @staticmethod
    def _create_cluster(problem_id: int, embedding: np.ndarray) -> int:
        now = now_iso()
        blob = vector_to_blob(embedding)
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO clusters (centroid, size, created_at, updated_at) VALUES (?, 1, ?, ?)",
                (blob, now, now),
            )
            cluster_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO problem_clusters (problem_id, cluster_id) VALUES (?, ?)",
                (problem_id, cluster_id),
            )
        return cluster_id

    @staticmethod
    def _add_to_cluster(cluster_id: int, problem_id: int, embedding: np.ndarray) -> None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT centroid, size FROM clusters WHERE id = ?", (cluster_id,)
            ).fetchone()
            old_centroid = blob_to_vector(row["centroid"])
            old_size = row["size"]

            new_size = old_size + 1
            new_centroid = (old_centroid * old_size + embedding) / new_size
            new_centroid = new_centroid / (np.linalg.norm(new_centroid) + 1e-10)

            conn.execute(
                "UPDATE clusters SET centroid = ?, size = ?, updated_at = ? WHERE id = ?",
                (vector_to_blob(new_centroid.astype(np.float32)), new_size, now_iso(), cluster_id),
            )
            conn.execute(
                "INSERT INTO problem_clusters (problem_id, cluster_id) VALUES (?, ?)",
                (problem_id, cluster_id),
            )
