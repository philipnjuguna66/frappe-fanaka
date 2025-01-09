import frappe
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from frappe.utils import date_diff, today

class FanakaLeaveApplication(LeaveApplication):
    def validate(self):
        # Call the parent validate method to retain existing logic
        super().validate()

        try:
            frappe.log_error(f"leave application validations triggered for {self.leave_type} | Name: {self.name}", "Custom Hook Log")
            if (self.leave_type.upper() == "ANNUAL LEAVE"):
                if self.from_date:
                    days_to_leave_start = date_diff(self.from_date, today())
                    if days_to_leave_start < 3:
                        frappe.throw("You can only apply for Annual Leave at least 3 days in advance.")


            # Check for existing leave applications in "Draft" status
            existing_draft_leaves = frappe.db.count(
                'Leave Application',
                filters={
                    'employee': self.employee,
                    'status': 'Open'
                }
            )
            if existing_draft_leaves >= 1:
                frappe.throw("You cannot create a third Annual Leave application while previous ones are still in 'Open' status.")
        except Exception as e:
            frappe.log_error(f"Error in custom_before_save: {str(e)}", "Custom Hook Error")
            raise
