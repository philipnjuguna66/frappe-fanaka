import frappe
from frappe.utils import date_diff, today

def pass_requirement(doc, event):
    if doc.get('doctype') == 'Leave Application':



        # Validate leave application date (at least 3 days in advance)
        if doc.leave_type === "Annual leave" && doc.from_date:
            days_to_leave_start = date_diff(doc.from_date, today())
            if days_to_leave_start < 3:
                frappe.throw("You can only apply for Annual Leave at least 3 days in advance.")

        # Check for existing leave applications in "Draft" status
        existing_draft_leaves = frappe.db.count(
            'Leave Application',
            filters={
                'employee': doc.employee,
                'status': 'Open'
            }
        )

        if existing_draft_leaves >= 1:
            frappe.throw("You cannot create a third Annual Leave application while previous ones are still in 'Draft' status.")
