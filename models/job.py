from extensions import db
from datetime import datetime


class Job(db.Model):
    __tablename__ = 'jobs'

    id                  = db.Column(db.Integer, primary_key=True)
    client_name         = db.Column(db.String(200), nullable=False)
    job_title           = db.Column(db.String(200), nullable=False)
    jd_text             = db.Column(db.Text, nullable=False)
    required_skills     = db.Column(db.Text)           # comma-separated
    required_education  = db.Column(db.String(200))
    min_experience_yrs  = db.Column(db.Float, default=0)
    salary_min          = db.Column(db.Float)
    salary_max          = db.Column(db.Float)
    city                = db.Column(db.String(200))
    notice_period_days  = db.Column(db.Integer)
    employment_type     = db.Column(db.String(100))    # Full-time / Contract
    remote_ok           = db.Column(db.Boolean, default=False)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    is_active           = db.Column(db.Boolean, default=True)

    scores   = db.relationship('CandidateJobScore', backref='job', lazy=True, cascade='all, delete-orphan')
    flags    = db.relationship('MissingInfoFlag',   backref='job', lazy=True, cascade='all, delete-orphan')

    def skills_list(self):
        return [s.strip() for s in (self.required_skills or '').split(',') if s.strip()]

    def __repr__(self):
        return f'<Job {self.id}: {self.job_title} @ {self.client_name}>'
