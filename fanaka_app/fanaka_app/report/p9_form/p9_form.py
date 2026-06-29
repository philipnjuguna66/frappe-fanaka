# Copyright (c) 2026, Fanaka Real Estate Ltd. and contributors
# P9 Form (KRA Tax Deduction Card) - Script Report.

from frappe import _

from fanaka_app.api.p9 import get_p9_records


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()

	if not filters.get("employee") or not filters.get("year"):
		return columns, []

	report = get_p9_records(filters.get("employee"), filters.get("year"), filters.get("company"))

	data = list(report["months"])
	data.append({"is_total": 1, **report["totals"]})

	return columns, data


def get_columns():
	money = {"fieldtype": "Currency", "width": 110}
	return [
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 90},
		{"label": _("Basic Salary"), "fieldname": "basic", **money},
		{"label": _("Benefits"), "fieldname": "benefits", **money},
		{"label": _("Total Gross"), "fieldname": "gross", **money},
		{"label": _("NSSF"), "fieldname": "nssf", **money},
		{"label": _("NHIF"), "fieldname": "nhif", **money},
		{"label": _("SHIF"), "fieldname": "shif", **money},
		{"label": _("AHL"), "fieldname": "ahl", **money},
		{"label": _("Taxable Income"), "fieldname": "taxable", **money},
		{"label": _("Personal Relief"), "fieldname": "personal_relief", **money},
		{"label": _("Insurance Relief"), "fieldname": "insurance_relief", **money},
		{"label": _("Net Payee (PAYE)"), "fieldname": "paye", **money},
		{"label": _("Net Pay"), "fieldname": "net_pay", **money},
	]
