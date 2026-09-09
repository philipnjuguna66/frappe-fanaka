"""Interview invitation email for AI-shortlisted candidates.

hrms ships no invitation email of its own -- its only interview mail is
``send_interview_reminder``, a scheduled job that fires shortly before the interview to
interviewers + candidate (see ``hrms/hr/doctype/interview/interview.py``). This fills
that gap using the same templated-send + background-job pattern as the regret email.

See specs/recruitment_ai_screening.md (Phase 6) for the plan this implements.
"""

import frappe
from frappe.utils import format_time, formatdate

from fanaka_app.events.job_applicant.regret_email import hiring_sender_email, send_templated_email
from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings


def enqueue_interview_invite(applicant_name: str, interview_name: str):
	"""Queue a background job to send the interview invite for one applicant."""
	frappe.enqueue(
		"fanaka_app.events.job_applicant.interview_invite._send_interview_invite",
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
		applicant_name=applicant_name,
		interview_name=interview_name,
	)


def _send_interview_invite(applicant_name: str, interview_name: str):
	"""Background job body: render the invite (with interview schedule context) and send."""
	settings = get_settings()
	if not settings.interview_invite_template:
		frappe.log_error(
			title="Interview invite not sent: no template configured",
			message=f"Job Applicant {applicant_name}, Interview {interview_name}",
		)
		return

	interview = frappe.get_doc("Interview", interview_name)

	# Job Applicant.job_title is a Link (the Job Opening's ID, e.g. "HR-OPN-2026-00007"),
	# not a human-readable title -- Job Opening's own job_title/location fields are.
	# location is a Link to Branch, which only ever has a plain name (branch), no
	# address fields -- the most specific "where" this data model has, and real data
	# rather than a guess. Interview itself has no location field of its own.
	job_opening_title = None
	interview_location = None
	if interview.job_opening:
		job_opening_title, location = frappe.db.get_value(
			"Job Opening", interview.job_opening, ["job_title", "location"]
		) or (None, None)
		if location:
			interview_location = frappe.db.get_value("Branch", location, "branch")

	extra_context = {
		"interview_type": interview.interview_type,
		"interview_scheduled_on": formatdate(interview.scheduled_on),
		"interview_from_time": format_time(str(interview.from_time)),
		"interview_to_time": format_time(str(interview.to_time)),
		"job_opening_title": job_opening_title,
		"interview_location": interview_location,
	}

	send_templated_email(
		template=settings.interview_invite_template,
		applicant_name=applicant_name,
		sender=hiring_sender_email(),
		extra_context=extra_context,
	)
