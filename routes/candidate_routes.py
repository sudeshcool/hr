"""routes/candidate_routes.py – CV upload, parsing, and candidate management."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from extensions import db
from models.candidate import Candidate
from services import cv_parser, llm_service, vector_service

candidate_bp = Blueprint('candidates', __name__, url_prefix='/candidates')

ALLOWED = {'pdf', 'docx', 'doc'}


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@candidate_bp.route('/')
def list_candidates():
    candidates = Candidate.query.order_by(Candidate.created_at.desc()).all()
    return render_template('candidates/list.html', candidates=candidates)


@candidate_bp.route('/upload', methods=['GET', 'POST'])
def upload_cv():
    if request.method == 'POST':
        files = request.files.getlist('cv_files')
        success_count = 0
        for file in files:
            if file and _allowed(file.filename):
                filename = secure_filename(file.filename)
                upload_dir = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)

                # Extract text
                cv_text = cv_parser.extract_text(filepath)

                # LLM structured extraction
                data = llm_service.extract_cv_data(cv_text)

                # Check for existing candidate (by email)
                existing = None
                if data.get('email'):
                    existing = Candidate.query.filter_by(email=data['email']).first()

                if existing:
                    # Update existing candidate
                    _update_candidate(existing, data, cv_text, filepath)
                else:
                    candidate = Candidate(
                        name             = data.get('name') or filename.replace('_', ' ').replace('.pdf', '').replace('.docx', ''),
                        email            = data.get('email') or f"unknown_{filename}@temp.com",
                        phone            = data.get('phone', ''),
                        cv_file_path     = filepath,
                        cv_text          = cv_text,
                        current_salary   = data.get('current_salary'),
                        expected_salary  = data.get('expected_salary'),
                        current_city     = data.get('current_city', ''),
                        preferred_cities = data.get('preferred_cities', ''),
                        notice_period_days = data.get('notice_period_days'),
                        education        = data.get('education', ''),
                        years_experience = data.get('years_experience'),
                        skills           = data.get('skills', ''),
                        data_source      = 'cv',
                    )
                    db.session.add(candidate)
                    db.session.flush()
                    vector_service.index_candidate(candidate.id, cv_text)
                    success_count += 1

        db.session.commit()
        flash(f'{success_count} CV(s) processed successfully!', 'success')
        return redirect(url_for('candidates.list_candidates'))

    return render_template('candidates/upload.html')


@candidate_bp.route('/<int:candidate_id>')
def view_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    return render_template('candidates/detail.html', candidate=candidate)


@candidate_bp.route('/<int:candidate_id>/edit', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    if request.method == 'POST':
        f = request.form
        candidate.name              = f.get('name', candidate.name)
        candidate.email             = f.get('email', candidate.email)
        candidate.phone             = f.get('phone', candidate.phone)
        candidate.current_salary    = _float(f.get('current_salary'))
        candidate.expected_salary   = _float(f.get('expected_salary'))
        candidate.current_city      = f.get('current_city', '')
        candidate.preferred_cities  = f.get('preferred_cities', '')
        candidate.notice_period_days = _int(f.get('notice_period_days'))
        candidate.education         = f.get('education', '')
        candidate.years_experience  = _float(f.get('years_experience'))
        candidate.skills            = f.get('skills', '')
        candidate.data_source       = 'mixed' if candidate.data_source == 'cv' else candidate.data_source
        db.session.commit()
        flash('Candidate updated.', 'success')
        return redirect(url_for('candidates.view_candidate', candidate_id=candidate.id))
    return render_template('candidates/edit.html', candidate=candidate)


@candidate_bp.route('/<int:candidate_id>/delete', methods=['POST'])
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate deleted.', 'info')
    return redirect(url_for('candidates.list_candidates'))


# ─── manual add ──────────────────────────────────────────────────────────────
@candidate_bp.route('/new', methods=['GET', 'POST'])
def new_candidate():
    if request.method == 'POST':
        f = request.form
        candidate = Candidate(
            name             = f.get('name', '').strip(),
            email            = f.get('email', '').strip(),
            phone            = f.get('phone', ''),
            current_salary   = _float(f.get('current_salary')),
            expected_salary  = _float(f.get('expected_salary')),
            current_city     = f.get('current_city', ''),
            preferred_cities = f.get('preferred_cities', ''),
            notice_period_days = _int(f.get('notice_period_days')),
            education        = f.get('education', ''),
            years_experience = _float(f.get('years_experience')),
            skills           = f.get('skills', ''),
            data_source      = 'manual',
        )
        db.session.add(candidate)
        db.session.commit()
        flash('Candidate added.', 'success')
        return redirect(url_for('candidates.list_candidates'))
    return render_template('candidates/edit.html', candidate=None)


def _update_candidate(c, data, cv_text, filepath):
    if data.get('phone'):    c.phone = data['phone']
    c.cv_file_path   = filepath
    c.cv_text        = cv_text
    if data.get('current_salary'):    c.current_salary = data['current_salary']
    if data.get('expected_salary'):   c.expected_salary = data['expected_salary']
    if data.get('current_city'):      c.current_city = data['current_city']
    if data.get('preferred_cities'):  c.preferred_cities = data['preferred_cities']
    if data.get('notice_period_days'): c.notice_period_days = data['notice_period_days']
    if data.get('education'):         c.education = data['education']
    if data.get('years_experience'):  c.years_experience = data['years_experience']
    if data.get('skills'):            c.skills = data['skills']
    c.data_source = 'cv'
    vector_service.index_candidate(c.id, cv_text)


def _float(v):
    try:
        return float(v) if v else None
    except (ValueError, TypeError):
        return None

def _int(v):
    try:
        return int(v) if v else None
    except (ValueError, TypeError):
        return None
