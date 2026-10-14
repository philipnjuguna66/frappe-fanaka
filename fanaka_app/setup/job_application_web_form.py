# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe

WEB_FORM = "job-application"
FIELDNAME = "custom_preferred_work_location"


def ensure_preferred_work_location():
	"""Show Preferred Work Location (optional) on the HRMS job-application web form.

	The web form is standard (shipped by hrms) and re-synced on every migrate,
	so this runs from after_migrate and is idempotent.
	"""
	if not frappe.db.exists("Web Form", WEB_FORM):
		return
	if not frappe.db.exists("Custom Field", f"Job Applicant-{FIELDNAME}"):
		return

	form = frappe.get_doc("Web Form", WEB_FORM)
	if any(f.fieldname == FIELDNAME for f in form.web_form_fields):
		return

	row = {
		"fieldname": FIELDNAME,
		"fieldtype": "Data",
		"label": "Preferred Work Location",
		"reqd": 0,
	}
	# place right after Country of Residence
	idx = next((i for i, f in enumerate(form.web_form_fields) if f.fieldname == "country"), None)
	if idx is None:
		form.append("web_form_fields", row)
	else:
		form.web_form_fields.insert(idx + 1, frappe.new_doc("Web Form Field", parent_doc=form, parentfield="web_form_fields").update(row))
		for n, f in enumerate(form.web_form_fields, 1):
			f.idx = n

	form.flags.ignore_permissions = True
	form.flags.in_patch = True
	form.save()
