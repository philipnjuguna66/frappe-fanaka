# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Interview-round sequencing on Job Opening + confirmation-email flag on Employee
	Onboarding.

	See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
	"""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Opening": [
				{
					"fieldname": "custom_interview_rounds",
					"fieldtype": "Table",
					"label": "Interview Rounds",
					"options": "Job Opening Interview Round",
					"insert_after": "custom_qualifications",
					"description": "Ordered sequence of interview rounds for this opening. "
					"Clearing the last round in this list drafts a Job Offer for the "
					"candidate; clearing an earlier round auto-schedules the next. Leave "
					"empty to opt this opening out of pipeline automation entirely.",
				},
			],
			"Employee Onboarding": [
				{
					"fieldname": "custom_confirmation_email_sent",
					"fieldtype": "Check",
					"label": "Confirmation Email Sent",
					"insert_after": "boarding_status",
					"read_only": 1,
				},
			],
		}
	)
