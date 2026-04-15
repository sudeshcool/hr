from extensions import db
from datetime import datetime
import json


class CandidateJobScore(db.Model):
    __tablename__ = 'candidate_job_scores'

    id                  = db.Column(db.Integer, primary_key=True)
    candidate_id        = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    job_id              = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)

    # ─── Individual dimension scores (0–100) ─────────────────────────────────
    skills_score        = db.Column(db.Float, default=0)
    experience_score    = db.Column(db.Float, default=0)
    education_score     = db.Column(db.Float, default=0)
    salary_score        = db.Column(db.Float, default=0)
    location_score      = db.Column(db.Float, default=0)
    notice_score        = db.Column(db.Float, default=0)
    semantic_score      = db.Column(db.Float, default=0)   # vector similarity

    # ─── Final weighted score ─────────────────────────────────────────────────
    total_weighted_score = db.Column(db.Float, default=0)
    rank                = db.Column(db.Integer)

    # ─── LLM-generated reasoning ─────────────────────────────────────────────
    reasoning           = db.Column(db.Text)
    strengths           = db.Column(db.Text)
    weaknesses          = db.Column(db.Text)

    scored_at           = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('candidate_id', 'job_id', name='_candidate_job_uc'),)

    def score_breakdown(self):
        return {
            'Skills Match':         round(self.skills_score, 1),
            'Experience':           round(self.experience_score, 1),
            'Education':            round(self.education_score, 1),
            'Salary Fit':           round(self.salary_score, 1),
            'Location':             round(self.location_score, 1),
            'Notice Period':        round(self.notice_score, 1),
        }
    
    def get_strengths_list(self):
        """Deserialize strengths from JSON string to list."""
        if not self.strengths:
            return []
        try:
            # If it's already a list (from JSON), return it
            parsed = json.loads(self.strengths)
            if isinstance(parsed, list):
                return parsed
            # If it's a string, split by bullet points or newlines
            return [s.strip() for s in str(parsed).split('\n') if s.strip()]
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as plain text and split by newlines or bullet points
            if isinstance(self.strengths, str):
                return [s.strip() for s in self.strengths.split('\n') if s.strip()]
            return []
    
    def get_weaknesses_list(self):
        """Deserialize weaknesses from JSON string to list."""
        if not self.weaknesses:
            return []
        try:
            # If it's already a list (from JSON), return it
            parsed = json.loads(self.weaknesses)
            if isinstance(parsed, list):
                return parsed
            # If it's a string, split by bullet points or newlines
            return [s.strip() for s in str(parsed).split('\n') if s.strip()]
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as plain text and split by newlines or bullet points
            if isinstance(self.weaknesses, str):
                return [s.strip() for s in self.weaknesses.split('\n') if s.strip()]
            return []


class MissingInfoFlag(db.Model):
    __tablename__ = 'missing_info_flags'

    id              = db.Column(db.Integer, primary_key=True)
    candidate_id    = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    job_id          = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    missing_fields  = db.Column(db.Text)    # JSON list of field names
    status          = db.Column(db.String(50), default='pending')  # pending | filled | skipped
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
