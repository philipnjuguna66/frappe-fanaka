import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class ProjectExpenses(Document):
    def validate(self):
        if not self.expense_date:
            self.expense_date = today()

        if not self.payment_date:
            self.payment_date = self.expense_date

        if self.project and not self.branch:
            project_cc = frappe.db.get_value("Project", self.project, "cost_center")
            if project_cc:
                self.branch = project_cc

        if self.expense_type and not self.expense_account:
            default_acc = frappe.db.get_value(
                "Expense Type", self.expense_type, "default_expense_account"
            )
            if default_acc:
                self.expense_account = default_acc

        if flt(self.amount) <= 0:
            frappe.throw("Amount must be greater than zero")

    def on_submit(self):
        company = self.company or frappe.defaults.get_user_default("Company")
        if not company:
            frappe.throw("Company not set on the document or as a default")

        for account in [self.expense_account, self.bank_account]:
            if not frappe.db.exists("Account", account):
                frappe.throw(f"Account {account} does not exist")
            acc_company = frappe.db.get_value("Account", account, "company")
            if acc_company != company:
                frappe.throw(f"Account {account} does not belong to company {company}")

        expense_amount = flt(self.amount)

        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.payment_date or self.expense_date or today()
        je.company = company
        je.voucher_type = "Journal Entry"
        je.remark = (
            f"Project Expense {self.name} for {self.project_name or self.project}"
            + (f" - Supplier: {self.supplier}" if self.supplier else "")
        )

        if self.reference_code:
            je.cheque_no = self.reference_code
            je.cheque_date = je.posting_date

        if self.supplier:
            je.party_type = "Supplier"
            je.party = self.supplier

        je.append(
            "accounts",
            {
                "account": self.expense_account,
                "debit_in_account_currency": expense_amount,
                "credit_in_account_currency": 0,
                "project": self.project,
                "cost_center": self.branch,
            },
        )

        je.append(
            "accounts",
            {
                "account": self.bank_account,
                "credit_in_account_currency": expense_amount,
                "debit_in_account_currency": 0,
                "project": self.project,
                "cost_center": self.branch,
            },
        )

        je.flags.ignore_permissions = True
        je.set_total_debit_credit()
        je.insert()
        je.submit()

        self.db_set("journal_entry", je.name)
        self.db_set("status", "Submitted")

        frappe.msgprint(f"Journal Entry {je.name} created")

    def on_cancel(self):
        if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.flags.ignore_permissions = True
                je.cancel()
            try:
                frappe.delete_doc("Journal Entry", je.name, force=1)
            except Exception:
                pass

        self.db_set("journal_entry", None)
        self.db_set("status", "Cancelled")
