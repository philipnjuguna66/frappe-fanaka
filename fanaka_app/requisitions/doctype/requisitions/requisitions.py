import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Requisitions(Document):
    def on_submit(self):
        self.create_journal_entry()

    def create_journal_entry(self):
        if not self.bank_account or not self.expense_account:
            frappe.throw("Please ensure Bank Account and Expense Account are set before submitting.")

        # Get Company for both accounts
        bank_company = frappe.db.get_value("Account", self.bank_account, "company")
        expense_company = frappe.db.get_value("Account", self.expense_account, "company")
        
        # Build Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Bank Entry"
        je.company = bank_company
        je.posting_date = self.posting_date
        je.cheque_no = self.reference
        je.cheque_date = self.reference_date
        
        remark = f"Requisition Payment: {self.name}. Pay To: {self.pay_to or 'N/A'}"
        if bank_company != expense_company:
            remark += f" (Inter-company for {expense_company})"
        
        je.user_remark = remark
        
        # Logic for Inter-company Posting
        target_debit_account = self.expense_account
        
        if bank_company != expense_company:
            # Look for an Inter-company Account (Asset/Liability) in the PAYING company
            # Usually named something like "Due from [Company B]"
            inter_company_account = frappe.db.get_value("Account", {
                "company": bank_company,
                "inter_company_account_actual": expense_company, # Standard ERPNext field if configured
                "is_group": 0
            }, "name")
            
            if inter_company_account:
                target_debit_account = inter_company_account
            else:
                # Fallback: post to expense but warn, or you can create a custom field for "Inter-company Bridge Account"
                frappe.msgprint(f"<b>Warning:</b> No Inter-company bridge account found for {expense_company} in {bank_company}. Posting directly to the selected expense account.")

        # Debit Entry
        je.append("accounts", {
            "account": target_debit_account,
            "debit_in_account_currency": flt(self.total_amount),
            "cost_center": self.cost_center,
            "user_remark": self.description
        })
        
        # Credit Entry (Bank/Cash)
        je.append("accounts", {
            "account": self.bank_account,
            "credit_in_account_currency": flt(self.total_amount),
            "cost_center": self.cost_center
        })
        
        je.insert()
        je.submit()
        
        # Link back to Requisition
        self.db_set("journal_entry", je.name)
        frappe.msgprint(f"Journal Entry <a href='/app/journal-entry/{je.name}'>{je.name}</a> created.")

    def on_cancel(self):
        if self.journal_entry:
            je_status = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
            if je_status == 1:
                frappe.throw(f"Cannot cancel requisition. Please cancel Journal Entry {self.journal_entry} first.")
            elif je_status == 0:
                frappe.delete_doc("Journal Entry", self.journal_entry)
                self.db_set("journal_entry", "")