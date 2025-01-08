import frappe
from frappe.utils import date_diff, today
def pass_requirement(doc, event):
    try:
        frappe.log_error(f"leave application validations triggered for {doc.doctype} | Name: {doc.name}", "Custom Hook Log")
        if (doc.leave_type == "Annual Leave"):
            if doc.from_date:
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
            frappe.throw(
                "You cannot create a third Annual Leave application while previous ones are still in 'Open' status.")
    except Exception as e:
        frappe.log_error(f"Error in custom_before_save: {str(e)}", "Custom Hook Error")
        raise