"""Job Offer doc_events: candidate-facing confirmation email + HR handoff once
accepted.

Employee/Employee Onboarding are deliberately NOT auto-created here. hrms's own
"Create Employee" button (job_offer.js, shown once the offer is submitted and
Accepted) already opens a pre-filled, unsaved Employee form for HR to complete --
duplicating that server-side would mean force-inserting a record missing fields
nothing in this system can know (gender, date_of_birth, date_of_joining are business
facts, not derivable defaults), which is worse than just handing HR the native button.
Employee Onboarding has the same problem (date_of_joining, boarding_begins_on are
required and unknowable). See specs/recruitment_ai_screening.md (Phase 8) for the
build-time correction this reflects.

See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
"""

import frappe
from frappe import _

from fanaka_app.events.hr_notify import notify_hr
from fanaka_app.events.job_applicant.regret_email import hiring_sender_email, send_templated_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


def on_status_change(doc, method=None):
	# Registered on doc_events "on_change", not "on_update" -- HR flips status to
	# Accepted on an already-submitted offer, which Frappe runs as the
	# "update_after_submit" action (fires on_update_after_submit, not on_update).
	# "on_change" is the one event Frappe always fires regardless of action type
	# (frappe/model/document.py:run_post_save_methods) -- verified live during build
	# after this handler silently never ran registered on "on_update".
	if doc.docstatus != 1:
		return
	if not doc.has_value_changed("status") or doc.status != "Accepted":
		return

	frappe.enqueue(
		"fanaka_app.events.job_offer.job_offer._send_offer_acceptance_email",
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
		job_offer=doc.name,
	)
	notify_hr(
		"Job Offer",
		doc.name,
		_(
			'{0} accepted the offer -- use "Create Employee" on this Job Offer, then start '
			"Employee Onboarding from the Job Applicant's dashboard."
		).format(doc.applicant_name),
	)


def _send_offer_acceptance_email(job_offer: str):
	"""Background job body: settings/template check happens here, not before enqueueing
	-- same convention as regret_email.py and employee_onboarding.py, since the queued
	state may have moved on (or settings may have changed) between enqueue and run."""
	settings = get_settings()
	if not settings.offer_acceptance_confirmation_template:
		frappe.log_error(
			title="Offer acceptance email not sent: no template configured",
			message=f"Job Offer {job_offer}",
		)
		return

	offer = frappe.get_doc("Job Offer", job_offer)
	if offer.status != "Accepted":
		return

	send_templated_email(
		template=settings.offer_acceptance_confirmation_template,
		applicant_name=offer.job_applicant,
		sender=hiring_sender_email(),
		extra_context={"offer_date": offer.offer_date, "designation": offer.designation},
	)
