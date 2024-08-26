# Copyright (c) 2024, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from fanaka_app.helpers import update_clearance_date

from fanaka_app.cancel_journal_entry import cancel_journal_entry

class Requisition(Document):
    def on_change(self):
        pass


    def on_submit(self):
        if not self.paying_account:
            frappe.throw(f" Paying account cannot be null")
        if not self.paying_date:
            frappe.throw(f" Paying Date cannot be null")
        if not self.expense_account:
            frappe.throw(f" Expense account cannot be null")
        if not self.payment_mode:
            frappe.throw(f" payment Mode cannot be null")

        # Create a journal entry

        doc = self
        journal_entry = frappe.new_doc('Journal Entry')
        journal_entry.posting_date = doc.paying_date
        journal_entry.voucher_type = 'Journal Entry'
        journal_entry.remark = doc.description
        journal_entry.title = doc.name
        journal_entry.total_amount = doc.total_amount
        journal_entry.mode_of_payment = doc.payment_mode

        journal_entry.append('accounts', {
            'account': doc.paying_account,
            'debit_in_account_currency': 0,
            'credit_in_account_currency': doc.total_amount,
            'cost_center': doc.cost_center,

        })

        journal_entry.append('accounts', {
            'account': doc.expense_account,
            'debit_in_account_currency': doc.total_amount,
            'credit_in_account_currency': 0,
            'cost_center': doc.cost_center,
        })

        journal_entry.save(ignore_permissions=True)
        journal_entry.submit()
        update_clearance_date(journal_entry.name)

    def calculate_total(self):
        frappe.throw(self)

    def on_cancel(self):
        journal_entries = frappe.get_all("Journal Entry", filters={"title": self.name}, fields=["name"])

        if journal_entries:
            journal_entry_name = journal_entries[0]["name"]
            cancel_journal_entry(journal_entry_name)
        else:
            frappe.log_error(f"No Journal Entry found with title {self.name}.")


