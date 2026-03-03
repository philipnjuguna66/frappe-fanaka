import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms

def normalize_number(number):
    number = re.sub(r"\D", "", number)  # remove everything except digits

    # Kenya normalization
    if number.startswith("0"):
        number = "254" + number[1:]
    elif number.startswith("7") and len(number) == 9:
        number = "254" + number

    return number

def handle_sms_cc(doc, method=None):

    if doc.channel != "SMS":
        return

    raw_numbers = doc.custom_additional_sms_numbers.split(",")
    print(doc.custom_additional_sms_numbers)

    numbers = []
    for n in raw_numbers:
        print(doc.custom_additional_sms_numbers)
        cleaned = normalize_number(n.strip())

        # STRICT VALIDATION
        if cleaned.startswith("254") and len(cleaned) == 12:
            numbers.append(cleaned)
            print(cleaned)

    frappe.msgprint(f"Final Numbers: {numbers}")  # DEBUG

    if not numbers:
        frappe.throw("No valid numbers after cleaning.")

    send_sms(numbers, doc.message or "")