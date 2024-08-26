import frappe
import requests
import json

def cancel_linked_journal_entry(doc, method):

    try:
        journal_entry = frappe.get_all("Journal Entry", filters={"title": doc.name}, fields=["name"])
        if journal_entry:
            journal_entry_name = journal_entry[0]["name"]

            cancel_journal_entry(journal_entry_name)
        else:
            frappe.log_error(f"No Journal Entry found with title {doc.name}.")
    except Exception as e:
        frappe.log_error(f"Error canceling Journal Entry for {doc.name}: {str(e)}")

def cancel_journal_entry(journal_entry_name):
    journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
    if journal_entry.docstatus == 1:
        journal_entry.cancel()
        frappe.db.commit()
    else:
        frappe.msgprint(f"Journal Entry {journal_entry_name} is not submitted and cannot be canceled.")