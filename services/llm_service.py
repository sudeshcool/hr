"""
llm_service.py  –  Wrapper around OpenAI (or local fallback) for:
  • Structured CV data extraction
  • JD skill/requirement extraction
  • Candidate ranking reasoning generation
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if api_key and api_key != 'your-openai-api-key-here':
            try:
                from openai import OpenAI
                _client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized.")
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}. Using rule-based fallback.")
                _client = 'fallback'
        else:
            logger.info("No OpenAI key – using rule-based extraction fallback.")
            _client = 'fallback'
    return _client


def extract_cv_data(cv_text: str) -> dict:
    """
    Parse a raw CV text and return a structured dict with:
      name, email, phone, current_salary, expected_salary,
      current_city, preferred_cities, notice_period_days,
      education, years_experience, skills
    """
    client = _get_client()

    if client == 'fallback':
        return _rule_based_cv_extract(cv_text)

    prompt = f"""You are an expert HR data extractor. Extract the following fields from the CV text below.
Return ONLY a valid JSON object with these exact keys:
{{
  "name": "",
  "email": "",
  "phone": "",
  "current_salary": null,
  "expected_salary": null,
  "current_city": "",
  "preferred_cities": "",
  "notice_period_days": null,
  "education": "",
  "years_experience": null,
  "skills": ""
}}

Rules:
- salary fields should be annual figures as numbers (no currency symbols)
- notice_period_days should be an integer (e.g. 30, 60, 90)
- years_experience should be a float
- skills should be a comma-separated string of technical/professional skills
- preferred_cities should be a comma-separated string
- If a value is not found, use null for numbers or "" for strings
- Do NOT include any explanation outside the JSON

CV TEXT:
{cv_text[:4000]}
"""
    try:
        response = client.chat.completions.create(
            model=os.environ.get('LLM_MODEL', 'gpt-4o-mini'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"LLM CV extraction failed: {e}")
        return _rule_based_cv_extract(cv_text)


def extract_jd_requirements(jd_text: str) -> dict:
    """Extract structured requirements from a job description."""
    client = _get_client()

    if client == 'fallback':
        return _rule_based_jd_extract(jd_text)

    prompt = f"""Extract the following from this job description. Return ONLY valid JSON:
{{
  "required_skills": "",
  "required_education": "",
  "min_experience_yrs": null,
  "employment_type": ""
}}

Rules:
- required_skills: comma-separated technical + soft skills
- required_education: highest required qualification (e.g. "Bachelor's in CS")
- min_experience_yrs: minimum years experience as a float
- employment_type: "Full-time", "Part-time", "Contract", etc.

JD TEXT:
{jd_text[:3000]}
"""
    try:
        response = client.chat.completions.create(
            model=os.environ.get('LLM_MODEL', 'gpt-4o-mini'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"LLM JD extraction failed: {e}")
        return _rule_based_jd_extract(jd_text)


def generate_ranking_reasoning(job: dict, candidate: dict, scores: dict) -> dict:
    """Generate a human-readable ranking reasoning for a candidate."""
    client = _get_client()

    if client == 'fallback':
        return _rule_based_reasoning(job, candidate, scores)

    prompt = f"""You are a senior HR analyst. Write a concise evaluation for this candidate vs job.
Return ONLY valid JSON with keys: "reasoning", "strengths", "weaknesses"

JOB: {json.dumps(job)}
CANDIDATE: {json.dumps(candidate)}
SCORES: {json.dumps(scores)}

Guidelines:
- reasoning: 2-3 sentences overall suitability assessment
- strengths: 2-3 bullet points (use • separator)
- weaknesses: 1-2 bullet points (use • separator)
"""
    try:
        response = client.chat.completions.create(
            model=os.environ.get('LLM_MODEL', 'gpt-4o-mini'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"LLM reasoning failed: {e}")
        return _rule_based_reasoning(job, candidate, scores)


# ─── Rule-based fallbacks (no LLM required) ──────────────────────────────────

def _rule_based_cv_extract(cv_text: str) -> dict:
    """Simple regex-based extraction when LLM is unavailable."""
    import re

    data = {
        'name': '', 'email': '', 'phone': '',
        'current_salary': None, 'expected_salary': None,
        'current_city': '', 'preferred_cities': '',
        'notice_period_days': None,
        'education': '', 'years_experience': None, 'skills': ''
    }

    # Email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', cv_text)
    if email_match:
        data['email'] = email_match.group()

    # Phone
    phone_match = re.search(r'(\+?\d[\d\s\-().]{8,15}\d)', cv_text)
    if phone_match:
        data['phone'] = phone_match.group().strip()

    # Notice period
    np_match = re.search(r'notice\s+period[:\s]+(\d+)\s*(day|week|month)', cv_text, re.IGNORECASE)
    if np_match:
        val, unit = int(np_match.group(1)), np_match.group(2).lower()
        data['notice_period_days'] = val * (7 if 'week' in unit else 30 if 'month' in unit else 1)

    # Years of experience
    exp_match = re.search(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of)?\s*(experience|exp)', cv_text, re.IGNORECASE)
    if exp_match:
        data['years_experience'] = float(exp_match.group(1))

    return data


def _rule_based_jd_extract(jd_text: str) -> dict:
    import re
    data = {'required_skills': '', 'required_education': '', 'min_experience_yrs': None, 'employment_type': 'Full-time'}
    exp_match = re.search(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of)?\s*(experience|exp)', jd_text, re.IGNORECASE)
    if exp_match:
        data['min_experience_yrs'] = float(exp_match.group(1))
    return data


def _rule_based_reasoning(job: dict, candidate: dict, scores: dict) -> dict:
    total = scores.get('total', 0)
    level = "strong" if total >= 75 else "moderate" if total >= 50 else "weak"
    return {
        "reasoning": f"The candidate shows a {level} match with a total score of {total:.1f}/100. "
                     f"Skills alignment and experience are the primary differentiators.",
        "strengths": "• Profile extracted from CV\n• Candidate meets basic criteria",
        "weaknesses": "• LLM reasoning unavailable – add OpenAI key for detailed analysis"
    }
