# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe

WEB_FORM = "job-application"
FIELDNAME = "custom_preferred_work_location"


def ensure_preferred_work_location():
	"""Show Preferred Work Location (optional) on the HRMS job-application web form.

	The web form is standard (shipped by hrms) and re-synced on every migrate, and
	Web Form.save() refuses standard forms outside developer mode, so the child row
	is written straight to the DB. Idempotent; runs from after_migrate.
	"""
	if not frappe.db.exists("Web Form", WEB_FORM):
		return
	if not frappe.db.exists("Custom Field", f"Job Applicant-{FIELDNAME}"):
		return
	if frappe.db.exists("Web Form Field", {"parent": WEB_FORM, "fieldname": FIELDNAME}):
		return

	after = frappe.db.get_value(
		"Web Form Field", {"parent": WEB_FORM, "fieldname": "country"}, "idx"
	)
	if after is None:
		after = frappe.db.count("Web Form Field", {"parent": WEB_FORM})
	idx = after + 1

	frappe.db.sql(
		"update `tabWeb Form Field` set idx = idx + 1 where parent = %s and idx >= %s",
		(WEB_FORM, idx),
	)
	frappe.get_doc(
		{
			"doctype": "Web Form Field",
			"parent": WEB_FORM,
			"parenttype": "Web Form",
			"parentfield": "web_form_fields",
			"idx": idx,
			"fieldname": FIELDNAME,
			"fieldtype": "Data",
			"label": "Preferred Work Location",
			"reqd": 0,
		}
	).db_insert()
	frappe.clear_document_cache("Web Form", WEB_FORM)
