import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Requisitions(Document):
    def on_submit(self):
        self.create_journal_entry()

    def create_journal_entry(self):
        # This implementation assumes you have added the following fields to your Requisition doctype:
        # - is_inter_company: Checkbox to explicitly mark this as an inter-company transaction.
        # - credit_account: Link to the Account to be credited (e.g., Bank or Payable account).
        # - debit_account: Link to the Account to be debited (e.g., an Expense account).
        # - total_amount: Currency field for the transaction amount.
        # - posting_date: Date of the transaction.
        # - cost_center: (Optional) Link to a Cost Center.
        # - journal_entry: Link to Journal Entry, to store the created JE.

        if not self.credit_account or not self.debit_account:
            frappe.throw("Please ensure Credit and Debit accounts are set before submitting.")

        # Determine the companies involved from the accounts
        credit_company = frappe.db.get_value("Account", self.credit_account, "company")
        debit_company_for_expense = frappe.db.get_value("Account", self.debit_account, "company")

        # The Journal Entry is created in the company that is making the payment (credit)
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = credit_company
        je.posting_date = self.posting_date
        
        remark = f"Requisition: {self.name}"
        if self.is_inter_company:
            remark += f" (Inter-company for {debit_company_for_expense})"
        je.user_remark = remark
        
        target_debit_account = self.debit_account
        
        # Inter-company posting logic
        if self.is_inter_company and credit_company != debit_company_for_expense:
            # In an inter-company transaction, the paying company (credit_company)
            # debits a 'receivable from other company' account, not the final expense account directly.
            inter_company_receivable_account = frappe.db.get_value("Account", {
                "company": credit_company,
                "inter_company_account_actual": debit_company_for_expense,
                "is_group": 0
            }, "name")
            
            if inter_company_receivable_account:
                target_debit_account = inter_company_receivable_account
            else:
                # If no inter-company account is set up, inform the user.
                frappe.msgprint(
                    f"<b>Warning:</b> No Inter-Company Receivable account found in '{credit_company}' "
                    f"for '{debit_company_for_expense}'. Posting directly to the expense account. "
                    "Please configure an inter-company account in the Chart of Accounts for proper accounting."
                )

        # Debit Entry
        je.append("accounts", {
            "account": target_debit_account,
            "debit_in_account_currency": flt(self.total_amount),
            "cost_center": self.cost_center,
        })
        
        # Credit Entry
        je.append("accounts", {
            "account": self.credit_account,
            "credit_in_account_currency": flt(self.total_amount),
            "cost_center": self.cost_center,
        })
        
        je.insert(ignore_permissions=True)
        je.submit()
        
        # Link the Journal Entry back to the Requisition
        self.db_set("journal_entry", je.name)
        frappe.msgprint(f"Journal Entry <a href='/app/journal-entry/{je.name}'>{je.name}</a> created successfully.")

    def on_cancel(self):
        if self.journal_entry:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                if je.docstatus == 1:  # If submitted
                    je.cancel()
                    frappe.msgprint(f"Journal Entry <a href='/app/journal-entry/{je.name}'>{je.name}</a> has been cancelled.")
                elif je.docstatus == 0:  # If draft
                    frappe.delete_doc("Journal Entry", self.journal_entry)
                    frappe.msgprint(f"Draft Journal Entry {self.journal_entry} has been deleted.")
            except frappe.DoesNotExistError:
                pass # Journal entry already deleted

            self.db_set("journal_entry", None)