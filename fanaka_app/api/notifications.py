import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms


def normalize_phone(number):
    """
    Normalize Kenyan phone numbers to 2547XXXXXXXX format
    Returns None if invalid
    """
    if not number:
        return None

    digits = re.sub(r'\D', '', str(number))

    # Convert formats
    if digits.startswith('0') and len(digits) == 10:
        digits = '254' + digits[1:]
    elif len(digits) == 9 and digits.startswith(('7', '1')):
        digits = '254' + digits

    # Final validation
    if len(digits) == 12 and digits.startswith('254'):
        return digits

    return None


def send_notification_sms(doc, method=None):
    """
    Send SMS using custom numbers field ONLY.
    Safe: will never break document save.
    """

    try:
        # Only act on Notification doctype
        if doc.doctype != "Notification":
            return

        # Ensure message exists
        if not doc.message:
            frappe.log_error("Missing message", "SMS Notification")
            return

        # Get numbers from custom field
        raw_input = doc.get("custom_additional_sms_numbers") or ""

        if not raw_input.strip():
            frappe.log_error(
                f"No numbers provided in Notification {doc.name}",
                "SMS Notification"
            )
            return

        raw_numbers = [n.strip() for n in raw_input.split(",") if n.strip()]

        valid_numbers = []
        invalid_numbers = []

        for num in raw_numbers:
            cleaned = normalize_phone(num)
            if cleaned:
                valid_numbers.append(cleaned)
            else:
                invalid_numbers.append(num)

        # Log invalid numbers (but don't fail)
        if invalid_numbers:
            frappe.log_error(
                f"Invalid numbers skipped in {doc.name}: {', '.join(invalid_numbers)}",
                "SMS Notification"
            )

        if not valid_numbers:
            frappe.log_error(
                f"No valid numbers after cleaning in {doc.name}",
                "SMS Notification"
            )
            return

        # ✅ SEND SMS
        send_sms(
            receiver_list=valid_numbers,
            msg=doc.message,
            sender_name="Fanaka_Ltd"
        )

        # ✅ SUCCESS LOG
        frappe.logger().info(
            f"SMS sent ({doc.name}) → {', '.join(valid_numbers)}"
        )

        # Optional status tracking
        if hasattr(doc, "sms_status"):
            doc.db_set("sms_status", "Sent")

    except Exception:
        error = frappe.get_traceback()

        frappe.log_error(
            f"SMS failed for {doc.name}\n{error}",
            "SMS Notification"
        )

        if hasattr(doc, "sms_status"):
            doc.db_set("sms_status", "Failed")