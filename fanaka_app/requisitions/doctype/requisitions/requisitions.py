import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Requisitions(Document):

    def before_insert(self):
        # Set default posting date to today if not set
        if not self.requisition_owner:
            self.requisition_owner = frappe.session.user