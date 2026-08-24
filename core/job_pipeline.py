"""UMAY Job Search + CV Adaptation Pipeline.

Workflow:
1. User profile / CV
2. Job search (web_search + browser)
3. Job listing analysis
4. Match scoring
5. Missing skills identification
6. CV adaptation
7. Cover letter generation
8. User approval before any action
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.utils.logger import log

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class JobListing:
    """Parsed job listing."""
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    experience: str = ""
    skills: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    preferred: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    education: str = ""
    work_type: str = ""
    deadline: str = ""
    url: str = ""
    description: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "experience": self.experience,
            "skills": self.skills,
            "requirements": self.requirements,
            "preferred": self.preferred,
            "languages": self.languages,
            "education": self.education,
            "work_type": self.work_type,
            "deadline": self.deadline,
            "url": self.url,
            "source": self.source,
        }


@dataclass
class MatchResult:
    """Match analysis between CV and job."""
    match_score: float = 0.0
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    matched_requirements: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "match_score": self.match_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "matched_requirements": self.matched_requirements,
            "missing_requirements": self.missing_requirements,
            "recommendations": self.recommendations,
        }


def load_user_profile() -> dict:
    """Load user profile from profiles/ directory."""
    profile_path = PROFILES_DIR / "user_profile.json"
    if not profile_path.exists():
        return {}
    try:
        with open(profile_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_profile(profile: dict) -> bool:
    """Save user profile."""
    try:
        profile_path = PROFILES_DIR / "user_profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        return True
    except Exception as exc:
        log(f"[JOB] Profile save error: {exc}")
        return False


def analyze_job_listing(text: str, url: str = "") -> JobListing:
    """Parse job listing text into structured data."""
    listing = JobListing(url=url, description=text)

    # Try to extract title (first line or first heading)
    lines = text.strip().split("\n")
    if lines:
        listing.title = lines[0].strip()[:100]

    # Extract skills using common patterns
    skill_patterns = [
        r"(?:skills|teknoloji|teknik|yetenek)[\s:]+(.+?)(?:\n\n|\Z)",
        r"(?: requirements|gereksinim)[\s:]+(.+?)(?:\n\n|\Z)",
    ]
    for pattern in skill_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            skills_text = match.group(1)
            listing.skills = [s.strip() for s in re.split(r"[,\n•\-]", skills_text) if s.strip()]

    # Extract location
    loc_match = re.search(r"(?:location|lokasyon|yer|adres)[\s:]+([^\n]+)", text, re.IGNORECASE)
    if loc_match:
        listing.location = loc_match.group(1).strip()

    # Extract experience
    exp_match = re.search(r"(?:experience|deneyim)[\s:]+([^\n]+)", text, re.IGNORECASE)
    if exp_match:
        listing.experience = exp_match.group(1).strip()

    # Extract salary
    sal_match = re.search(r"(?:salary|maaş|ücret|compensation)[\s:]+([^\n]+)", text, re.IGNORECASE)
    if sal_match:
        listing.salary = sal_match.group(1).strip()

    return listing


def match_cv_to_job(user_profile: dict, job: JobListing) -> MatchResult:
    """Compare user profile/CV against job listing."""
    result = MatchResult()

    user_skills = set(s.lower() for s in user_profile.get("skills", []))
    job_skills = set(s.lower() for s in job.skills)

    if job_skills:
        result.matched_skills = [s for s in job.skills if s.lower() in user_skills]
        result.missing_skills = [s for s in job.skills if s.lower() not in user_skills]
        if job_skills:
            result.match_score = len(result.matched_skills) / len(job_skills) * 100

    # Check requirements
    user_experience = user_profile.get("experience_years", 0)
    result.recommendations = []

    if result.match_score < 50:
        result.recommendations.append("Düşük uyum puanı — bu ilana başvuru riskli olabilir")
    if result.missing_skills:
        result.recommendations.append(f"Eksik yetenekler: {', '.join(result.missing_skills[:5])}")

    return result


def generate_cover_letter(user_profile: dict, job: JobListing, match: MatchResult) -> str:
    """Generate a cover letter template.

    NOTE: This generates a template. The actual content should be reviewed
    and customized by the user before sending.
    """
    name = user_profile.get("name", "[İSİM]")
    template = f"""Sayın {job.company or '[ŞİRKET]'} Yetkilileri,

{job.title or '[POZİSYON]'} ilanınızı gördüm ve bu pozisyona yönelik deneyimlerimi sizinle paylaşmak istiyorum.

{user_profile.get('experience_summary', '[DENETİM ÖZETİ]')}

"""
    if match.matched_skills:
        template += f"Pozisyonunuzda gereken {', '.join(match.matched_skills[:5])} gibi yeteneklere sahibim.\n\n"

    if match.missing_skills:
        template += f"Not: {', '.join(match.missing_skills[:3])} alanlarında kendimi geliştirmekteyim.\n\n"

    template += """Bu pozisyonda ekibinize katkı sağlayabileceğime inanıyorum.
Görüşme fırsatı tanığınız için teşekkür ederim.

Saygılarımla,
[İSİM]
[İLETİŞİM]"""

    return template


# Available search query builders
def build_search_queries(job_title: str, location: str = "", keywords: list[str] | None = None) -> list[str]:
    """Build search queries for job search."""
    queries = []
    base = f"{job_title} iş ilanı"
    if location:
        base += f" {location}"
    queries.append(base)
    if keywords:
        queries.append(f"{job_title} {' '.join(keywords[:3])}")
    queries.append(f"{job_title} job opening")
    return queries
