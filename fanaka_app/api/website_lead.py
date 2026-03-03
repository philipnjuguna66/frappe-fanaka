import frappe
from frappe.utils import get_datetime

@frappe.whitelist(allow_guest=True)
def create_lead():
    data = frappe.local.form_dict

    required_fields = [
        "lead_name",
        "scheduled_at",
        "phone_number",
        "location",
    ]

    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"{field} is required")

    # Convert scheduled_at to proper datetime object
    try:
        scheduled_at = get_datetime(data.get("scheduled_at"))
    except Exception:
        frappe.throw("Invalid date format for scheduled_at. Use YYYY-MM-DD HH:MM:SS")

    lead = frappe.get_doc({
        "doctype": "Website Lead",
        "lead_name": data.get("lead_name"),
        "phone": data.get("phone_number"),
        "location": data.get("location"),
        "scheduled_at": scheduled_at,
    })

    lead.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "Lead submitted successfully",
        "name": lead.name
    }