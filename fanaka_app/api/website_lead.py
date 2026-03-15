import frappe
from frappe.utils import get_datetime
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms

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
        "scheduled_at": get_datetime(data.get("scheduled_at")),
    })

    lead.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "Lead submitted successfully",
        "name": lead.name
    }

# fanaka_app/api/website_lead.py





def normalize_phone(number):
    """Normalize to 2547xxxxxxxx or None"""
    if not number:
        return None
    digits = re.sub(r'\D', '', str(number).strip())
    if digits.startswith('0'):
        digits = '254' + digits[1:]
    elif digits.startswith(('7', '1')) and len(digits) == 9:
        digits = '254' + digits
    elif digits.startswith('+'):
        digits = digits[1:]
    return digits if len(digits) == 12 and digits.startswith('254') else None


@frappe.whitelist()
def resend_to_additional_numbers(lead_name):
    try:
        lead = frappe.get_doc("Website Lead", lead_name)

        # Get comma-separated numbers from custom field
        raw_input = lead.get("custom_additional_sms_numbers") or ""
        if not raw_input.strip():
            return {
                "status": "error",
                "message": "No numbers found in 'Additional SMS Numbers'"
            }

        raw_numbers = [n.strip() for n in raw_input.split(",") if n.strip()]

        valid_phones = []
        for raw in raw_numbers:
            cleaned = normalize_phone(raw)
            if cleaned:
                valid_phones.append(cleaned)

        if not valid_phones:
            return {
                "status": "error",
                "message": "No valid phone numbers after normalization"
            }

        # Customize the message here (or pull from a Notification)
        message = (
            f"Hello {lead.lead_name or 'Customer'}, "
            f"this is a follow-up from Fanaka Real Estate regarding your inquiry in {lead.location or 'your area'}. "
            f"We'll contact you soon at {lead.scheduled_at or 'your preferred time'}."
        )

        send_sms(
            receiver_list=valid_phones,
            msg=message,
            # sender_name="Fanaka"  # if set in SMS Settings
        )

        return {
            "status": "success",
            "message": f"SMS resent to {len(valid_phones)} additional numbers"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Resend Additional SMS Failed")
        return {
            "status": "error",
            "message": str(e)
        }