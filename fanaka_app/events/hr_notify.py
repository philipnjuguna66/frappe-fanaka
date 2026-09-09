"""Shared HR-notification helper for the pipeline-automation events (Phase 8): assigns
a ToDo to every enabled user holding a recruitment approval role, so a newly created
draft (next interview round, Job Offer, ...) reaches an actual person instead of
sitting unassigned.

Same role-lookup-by-SQL idiom hrms's own EmployeeBoardingController.create_task_and_
notify_user already uses (hrms/controllers/employee_boarding_controller.py) -- this is
this app's own copy of a pattern hrms already relies on itself, not a new idiom.

See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
"""

import frappe
from frappe.desk.form.assign_to import add as assign_to_add

from fanaka_app.events.job_applicant.job_applicant import APPROVAL_ROLES


def notify_hr(reference_doctype: str, reference_name: str, message: str):
	users = frappe.db.sql_list(
		"""
		SELECT DISTINCT has_role.parent
		FROM `tabHas Role` has_role
		INNER JOIN `tabUser` user ON has_role.parent = user.name
		WHERE user.enabled = 1 AND has_role.role IN %(roles)s AND has_role.parent != 'Administrator'
		""",
		{"roles": APPROVAL_ROLES},
	)
	if not users:
		return

	assign_to_add(
		{
			"assign_to": users,
			"doctype": reference_doctype,
			"name": reference_name,
			"description": message,
		}
	)
