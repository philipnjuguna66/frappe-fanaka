"""Employee Onboarding doc_events: employment-confirmation email once onboarding
completes (hrms's own "Mark Onboarding as Completed" button sets boarding_status to
"Completed" -- see hrms/hr/doctype/employee_onboarding/employee_onboarding.py).

See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
"""

import frappe

from fanaka_app.events.job_applicant.regret_email import hiring_sender_email, send_templated_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


def on_status_change(doc, method=None):
	if not doc.has_value_changed("boarding_status") or doc.boarding_status != "Completed":
		return
	if doc.custom_confirmation_email_sent or not doc.job_applicant:
		return

	frappe.enqueue(
		"fanaka_app.events.employee_onboarding.employee_onboarding._send_confirmation_email",
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
		onboarding_name=doc.name,
	)


def _send_confirmation_email(onboarding_name: str):
	settings = get_settings()
	if not settings.employment_confirmation_template:
		frappe.log_error(
			title="Employment confirmation email not sent: no template configured",
			message=f"Employee Onboarding {onboarding_name}",
		)
		return

	onboarding = frappe.get_doc("Employee Onboarding", onboarding_name)
	if onboarding.custom_confirmation_email_sent or onboarding.boarding_status != "Completed":
		return

	# Recipient stays the Job Applicant's own email_id (send_templated_email's default) --
	# not Employee.personal_email -- since overriding the recipient there also switches
	# the send to immediate/unqueued (built for the settings "Send Test Email" button,
	# not a production send). Same person, same address used throughout this app.
	send_templated_email(
		template=settings.employment_confirmation_template,
		applicant_name=onboarding.job_applicant,
		sender=hiring_sender_email(),
	)

	onboarding.db_set("custom_confirmation_email_sent", 1, update_modified=False)
