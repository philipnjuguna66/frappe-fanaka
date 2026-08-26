"""AI resume/cover-letter screening for Job Applicant.

Runs as a background job, queued by ``fanaka_app.events.job_applicant.job_applicant``
whenever a resume or cover letter is uploaded. Extracts resume text, sends it to
whichever LLM provider is configured in Recruitment AI Settings (see
``fanaka_app.api.llm_providers``) alongside the Job Opening's Qualifications + Description,
and writes back an aggregate score plus a per-category breakdown.

See specs/recruitment_ai_screening.md (Phase 1/2, Phase 7) for the plan this implements.
"""

import os

import frappe
from frappe.utils import flt, now_datetime, strip_html_tags

from fanaka_app.api.llm_providers import get_adapter
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

SCORE_CATEGORIES = ("Skills", "Experience", "Education")

# Statuses a re-analysis is allowed to promote out of. Anything else means a human (or an
# earlier analysis) already made a call on this applicant -- re-running AI screening (e.g.
# after a corrected resume upload) must not silently overturn that.
PROMOTABLE_STATUSES = ("Open", "Replied")

SYSTEM_PROMPT = """You are screening a job application against a job opening's requirements.
Score the candidate's fit as a percentage from 0 to 100, and justify it with a breakdown
across exactly these three categories: Skills, Experience, Education. Each category may
contain any number of reasons (at least one), each with a point contribution (which may be
negative, e.g. a missing required skill) such that the points across all categories sum to
the aggregate score.

Respond with ONLY a JSON object of this exact shape, no other text:
{
  "score": <number 0-100>,
  "summary": "<1-3 sentence overall assessment>",
  "breakdown": [
    {"category": "Skills", "criteria": "<short label>", "points": <number>, "remark": "<why>"},
    ...
  ]
}"""


def analyze_candidate(job_applicant: str):
	"""Background job entry point. Enqueued with ``job_applicant=<name>``."""
	settings = get_settings()
	if not settings.enable_ai_screening:
		# screening was turned off between enqueue and this job running -- skip quietly
		return

	doc = frappe.get_doc("Job Applicant", job_applicant)

	resume_text = _extract_resume_text(doc.resume_attachment)
	cover_letter_text = strip_html_tags(doc.cover_letter) if doc.cover_letter else ""

	if not resume_text and not cover_letter_text:
		frappe.logger().info(f"Job Applicant {doc.name}: nothing to analyze (no resume/cover letter text)")
		return

	job_context = _job_opening_context(doc.job_title)

	try:
		adapter = get_adapter(settings.llm_provider)
		result = adapter.chat_completion(
			model=settings.llm_model,
			api_key=settings.get_password("llm_api_key", raise_exception=False),
			messages=[
				{"role": "system", "content": SYSTEM_PROMPT},
				{
					"role": "user",
					"content": (
						f"JOB OPENING:\n{job_context or '(no description or qualifications provided)'}\n\n"
						f"CANDIDATE COVER LETTER:\n{cover_letter_text or '(none provided)'}\n\n"
						f"CANDIDATE RESUME:\n{resume_text or '(none provided)'}"
					),
				},
			],
		)
	except Exception:
		frappe.log_error(
			title="AI candidate screening failed",
			message=frappe.get_traceback(),
			reference_doctype="Job Applicant",
			reference_name=doc.name,
		)
		raise

	_apply_result(doc, result, settings)


def _apply_result(doc, result: dict, settings):
	score = max(0.0, min(100.0, flt(result.get("score"))))
	breakdown = _valid_breakdown_rows(result.get("breakdown"))

	doc.custom_ai_score = score
	doc.custom_ai_analysis_summary = str(result.get("summary") or "")[:2000]
	doc.custom_ai_analyzed_on = now_datetime()
	doc.set("custom_ai_score_breakdown", [])
	for row in breakdown:
		doc.append("custom_ai_score_breakdown", row)

	if score >= flt(settings.shortlist_threshold_score) and doc.status in PROMOTABLE_STATUSES:
		doc.status = "Shortlisted by AI"

	# validate_fields_for_doctype/permissions already covered by controller; this job runs
	# unattended, so ignore_permissions is correct here, same as hrms's own status-update jobs.
	doc.save(ignore_permissions=True)


def _valid_breakdown_rows(breakdown) -> list[dict]:
	if not isinstance(breakdown, list):
		return []

	rows = []
	for row in breakdown:
		if not isinstance(row, dict):
			continue
		category = row.get("category")
		criteria = row.get("criteria")
		if category not in SCORE_CATEGORIES or not criteria:
			continue
		rows.append(
			{
				"category": category,
				"criteria": str(criteria)[:140],
				"points": flt(row.get("points")),
				"remark": str(row.get("remark") or "")[:500],
			}
		)
	return rows


def _job_opening_context(job_title: str | None) -> str:
	"""Qualifications + Description, in that order -- Qualifications is the primary
	screening signal (Description is written for the careers page and often padded
	with "why join us" copy), with Description still included for role-summary context
	(e.g. seniority level implied by the pitch). If Qualifications is empty (an opening
	predating this field, or HR hasn't filled it in yet), this naturally reduces to just
	Description -- no special-cased fallback branch needed.
	"""
	if not job_title:
		return ""

	description, qualifications = frappe.db.get_value(
		"Job Opening", job_title, ["description", "custom_qualifications"]
	)

	parts = []
	if qualifications:
		parts.append("Qualifications:\n" + strip_html_tags(qualifications))
	if description:
		parts.append("Description:\n" + strip_html_tags(description))
	return "\n\n".join(parts)


def _extract_resume_text(resume_attachment: str | None) -> str:
	if not resume_attachment:
		return ""

	file_doc = frappe.get_doc("File", {"file_url": resume_attachment})
	file_path = file_doc.get_full_path()
	extension = os.path.splitext(file_path)[1].lower()

	try:
		if extension == ".pdf":
			return _extract_pdf_text(file_path)
		if extension == ".docx":
			return _extract_docx_text(file_path)
	except Exception:
		frappe.log_error(
			title="Resume text extraction failed",
			message=frappe.get_traceback(),
			reference_doctype="File",
			reference_name=file_doc.name,
		)
		return ""

	frappe.logger().info(f"Resume {resume_attachment}: unsupported file type {extension!r}, skipped")
	return ""


def _extract_pdf_text(file_path: str) -> str:
	import pdfplumber

	with pdfplumber.open(file_path) as pdf:
		return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_docx_text(file_path: str) -> str:
	import docx

	document = docx.Document(file_path)
	return "\n".join(p.text for p in document.paragraphs)
