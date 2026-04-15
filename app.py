"""app.py – Flask application factory and entry point."""
import os
from flask import Flask, render_template
from config import Config
from extensions import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload and data directories exist (use /tmp for Cloud Run)
    upload_folder = app.config['UPLOAD_FOLDER']
    chroma_path = app.config['CHROMA_DB_PATH']
    
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(chroma_path, exist_ok=True)
    
    # Ensure database directory exists
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Init extensions
    db.init_app(app)

    # Register blueprints
    from routes.job_routes import job_bp
    from routes.candidate_routes import candidate_bp
    from routes.ranking_routes import ranking_bp

    app.register_blueprint(job_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(ranking_bp)

    # Dashboard
    @app.route('/')
    def index():
        from models.job import Job
        from models.candidate import Candidate
        from models.ranking import CandidateJobScore, MissingInfoFlag
        jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
        total_jobs = Job.query.count()
        total_candidates = Candidate.query.count()
        total_scores = CandidateJobScore.query.count()
        pending_flags = MissingInfoFlag.query.filter_by(status='pending').count()
        recent_scores = (
            CandidateJobScore.query
            .order_by(CandidateJobScore.scored_at.desc())
            .limit(10)
            .all()
        )
        return render_template('dashboard.html',
                               jobs=jobs,
                               total_jobs=total_jobs,
                               total_candidates=total_candidates,
                               total_scores=total_scores,
                               pending_flags=pending_flags,
                               recent_scores=recent_scores)

    # Create tables
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8080)
