"""Whitelisted methods backing the Shortlisted Candidates desk page.

Ties Phase 3's approve/reject and Phase 4's regret-email send path together into the
surface HR actually works from day to day: everyone with status "Shortlisted by AI" or
the human-approved "Shortlisted" in one filterable list, with row/bulk actions to either
approve + invite for interview, or reject + send a regret email.

See specs/recruitment_ai_screening.md (Phase 6) for the plan this implements.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from fanaka_app.events.job_applicant.interview_invite import enqueue_interview_invite
from fanaka_app.events.job_applicant.job_applicant import APPROVAL_ROLES, approve_ai_shortlist, reject_ai_shortlist
from fanaka_app.events.job_applicant.regret_email import enqueue_regret_email

LISTED_STATUSES = ("Shortlisted by AI", "Shortlisted")


@frappe.whitelist()
def get_shortlisted_candidates(filters: dict | str | None = None) -> list[dict]:
	"""Server-side filtered query backing the page's listing. Keep filtering here, not
	in JS -- the point of a dedicated endpoint is that the client never pulls the full
	table."""
	frappe.only_for(APPROVAL_ROLES)
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})

	query_filters = []

	status = filters.get("status")
	if status in LISTED_STATUSES:
		query_filters.append(["status", "=", status])
	else:
		query_filters.append(["status", "in", LISTED_STATUSES])

	if filters.get("job_opening"):
		query_filters.append(["job_title", "=", filters["job_opening"]])
	if filters.get("designation"):
		query_filters.append(["designation", "=", filters["designation"]])
	if filters.get("min_score") not in (None, ""):
		query_filters.append(["custom_ai_score", ">=", flt(filters["min_score"])])
	if filters.get("max_score") not in (None, ""):
		query_filters.append(["custom_ai_score", "<=", flt(filters["max_score"])])
	if filters.get("from_date"):
		query_filters.append(["creation", ">=", filters["from_date"]])
	if filters.get("to_date"):
		query_filters.append(["creation", "<=", filters["to_date"]])
	if filters.get("email_sent") not in (None, ""):
		query_filters.append(["custom_regret_email_sent", "=", cint(filters["email_sent"])])

	return frappe.get_all(
		"Job Applicant",
		filters=query_filters,
		fields=[
			"name",
			"applicant_name",
			"email_id",
			"job_title",
			"designation",
			"status",
			"custom_ai_score",
			"custom_ai_analysis_summary",
			"custom_regret_email_sent",
			"resume_attachment",
			"resume_link",
			"creation",
		],
		order_by="custom_ai_score desc",
	)


@frappe.whitelist()
def approve_and_invite(
	job_applicant: str, interview_type: str, scheduled_on: str, from_time: str, to_time: str
) -> dict:
	"""Approve (if not already) and schedule + queue-invite an interview.

	Handles both statuses this page lists: "Shortlisted by AI" gets promoted first,
	"Shortlisted" (already human-approved earlier, HR is only inviting now) is scheduled
	directly.
	"""
	frappe.only_for(APPROVAL_ROLES)

	applicant = frappe.get_doc("Job Applicant", job_applicant)
	if applicant.status not in LISTED_STATUSES:
		frappe.throw(
			_("Only Shortlisted by AI or Shortlisted candidates can be invited for interview. Current status: {0}").format(
				applicant.status
			)
		)
	if applicant.status == "Shortlisted by AI":
		approve_ai_shortlist(job_applicant)

	from hrms.hr.doctype.job_applicant.job_applicant import create_interview

	try:
		interview = create_interview(job_applicant, interview_type)
		interview.scheduled_on = scheduled_on
		interview.from_time = from_time
		interview.to_time = to_time
		interview.insert()
	except frappe.ValidationError as e:
		# hrms's own validate_designation() (thrown inside create_interview) and
		# validate_duplicate_interview() (thrown on insert()) both raise ValidationError
		# subclasses -- surfaced as a clean message, not a raw traceback, per the spec.
		frappe.throw(str(e), title=_("Could Not Schedule Interview"))

	enqueue_interview_invite(job_applicant, interview.name)
	return {"interview": interview.name}


@frappe.whitelist()
def reject_and_regret(job_applicant: str) -> dict:
	"""Reject (if not already) and queue the regret email -- one send path, same as the
	scheduler and the Job Applicant list's bulk action."""
	frappe.only_for(APPROVAL_ROLES)

	applicant = frappe.get_doc("Job Applicant", job_applicant)
	if applicant.status not in LISTED_STATUSES:
		frappe.throw(
			_("Only Shortlisted by AI or Shortlisted candidates can be rejected this way. Current status: {0}").format(
				applicant.status
			)
		)

	if applicant.status == "Shortlisted by AI":
		reject_ai_shortlist(job_applicant)
	else:
		applicant.status = "Rejected"
		applicant.save()

	enqueue_regret_email(job_applicant)
	return {"status": "Rejected"}


@frappe.whitelist()
def bulk_reject_and_regret(job_applicants: list[str] | str) -> dict:
	frappe.only_for(APPROVAL_ROLES)
	if isinstance(job_applicants, str):
		job_applicants = frappe.parse_json(job_applicants)

	processed = 0
	for name in job_applicants:
		reject_and_regret(name)
		processed += 1
	return {"processed": processed}


@frappe.whitelist()
def bulk_approve(job_applicants: list[str] | str) -> dict:
	"""Approve without inviting -- interviews can't be bulk-scheduled sensibly, each
	needs its own time slot. Only candidates still at "Shortlisted by AI" are actioned;
	already-"Shortlisted" ones are silently skipped rather than erroring, since bulk
	selections routinely mix both."""
	frappe.only_for(APPROVAL_ROLES)
	if isinstance(job_applicants, str):
		job_applicants = frappe.parse_json(job_applicants)

	processed, skipped = 0, 0
	for name in job_applicants:
		if frappe.db.get_value("Job Applicant", name, "status") == "Shortlisted by AI":
			approve_ai_shortlist(name)
			processed += 1
		else:
			skipped += 1
	return {"processed": processed, "skipped": skipped}
