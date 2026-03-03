import  frappe


@frappe.whitelist(allow_guest=True)
def create_lead():
    data = frappe.local.form_dict

    # Basic validation
    required_fields = [
        "lead_name",
        "scheduled_at",
        "phone_number",
        "location",
    ]

    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"{field} is required")

    create_lead = frappe.get_doc({
        "doctype": "Website Lead",
        "lead_name": data.get("lead_name"),
        "phone_number": data.get("phone_number"),
        "location": data.get("location"),
        "scheduled_at": data.get("scheduled_at"),
        #"country": data.get("country"),

    })

    create_lead.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "Lead submitted successfully",
        "name": create_lead.lead_name
    }

