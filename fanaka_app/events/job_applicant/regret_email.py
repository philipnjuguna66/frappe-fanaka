"""Regret email queueing for Job Applicant, plus the shared templated-send helper
reused by the interview-invite path (Phase 6).

See specs/recruitment_ai_screening.md (Phase 4) for the plan this implements.
"""

import frappe
from frappe.utils import now_datetime

# Statuses a candidate must NOT be in for a regret email to go out -- these are all
# "good news" or already-decided outcomes.
NON_REGRETTABLE_STATUSES = ("Shortlisted by AI", "Shortlisted", "Accepted", "Hold")


def send_templated_email(
	*,
	template: str,
	applicant_name: str,
	recipient: str | None = None,
	sender: str | None = None,
	extra_context: dict | None = None,
):
	"""Render an Email Template against a Job Applicant and send it.

	Bare placeholders (``{{ applicant_name }}``, not ``{{ doc.applicant_name }}``) --
	matches hrms's own shipped hiring templates, since ours sit in the same Email
	Template list HR browses. See the Phase 4 placeholder-convention note in the spec.

	``extra_context`` adds fields beyond the applicant's own (e.g. interview schedule
	details for the invite email in Phase 6) -- merged on top of the applicant dict, so
	an extra key can't be shadowed by a same-named Job Applicant field.

	``recipient`` overrides the applicant's own email -- used by the settings "Send Test
	Email" button so a test render never reaches a real candidate. A real send (no
	recipient override) always goes through ``frappe.sendmail``'s own queueing
	(``now=False`` by default); a test send goes out immediately so the sender gets
	pass/fail feedback in the same request.
	"""
	applicant = frappe.get_doc("Job Applicant", applicant_name)
	et = frappe.get_doc("Email Template", template)
	context = applicant.as_dict()
	if extra_context:
		context.update(extra_context)
	rendered = et.get_formatted_email(context)

	frappe.sendmail(
		recipients=[recipient or applicant.email_id],
		sender=sender,
		subject=rendered["subject"],
		message=rendered["message"],
		reference_doctype="Job Applicant",
		reference_name=applicant.name,
		now=bool(recipient),
	)


def enqueue_regret_email(applicant_name: str):
	"""Queue a background job to send the regret email to one applicant.

	Called from three places: the daily scheduler (fanaka_app.api.regret_emails.run),
	the Job Applicant list view's bulk action, and -- later -- the reject-and-regret
	action on the Shortlisted Candidates page (Phase 6). One send path for all three,
	per the spec.
	"""
	frappe.enqueue(
		"fanaka_app.events.job_applicant.regret_email._send_regret_email",
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
		applicant_name=applicant_name,
	)


def _send_regret_email(applicant_name: str):
	"""Background job body: render, send, and mark sent.

	Re-checks the sent flag and status here (not just in the callers) because this
	runs asynchronously -- state may have moved on between enqueue and execution, e.g.
	HR approved the candidate in the few seconds before the job ran.
	"""
	from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

	settings = get_settings()
	if not settings.regret_email_template:
		frappe.log_error(
			title="Regret email not sent: no template configured",
			message=f"Job Applicant {applicant_name}",
		)
		return

	applicant = frappe.get_doc("Job Applicant", applicant_name)
	if applicant.custom_regret_email_sent:
		return
	if applicant.status in NON_REGRETTABLE_STATUSES:
		return

	send_templated_email(
		template=settings.regret_email_template,
		applicant_name=applicant_name,
		sender=hiring_sender_email(),
	)

	applicant.db_set("custom_regret_email_sent", 1)
	applicant.db_set("custom_regret_email_sent_on", now_datetime(), update_modified=False)


@frappe.whitelist()
def bulk_send_regret_emails(applicant_names: list[str] | str, force: bool = False) -> dict:
	"""Manual/bulk send from the Job Applicant list view.

	Works regardless of the ``auto_send_regret_emails`` toggle -- HR can send with
	automation off, or act on applicants in the grey zone between the regret and
	shortlist thresholds that automation deliberately never touches.
	"""
	frappe.only_for(("System Manager", "HR Manager", "HR User"))

	if isinstance(applicant_names, str):
		applicant_names = frappe.parse_json(applicant_names)
	force = frappe.utils.cint(force)

	queued, skipped = 0, 0
	for name in applicant_names:
		status, already_sent = frappe.db.get_value(
			"Job Applicant", name, ["status", "custom_regret_email_sent"]
		)
		if status in NON_REGRETTABLE_STATUSES:
			skipped += 1
			continue
		if already_sent and not force:
			skipped += 1
			continue

		enqueue_regret_email(name)
		queued += 1

	return {"queued": queued, "skipped": skipped}


def hiring_sender_email() -> str | None:
	"""hrms's own dedicated recruitment sender, if HR has configured one."""
	return frappe.db.get_single_value("HR Settings", "hiring_sender_email")
