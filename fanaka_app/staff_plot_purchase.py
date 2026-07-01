"""Setup for staff plot purchases funded by salary deductions.

Creates:
* Salary Component ``Staff Plot Purchase`` (Deduction) — the payroll deduction
  used for a staff member's plot instalment.
* Custom field ``custom_plot`` on Additional Salary — links the deduction to the
  Plot being paid for, so the on_submit hook can post the payment to mis-erp.

Idempotent. Run with::

    bench --site <site> execute fanaka_app.staff_plot_purchase.setup
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SALARY_COMPONENT = "Staff Plot Purchase"


def setup():
    _ensure_salary_component(SALARY_COMPONENT)

    create_custom_fields({
        "Additional Salary": [
            {
                "fieldname": "custom_plot",
                "label": "Plot",
                "fieldtype": "Link",
                "options": "Plot",
                "insert_after": "salary_component",
                "description": "Plot this salary deduction pays for; the payment is posted to mis-erp on submit.",
            },
            {
                "fieldname": "custom_payment_method",
                "label": "Payment Method (mis-erp)",
                "fieldtype": "Select",
                # mis-erp PaymentMethod names; keep in sync with the mis-erp list.
                "options": "Salary\nEquity Bank - 1440269339566\nNCBA BANK\nKCB BANK\nMpesa Till (943922)",
                "default": "Salary",
                "insert_after": "custom_plot",
                "description": "Which mis-erp payment method the recorded payment is booked under.",
            },
        ],
    })

    frappe.db.commit()
    return {"salary_component": SALARY_COMPONENT, "custom_field": "Additional Salary-custom_plot"}


def _ensure_salary_component(name):
    if frappe.db.exists("Salary Component", name):
        return

    frappe.get_doc({
        "doctype": "Salary Component",
        "salary_component": name,
        "salary_component_abbr": "SPP",
        "type": "Deduction",
        "is_tax_applicable": 0,
    }).insert()
