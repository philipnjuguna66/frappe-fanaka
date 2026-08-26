# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# hrms's shipped Select options, plus "Shortlisted by AI" inserted right after "Replied" —
# the AI recommends, a human still has to move it on to the real "Shortlisted".
JOB_APPLICANT_STATUS_OPTIONS = (
	"Open\nReplied\nShortlisted by AI\nShortlisted\nRejected\nHold\nAccepted"
)


def execute():
	"""Recruitment AI screening: custom fields + status option on Job Applicant.

	See specs/recruitment_ai_screening.md (Phase 1) for the full plan this implements.
	"""
	if "hrms" not in frappe.get_installed_apps():
		# Job Applicant belongs to hrms — nothing to extend if it isn't installed.
		return

	create_custom_fields(
		{
			"Job Applicant": [
				{
					"fieldname": "custom_ai_section",
					"fieldtype": "Section Break",
					"label": "AI Screening",
					"insert_after": "notes",
					"collapsible": 1,
				},
				{
					"fieldname": "custom_ai_score",
					"fieldtype": "Percent",
					"label": "AI Score",
					"insert_after": "custom_ai_section",
					"read_only": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"description": "Aggregate match score from AI analysis of the resume and cover letter against the Job Opening.",
				},
				{
					"fieldname": "custom_ai_analyzed_on",
					"fieldtype": "Datetime",
					"label": "AI Analyzed On",
					"insert_after": "custom_ai_score",
					"read_only": 1,
				},
				{
					"fieldname": "custom_ai_column_break",
					"fieldtype": "Column Break",
					"insert_after": "custom_ai_analyzed_on",
				},
				{
					"fieldname": "custom_regret_email_sent",
					"fieldtype": "Check",
					"label": "Regret Email Sent",
					"insert_after": "custom_ai_column_break",
					"read_only": 1,
					"in_standard_filter": 1,
				},
				{
					"fieldname": "custom_regret_email_sent_on",
					"fieldtype": "Datetime",
					"label": "Regret Email Sent On",
					"insert_after": "custom_regret_email_sent",
					"read_only": 1,
					"depends_on": "custom_regret_email_sent",
				},
				{
					"fieldname": "custom_ai_analysis_summary",
					"fieldtype": "Small Text",
					"label": "AI Analysis Summary",
					"insert_after": "custom_regret_email_sent_on",
					"read_only": 1,
				},
				{
					"fieldname": "custom_ai_score_breakdown",
					"fieldtype": "Table",
					"label": "AI Score Breakdown",
					"options": "Job Applicant Score Item",
					"insert_after": "custom_ai_analysis_summary",
					"read_only": 1,
				},
			]
		}
	)

	property_setter = make_property_setter(
		"Job Applicant",
		"status",
		"options",
		JOB_APPLICANT_STATUS_OPTIONS,
		"Select",
		for_doctype=False,
	)
	# make_property_setter doesn't accept a module kwarg, but hooks.py's fixture export
	# filters Property Setter on module == "Fanaka App" — without this the option never
	# ships to another site. See specs/recruitment_ai_screening.md Phase 1.
	property_setter.db_set("module", "Fanaka App", update_modified=False)
