# fanaka_app/notification/sms.py

import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms


def normalize_phone(number):
    """Normalize to 2547xxxxxxxx format or return None"""
    if not number:
        return None
    
    digits = re.sub(r'\D', '', str(number).strip())
    
    if digits.startswith('0'):
        digits = '254' + digits[1:]
    elif digits.startswith(('7', '1')) and len(digits) == 9:
        digits = '254' + digits
    elif digits.startswith('+'):
        digits = digits[1:]
    
    # Final validation: exactly 12 digits starting with 254
    if len(digits) == 12 and digits.startswith('254'):
        return digits
    
    return None


def send_notification_sms(doc, method):
    """
    Hook: Send SMS from Notification using ONLY custom_additional_sms_numbers.
    Safe – does not crash document save.
    Only triggers when the notification is actually sent.
    """
    if doc.doctype != "Notification":
        return

    # Skip if no message
    if not doc.message:
        frappe.log_error("Notification has no message content", "SMS Notification - Empty Message")
        return

    # Get numbers from your custom field only
    raw_input = doc.get("custom_additional_sms_numbers") or ""
    if not raw_input.strip():
        frappe.log_error("No numbers in custom_additional_sms_numbers", "SMS Notification - No Recipients")
        return

    raw_numbers = [n.strip() for n in raw_input.split(",") if n.strip()]

    valid_phones = []
    invalid_numbers = []

    for raw in raw_numbers:
        cleaned = normalize_phone(raw)
        if cleaned:
            valid_phones.append(cleaned)
        else:
            invalid_numbers.append(raw)

    if invalid_numbers:
        frappe.log_error(
            f"Skipped invalid numbers in Notification {doc.name}: {', '.join(invalid_numbers)}",
            "SMS Notification - Invalid Numbers"
        )

    if not valid_phones:
        frappe.log_error("No valid phone numbers after normalization", "SMS Notification - No Valid")
        return

    try:
        send_sms(
            receiver_list=valid_phones,
            msg=doc.message,
            sender_name="Fanaka_Ltd"
            success_msg="SMS sent successfully"
        )

        # Success log
        frappe.log_error(
            f"SMS sent from Notification {doc.name} to {len(valid_phones)} numbers: {', '.join(valid_phones)}",
            "SMS Notification - Success"
        )

        # Optional: mark success in custom field (create field sms_status first)
        if hasattr(doc, "sms_status"):
            doc.sms_status = "Sent"
            doc.save(ignore_permissions=True)

    except Exception as e:
        error_msg = f"SMS failed for Notification {doc.name}\n{frappe.get_traceback()}"
        frappe.log_error(error_msg, "SMS Notification - Failed")

        # Optional: mark failure
        if hasattr(doc, "sms_status"):
            doc.sms_status = "Failed"
            doc.save(ignore_permissions=True)

        # Optional: notify admin via email (uncomment if needed)
        # frappe.sendmail(
        #     recipients=["admin@yourdomain.com"],
        #     subject=f"SMS Failure - Notification {doc.name}",
        #     message=error_msg
        # )