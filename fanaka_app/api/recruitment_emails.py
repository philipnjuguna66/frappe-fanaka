"""Recruitment AI Settings' "Send Test Email" action.

Lets HR see exactly what a candidate would receive before any real send goes out --
the only practical way to catch a misspelt bare placeholder, which otherwise renders
empty and silent. See specs/recruitment_ai_screening.md (Phase 4) for the plan this
implements.
"""

import frappe
from frappe import _

from fanaka_app.events.job_applicant.regret_email import send_templated_email


@frappe.whitelist()
def send_test_email(template: str, job_applicant: str, recipient: str | None = None) -> str:
	frappe.only_for(("System Manager", "HR Manager"))

	if not template:
		frappe.throw(_("Select a Template to Test."))
	if not job_applicant:
		frappe.throw(_("Select a Job Applicant to render the template's placeholders against."))

	recipient = recipient or (frappe.session.user if "@" in frappe.session.user else None)
	if not recipient:
		frappe.throw(_("Your account has no email address on file -- set Send Test To explicitly."))

	send_templated_email(template=template, applicant_name=job_applicant, recipient=recipient)
	return recipient
