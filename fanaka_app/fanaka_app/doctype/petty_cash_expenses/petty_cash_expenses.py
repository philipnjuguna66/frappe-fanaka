# -*- coding: utf-8 -*-
# Copyright (c) 2025, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.model.document import Document

class PettyCashExpenses(Document):
    def before_save(self):
        """
        This method is triggered before a new 'Petty Cash Transaction' document is inserted.
        If the document is an amendment, it ensures the 'journal_entry' field is cleared.
        The primary clearing for amendment validation is now handled by a client script.
        """
        if self.amended_from:
            self.journal_entry = None

    def on_submit(self):
        """
        This method is triggered when a 'Petty Cash Transaction' document is submitted.
        It creates a new 'Journal Entry' based on the details of the petty cash transaction,
        including the cost center, and then links the created Journal Entry back to this document.
        """
        try:
            # Create a new Journal Entry document
            journal_entry = frappe.new_doc("Journal Entry")

            # Set the required fields for the Journal Entry
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.posting_date = getdate(self.expense_date) # Use the expense date from petty cash
            journal_entry.narration = self.description if self.description else f"Petty Cash Expense for {self.expense_account_name}"
            journal_entry.company = frappe.defaults.get_user_default("Company") # Set company, adjust if needed

            # Add the debit entry (Expense Account)
            journal_entry.append("accounts", {
                "account": self.expense_account,
                "debit_in_account_currency": self.amount,
                "credit_in_account_currency": 0,
                "is_advance": "No",
                "cost_center": self.cost_center # Add cost center to the debit entry
            })

            # Add the credit entry (Petty Cash Account)
            journal_entry.append("accounts", {
                "account": self.petty_cash_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": self.amount,
                "is_advance": "No",
                "cost_center": self.cost_center # Add cost center to the credit entry
            })

            # Insert and submit the Journal Entry
            journal_entry.insert()
            journal_entry.submit()

            # Link the created Journal Entry back to the Petty Cash Transaction
            self.db_set('journal_entry', journal_entry.name)
          
        except Exception as e:
            # Log any errors that occur during the process
            frappe.log_error(frappe.get_traceback(), "Petty Cash Journal Entry Creation Failed")
            frappe.throw(f"Failed to create Journal Entry for Petty Cash Transaction {self.name}: {e}")

    def on_cancel(self):
        """
        This method is triggered when a 'Petty Cash Transaction' document is cancelled.
        It attempts to cancel the linked 'Journal Entry'.
        """
        if self.journal_entry:
            try:
                # Get the linked Journal Entry document
                journal_entry_doc = frappe.get_doc("Journal Entry", self.journal_entry)

                # Only cancel if the Journal Entry is submitted
                if journal_entry_doc.docstatus == 1: # docstatus 1 means submitted
                    journal_entry_doc.cancel()
                    frappe.msgprint(f"Journal Entry {self.journal_entry} cancelled successfully due to cancellation of Petty Cash Transaction {self.name}.")
                else:
                    frappe.msgprint(f"Journal Entry {self.journal_entry} is not submitted, no action taken on cancellation of Petty Cash Transaction {self.name}.")

            except frappe.DoesNotExistError:
                frappe.msgprint(f"Linked Journal Entry {self.journal_entry} not found for Petty Cash Transaction {self.name}.")
                frappe.log_error(frappe.get_traceback(), f"Linked Journal Entry {self.journal_entry} not found")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Journal Entry Cancellation Failed")
                frappe.throw(f"Failed to cancel Journal Entry {self.journal_entry}: {e}")
        else:
            frappe.msgprint(f"No Journal Entry linked to Petty Cash Transaction {self.name}. No action taken.")

