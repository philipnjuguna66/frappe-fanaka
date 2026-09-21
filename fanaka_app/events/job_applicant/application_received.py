"""Application-received acknowledgement email, sent when a candidate applies.

Same templated-send + background-job pattern as regret_email.py / interview_invite.py.
"""

import re

import frappe

from fanaka_app.events.job_applicant.regret_email import hiring_sender_email, send_templated_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


# "Re: ...", "RE: ...", "Fwd: ...", "FW: ..." -- an inbound mail with this subject is a
# reply to something we sent, not a fresh application.
REPLY_SUBJECT = re.compile(r"^\s*(re|fwd?)\s*:", re.IGNORECASE)


def is_email_reply(applicant) -> bool:
	"""True if this Job Applicant was auto-created by the mailbox from a candidate's reply.

	The hiring Email Account has Job Applicant as its "Append To" doctype, so a reply that
	frappe can't thread to the original applicant (mail client dropped the headers, a
	different reply-from address, ...) spawns a brand-new Job Applicant, with the mail
	subject stored in ``notes``. Acknowledging that would answer the candidate's reply.
	"""
	return bool(REPLY_SUBJECT.match(applicant.notes or ""))


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
	if is_email_reply(frappe.get_doc("Job Applicant", applicant_name)):
		return

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
		reply_to=settings.no_reply_email or None,
	)
