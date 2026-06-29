# Copyright (c) 2026, Fanaka Real Estate Ltd. and contributors
# P9 (KRA Tax Deduction Card) data builder.
#
# Independent of navari_csf_ke. Pulls figures straight from submitted Salary
# Slips and maps salary components to KRA P9 columns using keyword matching so
# it keeps working regardless of how components are named/abbreviated.

import calendar
import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

# Statutory monthly personal relief (KShs). Used as fallback when no explicit
# "Personal Relief" salary component exists but PAYE was charged.
DEFAULT_PERSONAL_RELIEF = 2400.0

# Keyword -> P9 bucket. Matched (case-insensitive) against both the salary
# component name and its abbreviation. First matching bucket wins.
DEDUCTION_KEYWORDS = {
	"nssf": ["nssf", "national social security"],
	"shif": ["shif", "shia", "social health"],
	"nhif": ["nhif", "national hospital", "hospital insurance"],
	"ahl": ["ahl", "affordable housing", "housing levy"],
	"paye": ["paye", "p.a.y.e", "income tax", "pay as you earn"],
	"insurance_relief": ["insurance relief"],
	"personal_relief": ["personal relief"],
}

MONTHS = list(calendar.month_name)[1:]  # ["January", ... "December"]


def _match_bucket(*names):
	"""Return the P9 bucket keyword for a component, or None."""
	hay = " ".join(n for n in names if n).lower()
	# compact form ignores dots/spaces so "N.S.S.F" matches "nssf"
	compact = re.sub(r"[^a-z0-9]", "", hay)
	for bucket, keywords in DEDUCTION_KEYWORDS.items():
		for kw in keywords:
			kw_compact = re.sub(r"[^a-z0-9]", "", kw)
			if kw in hay or kw_compact in compact:
				return bucket
	return None


def _blank_row(month_label):
	return {
		"month": month_label,
		"basic": 0.0,
		"benefits": 0.0,
		"gross": 0.0,
		"nssf": 0.0,
		"nhif": 0.0,
		"shif": 0.0,
		"ahl": 0.0,
		"taxable": 0.0,
		"personal_relief": 0.0,
		"insurance_relief": 0.0,
		"paye": 0.0,
		"net_pay": 0.0,
	}


def get_p9_records(employee, year, company=None):
	"""Build the full P9 dataset for one employee + calendar year.

	Returns dict: {employer, employee, year, months: [12 rows], totals}.
	"""
	if not employee:
		frappe.throw(_("Employee is required"))
	if not year:
		frappe.throw(_("Year is required"))
	year = int(year)

	emp = frappe.db.get_value(
		"Employee",
		employee,
		["employee_name", "employee_number", "tax_id", "national_id", "company"],
		as_dict=True,
	)
	if not emp:
		frappe.throw(_("Employee {0} not found").format(employee))

	company = company or emp.company
	comp = frappe.db.get_value("Company", company, ["company_name", "tax_id"], as_dict=True) or {}

	filters = {
		"docstatus": 1,
		"employee": employee,
		"end_date": ["between", [f"{year}-01-01", f"{year}-12-31"]],
	}
	if company:
		filters["company"] = company

	slips = frappe.get_all(
		"Salary Slip",
		filters=filters,
		fields=["name", "start_date", "end_date", "gross_pay", "net_pay"],
		order_by="end_date asc",
	)

	rows = [_blank_row(m) for m in MONTHS]
	has_personal_relief_component = False
	paye_charged_any = False

	for slip in slips:
		month_idx = getdate(slip.end_date).month - 1
		row = rows[month_idx]
		row["gross"] = flt(row["gross"]) + flt(slip.gross_pay)
		row["net_pay"] = flt(row["net_pay"]) + flt(slip.net_pay)

		# Earnings: basic vs everything-else (benefits/allowances).
		earnings = frappe.get_all(
			"Salary Detail",
			filters={"parent": slip.name, "parentfield": "earnings"},
			fields=["salary_component", "abbr", "amount"],
		)
		for e in earnings:
			if "basic" in (e.salary_component or "").lower():
				row["basic"] += flt(e.amount)
			else:
				row["benefits"] += flt(e.amount)

		# Deductions: bucket into P9 columns.
		deductions = frappe.get_all(
			"Salary Detail",
			filters={"parent": slip.name, "parentfield": "deductions"},
			fields=["salary_component", "abbr", "amount"],
		)
		for d in deductions:
			bucket = _match_bucket(d.salary_component, d.abbr)
			if bucket == "paye":
				row["paye"] += flt(d.amount)
				paye_charged_any = True
			elif bucket == "personal_relief":
				row["personal_relief"] += flt(d.amount)
				has_personal_relief_component = True
			elif bucket in ("nssf", "nhif", "shif", "ahl", "insurance_relief"):
				row[bucket] += flt(d.amount)
			# unmatched deductions are ignored for P9 purposes

		# Taxable income = gross - allowable statutory deductions.
		allowable = row["nssf"] + row["nhif"] + row["shif"] + row["ahl"]
		row["taxable"] = max(flt(row["gross"]) - allowable, 0.0)

		# Fallback personal relief: KRA grants 2,400/month when PAYE applies.
		if not has_personal_relief_component and flt(row["paye"]) > 0:
			row["personal_relief"] = DEFAULT_PERSONAL_RELIEF

	totals = _blank_row("Totals")
	for row in rows:
		for k in totals:
			if k == "month":
				continue
			totals[k] = flt(totals[k]) + flt(row[k])

	return {
		"employer": {"name": comp.get("company_name") or company, "pin": comp.get("tax_id") or ""},
		"employee": {
			"name": emp.employee_name,
			"pin": emp.tax_id or "",
			"id": emp.employee_number or employee,
			"national_id": emp.national_id or "",
		},
		"year": year,
		"months": rows,
		"totals": totals,
		"has_data": bool(slips),
	}


@frappe.whitelist()
def get_p9_data(employee, year, company=None):
	"""Whitelisted wrapper used by the report's 'Print KRA P9 Card' button."""
	return get_p9_records(employee, year, company)
