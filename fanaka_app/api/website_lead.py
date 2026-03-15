import frappe
from frappe.utils import get_datetime
import re

from frappe.email.doctype.notification.notification import Notification

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

# fanaka_app/api/website_lead.py

# fanaka_app/api/website_lead.py

import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms


@frappe.whitelist()
def resend_lead_notification_sms(lead_name):
    try:
        lead = frappe.get_doc("Website Lead", lead_name)

        # Find active SMS Notifications for Website Lead
        notifications = frappe.get_all(
            "Notification",
            filters={
                "document_type": "Website Lead",
                "channel": "SMS",
                "enabled": 1,
                "event": ["in", ["New", "Save", "Submit"]]   # adjust as needed
            },
            fields=["name"]
        )

        if not notifications:
            return {
                "status": "error",
                "message": "No active SMS notifications found for Website Lead"
            }

        sent_count = 0
        errors = []

        for notif in notifications:
            notification = frappe.get_doc("Notification", notif.name)

            # Get numbers from this notification's custom field
            raw_input = notification.get("custom_additional_sms_numbers") or ""
            if not raw_input.strip():
                continue

            valid_phones = []
            for raw in [n.strip() for n in raw_input.split(",") if n.strip()]:
                cleaned = normalize_phone(raw)  # your normalize function
                if cleaned:
                    valid_phones.append(cleaned)

            if not valid_phones:
                continue

            # Prepare context for Jinja rendering
            context = {"doc": lead, "frappe": frappe}

            # Render message correctly
            try:
                template = notification.get_template()  # ← this is the correct method
                message = template.render(context)
            except Exception as render_err:
                errors.append(f"Failed to render message for {notification.name}: {str(render_err)}")
                continue

            try:
                send_sms(
                    receiver_list=valid_phones,
                    msg=message
                )
                sent_count += 1
            except Exception as send_err:
                errors.append(f"SMS send failed for {notification.name}: {str(send_err)}")
                frappe.log_error(frappe.get_traceback(), f"Resend failed - {notification.name}")

        if sent_count == 0:
            return {
                "status": "error",
                "message": "No SMS was sent (check numbers, template, or gateway)"
            }

        msg = f"SMS resent via {sent_count} notification(s)"
        if errors:
            msg += f"\nErrors: {'; '.join(errors)}"

        return {
            "status": "success",
            "message": msg
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Resend Lead SMS Failed")
        return {
            "status": "error",
            "message": str(e)
        }