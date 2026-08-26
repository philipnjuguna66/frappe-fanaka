"""Job Applicant doc_events for AI recruitment screening.

See specs/recruitment_ai_screening.md (Phase 2) for the plan this implements.
"""

import frappe

from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

REFERRAL_SYNC_STATUS = "In Process"


def on_update(doc, method=None):
	_queue_ai_screening(doc)
	_sync_employee_referral(doc)


def _queue_ai_screening(doc):
	"""Enqueue AI analysis when a resume or cover letter is added/changed.

	Guarding on has_value_changed keeps this from re-triggering when the AI job's own
	``doc.save()`` fires this same on_update hook again -- that save never touches
	resume_attachment/cover_letter, so the guard is naturally false on the second pass.
	"""
	if not (doc.has_value_changed("resume_attachment") or doc.has_value_changed("cover_letter")):
		return
	if not (doc.resume_attachment or doc.cover_letter):
		return

	settings = get_settings()
	if not settings.enable_ai_screening:
		return

	frappe.enqueue(
		"fanaka_app.events.job_applicant.ai_screen.analyze_candidate",
		queue="long",
		timeout=600,
		enqueue_after_commit=True,
		job_applicant=doc.name,
	)


def _sync_employee_referral(doc):
	"""Keep Employee Referral status in step with "Shortlisted by AI".

	hrms's own JobApplicant.set_status_for_employee_referral() maps Open/Replied/Hold to
	"In Process" and Accepted/Rejected to themselves, but has no branch for our new
	"Shortlisted by AI" status -- so a referred candidate's referral would silently stop
	updating right when the referrer would most want to see progress. Extending it here
	rather than patching hrms's method.
	"""
	if not doc.employee_referral:
		return
	if not doc.has_value_changed("status") or doc.status != "Shortlisted by AI":
		return

	frappe.db.set_value("Employee Referral", doc.employee_referral, "status", REFERRAL_SYNC_STATUS)
