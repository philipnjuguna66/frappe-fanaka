import frappe

from frappe.integrations.oauth2_logins import custom


@frappe.whitelist()
def update_clearance_date(journal_name):
    journal = frappe.get_doc('Journal Entry', journal_name)
    journal.db_set("clearance_date", journal.posting_date)

@frappe.whitelist(allow_guest=True)
def login_via_custom_oauth(code=None, state=None):
    custom(code, state)
