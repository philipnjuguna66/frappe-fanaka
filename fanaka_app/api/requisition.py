# [2026-03-18 11:57:45]
import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def initiate_payment(docname):
    """
    Sets the initiation metadata for a Requisition.
    """
    doc = frappe.get_doc("Requisitions", docname)
    
    # Validation: Prevent re-initiation
    if doc.initiated_at:
        frappe.throw(_("Payment for this Requisition has already been initiated."))
    
    # Update fields
    doc.db_set('initiated_at', now_datetime())
    doc.db_set('initiated_by', frappe.session.user)
    
    # Add timeline log
    doc.add_comment("Info", _("Payment initiated by {0}").format(frappe.session.user))
    
    return {
        "status": "success",
        "initiated_at": doc.initiated_at,
        "initiated_by": doc.initiated_by
    }