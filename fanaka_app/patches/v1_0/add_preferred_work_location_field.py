# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Optional Preferred Work Location on Job Applicant."""
	if "hrms" not in frappe.get_installed_apps():
		return

	create_custom_fields(
		{
			"Job Applicant": [
				{
					"fieldname": "custom_preferred_work_location",
					"fieldtype": "Data",
					"label": "Preferred Work Location",
					"insert_after": "country",
					"reqd": 0,
				},
			],
		}
	)
