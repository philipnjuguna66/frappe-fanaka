# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Show the regret-sent flag as a Job Applicant list column.

	custom_ai_score already got in_list_view/in_standard_filter in
	add_recruitment_ai_fields.py -- this just extends custom_regret_email_sent to match,
	per Phase 5 of specs/recruitment_ai_screening.md. create_custom_fields(update=True)
	(the default) updates an existing Custom Field by (dt, fieldname) rather than
	erroring on a duplicate, so this is safe to run against a site that already has the
	field from the earlier patch.
	"""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Applicant": [
				{
					"fieldname": "custom_regret_email_sent",
					"fieldtype": "Check",
					"label": "Regret Email Sent",
					"insert_after": "custom_ai_column_break",
					"read_only": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
			]
		}
	)
