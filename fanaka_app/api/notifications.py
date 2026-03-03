import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms

import frappe
import re
from frappe.core.doctype.sms_settings.sms_settings import send_sms

def normalize_number(number):
    number = re.sub(r"\D", "", number)  # remove non-digits

    # Convert Kenyan format
    if number.startswith("0"):
        number = "254" + number[1:]
    elif number.startswith("7") and len(number) == 9:
        number = "254" + number

    return number

def handle_sms_cc(doc, method=None):

    if doc.channel != "SMS":
        return

    if not doc.custom_additional_sms_numbers:
        return

    raw_numbers = doc.custom_additional_sms_numbers.split(",")

    numbers = []
    for n in raw_numbers:
        cleaned = normalize_number(n.strip())
        if cleaned:
            numbers.append(cleaned)

    if not numbers:
        return

    send_sms(numbers, doc.message or "")