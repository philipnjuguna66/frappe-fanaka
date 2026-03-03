import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms

def handle_sms_cc(doc, method=None):

    if doc.channel != "SMS":
        return

    if not doc.custom_additional_sms_numbers:
        return

    numbers = [
        n.strip()
        for n in doc.custom_additional_sms_numbers.split(",")
        if n.strip()
    ]

    if not numbers:
        return

    send_sms(numbers, doc.message or "")