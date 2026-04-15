"""
ranking_engine.py  –  Compute weighted scores for each candidate against a job.
"""
import json
import logging
from typing import List

from models.candidate import Candidate
from models.job import Job
from models.ranking import CandidateJobScore, MissingInfoFlag
from services import llm_service, vector_service
from extensions import db

logger = logging.getLogger(__name__)

# Default weights (overridden by app config)
DEFAULT_WEIGHTS = {
    'skills':     0.30,
    'experience': 0.25,
    'education':  0.15,
    'salary':     0.15,
    'location':   0.10,
    'notice':     0.05,
}

EDUCATION_LEVELS = {
    'phd': 6, 'doctorate': 6,
    'master': 5, 'mba': 5, 'msc': 5, 'me': 5, 'mtech': 5,
    'bachelor': 4, 'be': 4, 'btech': 4, 'bsc': 4, 'ba': 4,
    'diploma': 3,
    'high school': 2, 'hsc': 2, 'ssc': 1,
}

def _serialize_list_field(value):
    """
    Serialize a field that might be a list or string to a JSON string.
    Handles both list inputs from LLM and string inputs from fallback.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, str):
        return value
    return str(value)


def _edu_level(text: str) -> int:
    """Return numeric education level from a string."""
    if not text:
        return 0
    t = text.lower()
    for key, val in EDUCATION_LEVELS.items():
        if key in t:
            return val
    return 2  # default to diploma level if unknown


def _score_skills(job: Job, candidate: Candidate) -> float:
    """Jaccard-style overlap between required and candidate skills."""
    required = set(s.lower() for s in job.skills_list())
    have = set(s.lower() for s in candidate.skills_list())
    if not required:
        return 70.0
    overlap = len(required & have)
    return round(min((overlap / len(required)) * 100, 100), 2)


def _score_experience(job: Job, candidate: Candidate) -> float:
    req = job.min_experience_yrs or 0
    have = candidate.years_experience or 0
    if req == 0:
        return 80.0
    if have >= req * 1.5:
        return 100.0
    if have >= req:
        return 85.0
    ratio = have / req
    return round(ratio * 80, 2)


def _score_education(job: Job, candidate: Candidate) -> float:
    req_level = _edu_level(job.required_education or '')
    cand_level = _edu_level(candidate.education or '')
    if req_level == 0:
        return 75.0
    if cand_level >= req_level:
        return 100.0
    diff = req_level - cand_level
    return max(0, round(100 - diff * 20, 2))


def _score_salary(job: Job, candidate: Candidate) -> float:
    sal_min = job.salary_min
    sal_max = job.salary_max
    expected = candidate.expected_salary

    if not expected:
        return 60.0   # unknown → neutral
    if not sal_min and not sal_max:
        return 70.0   # job has no salary range defined

    sal_max = sal_max or (sal_min * 1.3 if sal_min else None)
    sal_min = sal_min or 0

    if expected <= sal_max:
        if expected >= sal_min:
            return 100.0
        # Candidate asks less than min – good for company but may leave soon
        return 85.0
    # Candidate asks more than max
    overshoot = (expected - sal_max) / sal_max
    return max(0, round(100 - overshoot * 100, 2))


def _score_location(job: Job, candidate: Candidate) -> float:
    if not job.city:
        return 80.0
    job_city = job.city.lower().strip()
    current = (candidate.current_city or '').lower().strip()
    preferred = [c.lower().strip() for c in candidate.preferred_cities_list()]
    remote_ok = job.remote_ok

    if current == job_city:
        return 100.0
    if job_city in preferred:
        return 90.0
    if remote_ok:
        return 80.0
    # Different city, not willing to relocate (implicit)
    return 40.0


def _score_notice(job: Job, candidate: Candidate) -> float:
    req = job.notice_period_days
    have = candidate.notice_period_days

    if not req:
        return 80.0
    if not have:
        return 60.0
    if have <= req:
        return 100.0
    overshoot_days = have - req
    # Penalise 2 pts per extra day, max 80 pt deduction
    return max(20.0, round(100 - overshoot_days * 2, 2))


def _detect_missing(job: Job, candidate: Candidate) -> List[str]:
    """Return list of field names that are needed but missing."""
    missing = []
    if job.salary_min or job.salary_max:
        if candidate.expected_salary is None:
            missing.append('expected_salary')
    if job.city and not candidate.current_city:
        missing.append('current_city')
    if job.city and not candidate.preferred_cities:
        missing.append('preferred_cities')
    if job.notice_period_days and candidate.notice_period_days is None:
        missing.append('notice_period_days')
    return missing


def rank_candidates(job: Job, candidates: List[Candidate], weights: dict = None) -> List[CandidateJobScore]:
    """
    Score all candidates against the job and persist results.
    Returns sorted list of CandidateJobScore objects.
    """
    w = weights or DEFAULT_WEIGHTS

    results = []
    for candidate in candidates:
        # Detect missing info and log flags
        missing = _detect_missing(job, candidate)
        if missing:
            existing_flag = MissingInfoFlag.query.filter_by(
                candidate_id=candidate.id, job_id=job.id
            ).first()
            if not existing_flag:
                flag = MissingInfoFlag(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    missing_fields=json.dumps(missing),
                    status='pending'
                )
                db.session.add(flag)

        # Calculate dimension scores
        skills_s  = _score_skills(job, candidate)
        exp_s     = _score_experience(job, candidate)
        edu_s     = _score_education(job, candidate)
        sal_s     = _score_salary(job, candidate)
        loc_s     = _score_location(job, candidate)
        notice_s  = _score_notice(job, candidate)

        # Semantic similarity from vector DB
        sem_s = 50.0
        if candidate.cv_text and job.jd_text:
            sem_s = vector_service.semantic_score(job.id, candidate.id, job.jd_text, candidate.cv_text)

        # Weighted total
        total = (
            skills_s  * w.get('skills', 0.30) +
            exp_s     * w.get('experience', 0.25) +
            edu_s     * w.get('education', 0.15) +
            sal_s     * w.get('salary', 0.15) +
            loc_s     * w.get('location', 0.10) +
            notice_s  * w.get('notice', 0.05)
        )
        total = round(total, 2)

        # Generate reasoning
        job_dict = {
            'title': job.job_title, 'skills': job.required_skills,
            'min_exp': job.min_experience_yrs, 'city': job.city,
            'salary_max': job.salary_max, 'notice_days': job.notice_period_days,
        }
        cand_dict = {
            'name': candidate.name, 'skills': candidate.skills,
            'experience': candidate.years_experience, 'city': candidate.current_city,
            'expected_salary': candidate.expected_salary, 'notice_days': candidate.notice_period_days,
            'education': candidate.education,
        }
        score_dict = {
            'skills': skills_s, 'experience': exp_s, 'education': edu_s,
            'salary': sal_s, 'location': loc_s, 'notice': notice_s, 'total': total
        }
        reasoning = llm_service.generate_ranking_reasoning(job_dict, cand_dict, score_dict)

        # Upsert score row
        score_row = CandidateJobScore.query.filter_by(
            candidate_id=candidate.id, job_id=job.id
        ).first()
        if not score_row:
            score_row = CandidateJobScore(candidate_id=candidate.id, job_id=job.id)
            db.session.add(score_row)

        score_row.skills_score       = skills_s
        score_row.experience_score   = exp_s
        score_row.education_score    = edu_s
        score_row.salary_score       = sal_s
        score_row.location_score     = loc_s
        score_row.notice_score       = notice_s
        score_row.semantic_score     = sem_s
        score_row.total_weighted_score = total
        score_row.reasoning          = reasoning.get('reasoning', '')
        score_row.strengths          = _serialize_list_field(reasoning.get('strengths', ''))
        score_row.weaknesses         = _serialize_list_field(reasoning.get('weaknesses', ''))

        results.append(score_row)

    # Sort and assign ranks
    results.sort(key=lambda x: x.total_weighted_score, reverse=True)
    for rank, score_row in enumerate(results, start=1):
        score_row.rank = rank

    db.session.commit()
    return results
