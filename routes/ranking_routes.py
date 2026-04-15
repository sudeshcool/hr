"""routes/ranking_routes.py – Trigger ranking engine, view results, export CSV."""
import csv
import io
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from extensions import db
from models.job import Job
from models.candidate import Candidate
from models.ranking import CandidateJobScore, MissingInfoFlag
from services import ranking_engine

ranking_bp = Blueprint('ranking', __name__, url_prefix='/ranking')


@ranking_bp.route('/<int:job_id>')
def rank_for_job(job_id):
    job = Job.query.get_or_404(job_id)
    candidates = Candidate.query.all()
    scores = (
        CandidateJobScore.query
        .filter_by(job_id=job_id)
        .order_by(CandidateJobScore.rank)
        .all()
    )
    flags = MissingInfoFlag.query.filter_by(job_id=job_id, status='pending').all()
    return render_template('ranking/results.html', job=job, scores=scores, flags=flags,
                           candidate_count=len(candidates))


@ranking_bp.route('/<int:job_id>/run', methods=['POST'])
def run_ranking(job_id):
    job = Job.query.get_or_404(job_id)
    candidates = Candidate.query.all()
    if not candidates:
        flash('No candidates found. Upload CVs first.', 'warning')
        return redirect(url_for('ranking.rank_for_job', job_id=job_id))

    weights = current_app.config.get('SCORING_WEIGHTS', ranking_engine.DEFAULT_WEIGHTS)
    ranking_engine.rank_candidates(job, candidates, weights)
    flash(f'Ranking complete! {len(candidates)} candidates scored.', 'success')
    return redirect(url_for('ranking.rank_for_job', job_id=job_id))


@ranking_bp.route('/<int:job_id>/export/csv')
def export_csv(job_id):
    job = Job.query.get_or_404(job_id)
    scores = (
        CandidateJobScore.query
        .filter_by(job_id=job_id)
        .order_by(CandidateJobScore.rank)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Rank', 'Candidate Name', 'Email', 'Phone',
        'Skills Score', 'Experience Score', 'Education Score',
        'Salary Score', 'Location Score', 'Notice Score',
        'Total Score', 'Reasoning', 'Strengths', 'Weaknesses',
        'Current City', 'Expected Salary (Annual)', 'Notice Period (Days)', 'Education'
    ])
    for s in scores:
        c = s.candidate
        # Convert strengths/weaknesses lists to readable strings for CSV
        strengths_text = '; '.join(s.get_strengths_list()) if s.strengths else ''
        weaknesses_text = '; '.join(s.get_weaknesses_list()) if s.weaknesses else ''
        
        writer.writerow([
            s.rank, c.name, c.email, c.phone or '',
            s.skills_score, s.experience_score, s.education_score,
            s.salary_score, s.location_score, s.notice_score,
            s.total_weighted_score,
            s.reasoning or '', strengths_text, weaknesses_text,
            c.current_city or '', c.expected_salary or '', c.notice_period_days or '', c.education or ''
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=ranking_{job_id}_{job.job_title.replace(" ", "_")}.csv'}
    )


@ranking_bp.route('/missing/<int:flag_id>/fill', methods=['GET', 'POST'])
def fill_missing(flag_id):
    flag = MissingInfoFlag.query.get_or_404(flag_id)
    candidate = flag.candidate
    missing_fields = json.loads(flag.missing_fields or '[]')

    if request.method == 'POST':
        f = request.form
        if 'expected_salary' in missing_fields and f.get('expected_salary'):
            candidate.expected_salary = float(f['expected_salary'])
        if 'current_city' in missing_fields and f.get('current_city'):
            candidate.current_city = f['current_city']
        if 'preferred_cities' in missing_fields and f.get('preferred_cities'):
            candidate.preferred_cities = f['preferred_cities']
        if 'notice_period_days' in missing_fields and f.get('notice_period_days'):
            candidate.notice_period_days = int(f['notice_period_days'])
        candidate.data_source = 'mixed'
        flag.status = 'filled'
        db.session.commit()
        flash(f'Missing info filled for {candidate.name}.', 'success')
        return redirect(url_for('ranking.rank_for_job', job_id=flag.job_id))

    return render_template('ranking/fill_missing.html', flag=flag, candidate=candidate,
                           missing_fields=missing_fields, job=flag.job)
