# fanaka_app/notification/sms.py

import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms


def normalize_phone(number):
    """Return 2547xxxxxxxx or None"""
    if not number:
        return None
    digits = re.sub(r'\D', '', str(number).strip())
    if digits.startswith('0'):
        digits = '254' + digits[1:]
    elif digits.startswith(('7', '1')) and len(digits) == 9:
        digits = '254' + digits
    elif digits.startswith('254') and len(digits) == 12:
        pass
    else:
        digits = digits.lstrip('+')
        if not (digits.startswith('254') and len(digits) == 12):
            return None
    return digits if len(digits) == 12 and digits.startswith('254') else None


def send_notification_sms(doc, method):
    """
    Hook: send SMS from Notification using custom_additional_sms_numbers
    Safe – doesn't crash document save
    """
    if doc.doctype != "Notification":
        return

    if not doc.message:
        frappe.log_error("Notification has no message", "SMS Notification - Empty Message")
        return
    raw_input = doc.get("custom_additional_sms_numbers") or ""
    if not raw_input.strip():
        return  # nothing to do

    raw_numbers = [n.strip() for n in raw_input.split(",") if n.strip()]

    valid_phones = []
    invalid = []

    for raw in raw_numbers:
        cleaned = normalize_phone(raw)
        if cleaned:
            valid_phones.append(cleaned)
        else:
            invalid.append(raw)

    if invalid:
        frappe.log_error(
            f"Skipped invalid numbers in Notification {doc.name}: {', '.join(invalid)}",
            "SMS Notification - Invalid Numbers"
        )

    if not valid_phones:
        return

    try:
        send_sms(
            receiver_list=valid_phones,
            msg=doc.message,
            # sender_name="Fanaka"   # if configured in SMS Settings
        )

        frappe.log_error(
            f"SMS sent from Notification {doc.name} to {len(valid_phones)} numbers: {', '.join(valid_phones)}",
            "SMS Notification - Success"
        )

    except Exception as e:
        frappe.log_error(
            f"SMS failed for Notification {doc.name}\n{frappe.get_traceback()}",
            "SMS Notification - Failed"
        )
        # Optional: add a custom field "sms_status" = "Failed" and save again (carefully)