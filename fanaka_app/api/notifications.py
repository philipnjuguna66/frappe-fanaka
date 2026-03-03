import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms

def handle_sms_cc(doc, method=None):

    # If notification is not using SMS channel → exit
    if doc.channel != "SMS":
        return

    if not doc.custom_additional_sms_numbers:
        return

    numbers = [
        number.strip()
        for number in doc.custom_additional_sms_numbers.split(",")
        if number.strip()
    ]

    message = doc.message or ""

    # Send SMS to each additional number
    for number in numbers:
        send_sms([number], message)