import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hr.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Use /tmp for Cloud Run compatibility (ephemeral storage)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    CHROMA_DB_PATH = os.environ.get('CHROMA_DB_PATH', '/tmp/chromadb')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

    # ─── Scoring Weights (must sum to 1.0) ───────────────────────────────────
    SCORING_WEIGHTS = {
        'skills':       0.30,
        'experience':   0.25,
        'education':    0.15,
        'salary':       0.15,
        'location':     0.10,
        'notice':       0.05,
    }

    # ─── LLM Model ────────────────────────────────────────────────────────────
    LLM_MODEL = 'gpt-4o-mini'            # change to 'gpt-4o' for better accuracy
    EMBEDDING_MODEL = 'text-embedding-3-small'

    # ─── Use local embeddings if no OpenAI key ────────────────────────────────
    USE_LOCAL_EMBEDDINGS = True           # fallback to sentence-transformers
    LOCAL_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
