import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

class Requisitions(Document):
    def before_insert(self):
        if not self.requisition_owner:
            self.requisition_owner = frappe.session.user
        if not self.status:
            self.status = "pending"    

    def on_submit(self):
        self.make_journal_entry()

    def on_cancel(self):
        if self.journal_entry:
            # Check if JE is already cancelled
            docstatus = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
            if docstatus == 1:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                je.cancel()

    def make_journal_entry(self):
        # Determine Voucher Type based on Inter-Company checkbox
        voucher_type = "Journal Entry"
        if self.is_inter_company:
            voucher_type = "Inter Company Journal Entry"
        
        # Initialize Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = voucher_type
       # je.company = self.company # Ensure this field exists in your DocType
        je.posting_date = self.posting_date
        je.cheque_no = self.reference
        je.cheque_date = self.reference_date
        je.user_remark = self.description

        # Add Debit Row
        je.append("accounts", {
            "account": self.debit_account,
            "debit_in_account_currency": self.total_amount,
            "cost_center": self.cost_center,
            "user_remark": _("Requisition Debit")
        })

        # Add Credit Row
        je.append("accounts", {
            "account": self.credit_account,
            "credit_in_account_currency": self.total_amount,
            "cost_center": self.cost_center,
            "user_remark": _("Requisition Credit")
        })

        je.insert()
        je.submit()

        # Link the JE back to this Requisition
        self.db_set("journal_entry", je.name)
        frappe.msgprint(_("Journal Entry {0} created").format(frappe.bold(je.name)))