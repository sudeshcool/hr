"""routes/job_routes.py – CRUD routes for Job Descriptions."""
import os
import io
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.job import Job
from services import llm_service, vector_service

job_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@job_bp.route('/')
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('jobs/list.html', jobs=jobs)


@job_bp.route('/new', methods=['GET', 'POST'])
def new_job():
    if request.method == 'POST':
        f = request.form
        jd_text = f.get('jd_text', '').strip()

        # Auto-extract requirements from JD using LLM
        extracted = llm_service.extract_jd_requirements(jd_text)

        job = Job(
            client_name        = f.get('client_name', '').strip(),
            job_title          = f.get('job_title', '').strip(),
            jd_text            = jd_text,
            required_skills    = f.get('required_skills') or extracted.get('required_skills', ''),
            required_education = f.get('required_education') or extracted.get('required_education', ''),
            min_experience_yrs = _float(f.get('min_experience_yrs')) or extracted.get('min_experience_yrs'),
            salary_min         = _float(f.get('salary_min')),
            salary_max         = _float(f.get('salary_max')),
            city               = f.get('city', '').strip(),
            notice_period_days = _int(f.get('notice_period_days')),
            employment_type    = f.get('employment_type', 'Full-time'),
            remote_ok          = f.get('remote_ok') == 'on',
        )
        db.session.add(job)
        db.session.commit()

        # Index into vector DB
        vector_service.index_job(job.id, jd_text)

        flash(f'Job "{job.job_title}" created successfully!', 'success')
        return redirect(url_for('jobs.view_job', job_id=job.id))

    return render_template('jobs/form.html', job=None)


@job_bp.route('/<int:job_id>')
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('jobs/detail.html', job=job)


@job_bp.route('/<int:job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        f = request.form
        job.client_name        = f.get('client_name', '').strip()
        job.job_title          = f.get('job_title', '').strip()
        job.jd_text            = f.get('jd_text', '').strip()
        job.required_skills    = f.get('required_skills', '')
        job.required_education = f.get('required_education', '')
        job.min_experience_yrs = _float(f.get('min_experience_yrs'))
        job.salary_min         = _float(f.get('salary_min'))
        job.salary_max         = _float(f.get('salary_max'))
        job.city               = f.get('city', '').strip()
        job.notice_period_days = _int(f.get('notice_period_days'))
        job.employment_type    = f.get('employment_type', 'Full-time')
        job.remote_ok          = f.get('remote_ok') == 'on'
        db.session.commit()
        vector_service.index_job(job.id, job.jd_text)
        flash('Job updated successfully!', 'success')
        return redirect(url_for('jobs.view_job', job_id=job.id))
    return render_template('jobs/form.html', job=job)


@job_bp.route('/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted.', 'info')
    return redirect(url_for('jobs.list_jobs'))


# ─── helpers ─────────────────────────────────────────────────────────────────
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
