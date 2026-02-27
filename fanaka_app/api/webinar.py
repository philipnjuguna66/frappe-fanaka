import  frappe


@frappe.whitelist(allow_guest=True)
def create_lead():
    data = frappe.local.form_dict

    # Basic validation
    required_fields = [
        "name",
        "email",
        "phone_number"
    ]

    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"{field} is required")

    create_lead = frappe.get_doc({
        "doctype": "Webinar Attendance",
        "name1": data.get("name"),
        "email": data.get("email"),
        "phone_number": data.get("phone"),
        #"country": data.get("country"),

    })

    create_lead.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "Lead submitted successfully",
        "name": create_lead.name
    }

