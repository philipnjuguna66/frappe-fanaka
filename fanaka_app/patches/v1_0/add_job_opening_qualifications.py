# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add a structured Qualifications field on Job Opening, separate from Description.

	Description is written for humans browsing the careers page (often padded with
	"why join us" / perks copy); Qualifications is a cleaner signal of the actual bar
	for AI screening to match resumes/cover letters against, and for the public page to
	show as its own section. See specs/recruitment_ai_screening.md (Phase 7).
	"""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Opening": [
				{
					"fieldname": "custom_qualifications",
					"fieldtype": "Text Editor",
					"label": "Qualifications",
					"insert_after": "description",
					"description": "Shown as its own section on the careers page and used as the "
					"primary AI screening criteria against uploaded resumes/cover letters.",
				},
			]
		}
	)
