import frappe

@frappe.whitelist()
def update_clearance_date(journal_name):
    journal = frappe.get_doc('Journal Entry', journal_name)
    journal.db_set("clearance_date", journal.posting_date)