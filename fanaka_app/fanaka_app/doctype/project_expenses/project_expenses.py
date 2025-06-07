import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

class ProjectExpenses(Document):
    def on_submit(self):
        try:
            # Validate company
            company = frappe.defaults.get_user_default("Company")
            if not company:
                frappe.throw("Default Company not set. Please set a default company.")

            # Basic validations
            if not self.project:
                frappe.throw("Project is mandatory")
            if not self.expense_account:
                frappe.throw("Expense Account is mandatory")
            if not self.bank_account:
                frappe.throw("Bank Account is mandatory")
            if not self.payment_date:
                frappe.throw("Payment Date is mandatory")
            if not self.supplier:
                frappe.throw("Supplier is mandatory")

            # Validate accounts exist and are valid
            for account in [self.expense_account, self.bank_account]:
                if not frappe.db.exists("Account", account):
                    frappe.throw(f"Account {account} does not exist")
                
                # Check if account belongs to the company
                acc = frappe.get_doc("Account", account)
                if acc.company != company:
                    frappe.throw(f"Account {account} does not belong to company {company}")

            # Validate supplier
            if not frappe.db.exists("Supplier", self.supplier):
                frappe.throw(f"Supplier {self.supplier} does not exist")

            expense_amount = flt(self.amount)
            if expense_amount <= 0:
                frappe.throw("Amount must be greater than zero")

            # Create Journal Entry with error handling
            try:
                je = frappe.new_doc("Journal Entry")
                je.posting_date = self.payment_date
                je.company = company
                je.voucher_type = 'Journal Entry'
                je.remark = f"Project Expense for {self.project_name or self.project} - Supplier: {self.supplier}"
                
                # Add reference details if available
                if self.reference_code:
                    je.cheque_no = self.reference_code
                    je.cheque_date = self.payment_date

                # Add supplier details
                je.party_type = "Supplier"
                je.party = self.supplier

                # Append expense entry
                je.append("accounts", {
                    "account": self.expense_account,
                    "debit_in_account_currency": expense_amount,
                    "credit_in_account_currency": 0,
                    "project": self.project,
                   # "party_type": "Supplier",
                   # "party": self.supplier,
                    "cost_center": self.branch if hasattr(self, 'cost_center') else None
                })

                # Append bank entry
                je.append("accounts", {
                    "account": self.bank_account,
                    "credit_in_account_currency": expense_amount,
                    "debit_in_account_currency": 0,
                    "project": self.project,
                    #"party_type": "Supplier",
                   # "party": self.supplier,
                    "cost_center": self.branch if hasattr(self, 'cost_center') else None
                })

                # Insert with additional validations
                je.flags.ignore_permissions = True
                je.set_total_debit_credit()
                je.validate_reference_doc()
                je.insert()
                
                # Submit the journal entry
                je.submit()
                
                frappe.msgprint(f"Journal Entry {je.name} created successfully")

            except Exception as e:
                frappe.db.rollback()
                frappe.throw(f"Failed to create Journal Entry: {str(e)}")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Expenses: Journal Entry Creation Error")
            frappe.throw(f"Error creating Journal Entry: {str(e)}")