"""Job Applicant doc_events + HR review actions for AI recruitment screening.

See specs/recruitment_ai_screening.md (Phase 2: doc_events, Phase 3: approve/reject)
for the plan this implements.
"""

import frappe
from frappe import _

from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

REFERRAL_SYNC_STATUS = "In Process"
APPROVAL_ROLES = ("System Manager", "HR Manager", "HR User")


def after_insert(doc, method=None):
	from fanaka_app.events.job_applicant.application_received import enqueue_application_received_email

	enqueue_application_received_email(doc.name)


def on_update(doc, method=None):
	_queue_ai_screening(doc)
	_sync_employee_referral(doc)
	_regret_on_reject(doc)


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


def _regret_on_reject(doc):
	"""Any-stage rejection gets the same regret email -- AI-stage reject (this module's
	own reject_ai_shortlist) and hrms's native post-interview "Mark as Rejected" dialog
	(hrms/hr/doctype/interview/interview.py) both just set status = "Rejected" and save,
	so hooking the status change here covers both without hrms code changes. Before
	Phase 8, an interview-stage rejection sent no email at all -- exactly the gap
	Phase 1's "close the loop with every candidate" principle was written to prevent.

	See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
	"""
	if not doc.has_value_changed("status") or doc.status != "Rejected":
		return
	if doc.custom_regret_email_sent:
		return

	from fanaka_app.events.job_applicant.regret_email import enqueue_regret_email

	enqueue_regret_email(doc.name)


@frappe.whitelist()
def approve_ai_shortlist(name: str) -> str:
	"""HR approves an AI-shortlisted candidate: Shortlisted by AI -> Shortlisted.

	Role-checked explicitly (not just relying on the doctype's own permissions) so this
	specific action stays gated to recruitment roles even if Job Applicant's general
	write permissions are ever loosened for other reasons.
	"""
	frappe.only_for(APPROVAL_ROLES)
	doc = _get_shortlisted_by_ai(name)
	doc.status = "Shortlisted"
	doc.save()
	return doc.status


@frappe.whitelist()
def reject_ai_shortlist(name: str) -> str:
	"""HR rejects an AI-shortlisted candidate: Shortlisted by AI -> Rejected."""
	frappe.only_for(APPROVAL_ROLES)
	doc = _get_shortlisted_by_ai(name)
	doc.status = "Rejected"
	doc.save()
	return doc.status


def _get_shortlisted_by_ai(name: str):
	doc = frappe.get_doc("Job Applicant", name)
	if doc.status != "Shortlisted by AI":
		frappe.throw(
			_('Only candidates with status "Shortlisted by AI" can be reviewed this way. Current status: {0}').format(
				doc.status
			)
		)
	return doc


@frappe.whitelist()
def reanalyze_candidate(name: str) -> str:
	"""Manually re-run AI screening for one applicant.

	Bypasses the "did resume/cover letter actually change" guard that gates the
	automatic on_update trigger -- needed to recover after fixing a misconfigured
	Recruitment AI Settings (wrong model, missing/blank API key, etc.) without having
	to re-upload the resume just to re-trigger analysis.
	"""
	frappe.only_for(APPROVAL_ROLES)

	doc = frappe.get_doc("Job Applicant", name)
	if not (doc.resume_attachment or doc.cover_letter):
		frappe.throw(_("Nothing to analyze -- this applicant has no resume or cover letter."))

	settings = get_settings()
	if not settings.enable_ai_screening:
		frappe.throw(_("AI Screening is currently disabled in Recruitment AI Settings."))

	frappe.enqueue(
		"fanaka_app.events.job_applicant.ai_screen.analyze_candidate",
		queue="long",
		timeout=600,
		enqueue_after_commit=True,
		job_applicant=doc.name,
	)
	return "queued"
