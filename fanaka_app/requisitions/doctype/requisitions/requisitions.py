# Copyright (c) 2025, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class Requisitions(Document):
    def on_submit(self):
        """
        This method is called when the Requisitions document is submitted.
        It creates a corresponding Journal Entry based on the requisition details.
        """
        # --- Start of Field Validation ---
        # Ensure that all necessary fields are populated before creating the Journal Entry.
        if not self.bank_account:
            frappe.throw(frappe._("Bank Account is required to create a Journal Entry."))

        if not self.expense_account:
            frappe.throw(frappe._("Expense Account is required to create a Journal Entry."))

        if not self.total_amount:
            frappe.throw(frappe._("Total Amount is required to create a Journal Entry."))

        if not self.description:
            frappe.throw(frappe._("Description is required to create a Journal Entry."))
        # --- End of Field Validation ---

        try:
            # Create a new Journal Entry document
            journal_entry = frappe.new_doc("Journal Entry")

            # Set the required fields for the Journal Entry
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.posting_date = getdate(self.posting_date)
            journal_entry.narration = self.description
            journal_entry.company = frappe.defaults.get_user_default("Company")

            # Add the debit entry (Expense Account)
            journal_entry.append("accounts", {
                "account": self.expense_account,
                "debit_in_account_currency": self.total_amount,
                "credit_in_account_currency": 0,
                "is_advance": "No",
                "reference_date" : self.reference_date,
                "posting_date" : self.posting_date,
                "cost_center": self.cost_center
            })

            # Add the credit entry (Petty Cash Account)
            journal_entry.append("accounts", {
                "account": self.bank_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": self.total_amount,
                "is_advance": "No",
                "cost_center": self.cost_center
            })

            # Insert and submit the Journal Entry
            journal_entry.insert()
            journal_entry.submit()

            # Link the created Journal Entry back to the Requisitions document
            self.db_set('journal_entry', journal_entry.name)

        except Exception as e:
            # Log any errors that occur during the process
            frappe.log_error(frappe.get_traceback(), "Journal Entry Creation Failed")
            frappe.throw(frappe._(f"Failed to create Journal Entry for Requisition Transaction {self.name}: {e}"))
