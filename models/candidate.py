from extensions import db
from datetime import datetime


class Candidate(db.Model):
    __tablename__ = 'candidates'

    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(200), nullable=False)
    email               = db.Column(db.String(200), unique=True, nullable=False)
    phone               = db.Column(db.String(50))
    cv_file_path        = db.Column(db.String(500))
    cv_text             = db.Column(db.Text)

    # ─── Constraint fields (from CV or manually entered) ─────────────────────
    current_salary      = db.Column(db.Float)          # Annual, in same currency as JD
    expected_salary     = db.Column(db.Float)
    current_city        = db.Column(db.String(200))
    preferred_cities    = db.Column(db.String(500))    # comma-separated
    notice_period_days  = db.Column(db.Integer)
    education           = db.Column(db.String(300))    # Highest qualification
    years_experience    = db.Column(db.Float)
    skills              = db.Column(db.Text)           # comma-separated

    # ─── Source tracking ─────────────────────────────────────────────────────
    data_source         = db.Column(db.String(50), default='cv')   # 'cv' | 'manual' | 'mixed'
    info_complete       = db.Column(db.Boolean, default=False)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scores  = db.relationship('CandidateJobScore', backref='candidate', lazy=True, cascade='all, delete-orphan')
    flags   = db.relationship('MissingInfoFlag',   backref='candidate', lazy=True, cascade='all, delete-orphan')

    def skills_list(self):
        return [s.strip() for s in (self.skills or '').split(',') if s.strip()]

    def preferred_cities_list(self):
        return [c.strip() for c in (self.preferred_cities or '').split(',') if c.strip()]

    def __repr__(self):
        return f'<Candidate {self.id}: {self.name}>'
