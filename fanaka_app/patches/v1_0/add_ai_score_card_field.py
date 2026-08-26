# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add the read-only HTML field the score card renders into on the Job Applicant form.

	Separate from add_recruitment_ai_fields.py because that patch already ran on
	existing sites -- Frappe's patch log won't re-execute it, so a field added there
	now wouldn't reach any site that already migrated. See
	specs/recruitment_ai_screening.md (Phase 3).
	"""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Applicant": [
				{
					"fieldname": "custom_ai_score_card_html",
					"fieldtype": "HTML",
					"label": "AI Score Card",
					"insert_after": "custom_ai_score_breakdown",
					"read_only": 1,
				},
			]
		}
	)
