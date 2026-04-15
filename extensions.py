"""extensions.py – Shared Flask extensions to avoid circular imports."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
