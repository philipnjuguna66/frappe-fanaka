import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms


# -----------------------------
# NORMALIZE PHONE NUMBERS
# -----------------------------
def normalize_phone(number):
    """
    Convert Kenyan numbers to 2547XXXXXXXX format
    """
    if not number:
        return None

    digits = re.sub(r'\D', '', str(number))

    if digits.startswith('0') and len(digits) == 10:
        digits = '254' + digits[1:]
    elif len(digits) == 9 and digits.startswith(('7', '1')):
        digits = '254' + digits
    elif digits.startswith('254') and len(digits) == 12:
        pass
    else:
        return None

    return digits


# -----------------------------
# EXTRACT FROM COMMA SEPARATED
# -----------------------------
def extract_numbers(raw_input):
    """
    Returns valid and invalid numbers from comma-separated input
    """
    if not raw_input:
        return [], []

    raw_numbers = [n.strip() for n in raw_input.split(",") if n.strip()]

    valid = []
    invalid = []

    for num in raw_numbers:
        cleaned = normalize_phone(num)
        if cleaned:
            valid.append(cleaned)
        else:
            invalid.append(num)

    return valid, invalid


# -----------------------------
# MAIN SMS FUNCTION (FOR LEADS)
# -----------------------------
def send_lead_sms(doc, method=None):
    """
    Trigger SMS when a Website Lead is created
    """
    try:
        frappe.logger().info("🚀 SMS Triggered for new lead")

        # -----------------------------
        # MESSAGE
        # -----------------------------
        message = f"New Lead: {doc.lead_name or 'Unknown'} - {doc.phone or 'No Phone'}"

        # -----------------------------
        # GET NUMBERS (comma-separated)
        # -----------------------------
        raw_input = doc.get("custom_additional_sms_numbers") or ""

        valid_numbers, invalid_numbers = extract_numbers(raw_input)

        # -----------------------------
        # LOG INVALID NUMBERS
        # -----------------------------
        if invalid_numbers:
            frappe.log_error(
                f"Invalid numbers skipped: {', '.join(invalid_numbers)}",
                "SMS DEBUG"
            )

        # -----------------------------
        # STOP IF NONE VALID
        # -----------------------------
        if not valid_numbers:
            frappe.log_error("No valid phone numbers found", "SMS DEBUG")
            return

        # -----------------------------
        # DEBUG FINAL NUMBERS
        # -----------------------------
        frappe.log_error(
            f"FINAL NUMBERS: {', '.join(valid_numbers)}",
            "SMS DEBUG"
        )

        # -----------------------------
        # SEND SMS
        # -----------------------------
        send_sms(
            receiver_list=valid_numbers,
            msg=message,
            sender_name="Fanaka_Ltd"
        )

        # -----------------------------
        # SUCCESS LOG
        # -----------------------------
        frappe.logger().info(
            f"✅ SMS sent to: {', '.join(valid_numbers)}"
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "SMS ERROR"
        )