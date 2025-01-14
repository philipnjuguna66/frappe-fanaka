import frappe

from frappe.integrations.oauth2_logins import login_via_oauth2


@frappe.whitelist()
def update_clearance_date(journal_name):
    journal = frappe.get_doc('Journal Entry', journal_name)
    journal.db_set("clearance_date", journal.posting_date)




@frappe.whitelist()
def submit_leave(name):
    doc = frappe.get_doc("Leave Application", name)
    doc.submit()

    return doc.as_dict()