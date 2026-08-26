"""Daily automatic regret-email dispatch for low-scoring Job Applicants.

Scheduled via ``scheduler_events.daily`` in hooks.py, alongside the existing
``expiry_reminders.run``. See specs/recruitment_ai_screening.md (Phase 4) for the plan
this implements.
"""

import frappe
from frappe.utils import add_days, cint, flt, getdate, nowdate

from fanaka_app.events.job_applicant.regret_email import NON_REGRETTABLE_STATUSES, enqueue_regret_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


def run():
	"""Scheduler entry point."""
	settings = get_settings()
	if not settings.auto_send_regret_emails:
		return
	if not settings.regret_email_template:
		frappe.log_error(
			title="Automatic regret emails enabled but no template configured",
			message="Set Regret Email Template on Recruitment AI Settings, or turn Auto Send Regret Emails off.",
		)
		return

	grace_days = cint(settings.regret_send_after_days)
	# Exclusive upper bound at the start of the day AFTER the cutoff day, so every
	# datetime on the cutoff day itself still counts as "grace period elapsed" -- the
	# setting is day-granularity, not hour-granularity.
	cutoff_exclusive = add_days(getdate(nowdate()), -grace_days + 1)

	batch_size = cint(settings.regret_batch_size) or 50

	candidates = frappe.get_all(
		"Job Applicant",
		filters=[
			["custom_ai_score", "<", flt(settings.regret_threshold_score)],
			["status", "not in", NON_REGRETTABLE_STATUSES],
			["custom_regret_email_sent", "=", 0],
			["custom_ai_analyzed_on", "is", "set"],
			["custom_ai_analyzed_on", "<", cutoff_exclusive],
		],
		pluck="name",
		order_by="custom_ai_analyzed_on asc",
		limit_page_length=batch_size,
	)

	for name in candidates:
		enqueue_regret_email(name)
