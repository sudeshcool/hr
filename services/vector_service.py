"""
vector_service.py  –  Embed JDs and CVs into ChromaDB for semantic similarity search.
Falls back to TF-IDF cosine similarity if ChromaDB is unavailable.
"""
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

_chroma_client = None
_collection = None
_local_model = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        from chromadb.config import Settings
        path = os.environ.get('CHROMA_DB_PATH', 'data/chromadb')
        os.makedirs(path, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=path)
        _collection = _chroma_client.get_or_create_collection(
            name="hr_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("ChromaDB collection ready.")
        return _collection
    except Exception as e:
        logger.warning(f"ChromaDB unavailable: {e}. Will use TF-IDF fallback.")
        return None


def _embed(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI or local sentence-transformers."""
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if api_key and api_key != 'your-openai-api-key-here':
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                input=texts,
                model=os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}. Trying local model.")

    # Local fallback
    global _local_model
    try:
        from sentence_transformers import SentenceTransformer
        if _local_model is None:
            _local_model = SentenceTransformer('all-MiniLM-L6-v2')
        return _local_model.encode(texts).tolist()
    except Exception as e:
        logger.warning(f"Local embedding failed: {e}")
        return [[0.0] * 384] * len(texts)


def index_job(job_id: int, jd_text: str):
    """Embed and store a JD in ChromaDB."""
    collection = _get_collection()
    if collection is None:
        return
    try:
        embeddings = _embed([jd_text[:2000]])
        collection.upsert(
            ids=[f"job_{job_id}"],
            embeddings=embeddings,
            documents=[jd_text[:2000]],
            metadatas=[{"type": "job", "job_id": job_id}]
        )
    except Exception as e:
        logger.error(f"index_job failed: {e}")


def index_candidate(candidate_id: int, cv_text: str):
    """Embed and store a candidate CV in ChromaDB."""
    collection = _get_collection()
    if collection is None:
        return
    try:
        embeddings = _embed([cv_text[:2000]])
        collection.upsert(
            ids=[f"candidate_{candidate_id}"],
            embeddings=embeddings,
            documents=[cv_text[:2000]],
            metadatas=[{"type": "candidate", "candidate_id": candidate_id}]
        )
    except Exception as e:
        logger.error(f"index_candidate failed: {e}")


def semantic_score(job_id: int, candidate_id: int, jd_text: str, cv_text: str) -> float:
    """
    Return cosine similarity score (0-100) between a JD and a candidate CV.
    Uses ChromaDB if available, else falls back to TF-IDF.
    """
    collection = _get_collection()
    if collection:
        try:
            # Query the JD embedding against the candidate
            embeddings = _embed([jd_text[:2000]])
            results = collection.query(
                query_embeddings=embeddings,
                n_results=1,
                where={"candidate_id": candidate_id},
                include=["distances"]
            )
            if results and results['distances'] and results['distances'][0]:
                cosine_dist = results['distances'][0][0]
                return round((1 - cosine_dist) * 100, 2)
        except Exception as e:
            logger.warning(f"ChromaDB query failed: {e}")

    # TF-IDF fallback
    return _tfidf_similarity(jd_text, cv_text)


def _tfidf_similarity(text1: str, text2: str) -> float:
    """Simple TF-IDF cosine similarity fallback."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vect = TfidfVectorizer(stop_words='english')
        tfidf = vect.fit_transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(score * 100, 2)
    except Exception:
        return 50.0  # neutral fallback
