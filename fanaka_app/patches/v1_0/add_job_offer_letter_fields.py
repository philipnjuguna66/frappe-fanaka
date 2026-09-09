# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Offer-letter-sent tracking on Job Offer.

	See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
	"""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Offer": [
				{
					"fieldname": "custom_offer_letter_sent",
					"fieldtype": "Check",
					"label": "Offer Letter Sent",
					"insert_after": "status",
					"read_only": 1,
				},
				{
					"fieldname": "custom_offer_letter_sent_on",
					"fieldtype": "Datetime",
					"label": "Offer Letter Sent On",
					"insert_after": "custom_offer_letter_sent",
					"read_only": 1,
					"depends_on": "custom_offer_letter_sent",
				},
			],
		}
	)
