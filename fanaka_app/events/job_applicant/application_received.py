"""Application-received acknowledgement email, sent when a candidate applies.

Same templated-send + background-job pattern as regret_email.py / interview_invite.py.
"""

import frappe

from fanaka_app.events.job_applicant.regret_email import hiring_sender_email, send_templated_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


def enqueue_application_received_email(applicant_name: str):
	"""Queue a background job to send the application-received email to one applicant.

	Called from Job Applicant's after_insert -- fires once per applicant, right when
	their record is created.
	"""
	frappe.enqueue(
		"fanaka_app.events.job_applicant.application_received._send_application_received_email",
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
		applicant_name=applicant_name,
	)


def _send_application_received_email(applicant_name: str):
	"""Background job body: settings/template check happens here, not before enqueueing
	-- same convention as regret_email.py, since settings may change between enqueue and
	run."""
	settings = get_settings()
	if not settings.application_received_template:
		frappe.log_error(
			title="Application received email not sent: no template configured",
			message=f"Job Applicant {applicant_name}",
		)
		return

	send_templated_email(
		template=settings.application_received_template,
		applicant_name=applicant_name,
		sender=hiring_sender_email(),
	)
