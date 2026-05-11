# [2026-03-18 11:25:44]
import json
import requests
import base64
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms

class MpesaDisbursement:
    def __init__(self):
        # Updated to use 'Mpesa B2B Settings' as requested
        self.settings = frappe.get_single("Mpesa B2B Settings")
        self.env = self.settings.environment # 'live' or 'sandbox'
        self.base_url = "https://api.safaricom.co.ke" if self.env == 'live' else "https://sandbox.safaricom.co.ke"
        
        self.consumer_key = self.settings.consumer_key
        self.consumer_secret = self.settings.get_password("consumer_secret")
        self.shortcode = self.settings.shortcode
        self.initiator_name = self.settings.initiator_name
        self.initiator_password = self.settings.get_password("initiator_password")
        
    def get_access_token(self):
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=(self.consumer_key, self.consumer_secret))
        response.raise_for_status()
        return response.json().get('access_token')

    def generate_security_credential(self):
        cert_content = self.settings.public_certificate
        if not cert_content:
            frappe.throw(_("M-Pesa Public Certificate is missing in Mpesa B2B Settings"))

        cert = x509.load_pem_x509_certificate(cert_content.encode())
        public_key = cert.public_key()

        encrypted = public_key.encrypt(
            self.initiator_password.encode(),
            padding.PKCS1v15()
        )
        return base64.b64encode(encrypted).decode('utf-8')

    def format_phone(self, phone):
        phone = str(phone).strip().replace("+", "")
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif phone.startswith("7") or phone.startswith("1"):
            phone = "254" + phone
        return phone

    def b2c_payment(self, requisition):
        access_token = self.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        payload = {
            "InitiatorName": self.initiator_name,
            "SecurityCredential": self.generate_security_credential(),
            "CommandID": "BusinessPayment",
            "Amount": int(requisition.amount),
            "PartyA": self.shortcode,
            "PartyB": self.format_phone(requisition.pay_to),
            "Remarks": requisition.description[:20] if requisition.description else "Payment",
            "QueueTimeOutURL": self.settings.callback_url + "/timeout",
            "ResultURL": self.settings.callback_url + "/result",
            "Occasion": requisition.name
        }

        response = requests.post(f"{self.base_url}/mpesa/b2c/v3/paymentrequest", json=payload, headers=headers)
        return response.json()

    def b2b_payment(self, requisition, command_id):
        access_token = self.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        cmd_name = "BusinessBuyGoods" if command_id == "2" else "BusinessPayBill"
        receiver_type = "2" if command_id == "2" else "4"

        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": self.generate_security_credential(),
            "CommandID": cmd_name,
            "SenderIdentifierType": "4",
            "RecieverIdentifierType": receiver_type,
            "Amount": int(requisition.amount),
            "PartyA": self.shortcode,
            "PartyB": requisition.pay_to,
            "AccountReference": requisition.account_reference or requisition.name,
            "Remarks": requisition.description[:20] if requisition.description else "Payment",
            "QueueTimeOutURL": self.settings.callback_url + "/timeout",
            "ResultURL": self.settings.callback_url + "/result"
        }

        response = requests.post(f"{self.base_url}/mpesa/b2b/v1/paymentrequest", json=payload, headers=headers)
        return response.json()

@frappe.whitelist()
def process_disbursement(requisition_id):
    doc = frappe.get_doc("Requisitions", requisition_id)
    if doc.status == "Paid":
        frappe.throw(_("Requisition {0} is already paid").format(requisition_id))
    
    service = MpesaDisbursement()
    method = doc.payment_method
    
    try:
        if method == "phone":
            res = service.b2c_payment(doc)
        elif method == "till":
            res = service.b2b_payment(doc, "2")
        elif method == "paybill":
            res = service.b2b_payment(doc, "4")
        else:
            frappe.throw(_("Method {0} not supported").format(method))
            
        doc.add_comment("Info", f"M-Pesa Disbursement initiated. Response: {res.get('ResponseDescription')}")
        return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Disbursement Error")
        frappe.throw(_("Disbursement failed: {0}").format(str(e)))

@frappe.whitelist()
def send_otp_notification(step="payment release"):
    settings = frappe.get_single("Mpesa B2B Settings")
    target_number = settings.notification_phone
    otp = frappe.generate_hash(length=6).upper()
    
    frappe.cache().set_value(f"requisition_otp_{step}", otp, expires_in_sec=600)
    
    # Example SMS integration
    send_sms(
            receiver_list=[target_number],
            msg=f"OTP: {otp} for {step}",
            sender_name="Fanaka_Ltd",
            success_msg="OTP sent successfully"
        )
    return True
@frappe.whitelist()
def verify_authorisation_otp(otp,step="payment release"):
    expected_otp = frappe.cache().get_value(f"requisition_otp_{step}")
    if otp == expected_otp:
        frappe.cache().delete_value(f"requisition_otp_{step}")
        return True
    return False

@frappe.whitelist()
def payment_result():
    data = json.loads(frappe.request.data)
    frappe.publish_realtime("mpesa_payment_result", data, user=frappe.session.user)
    # Log the incoming data for debugging
    frappe.log_error(message=json.dumps(data), title="M-Pesa Payment Result")
    
    # Process the result based on your application's logic
    # For example, you might want to update the Requisition status based on the result
    
    return "Result received"

@frappe.whitelist()
def payment_timeout():
    data = json.loads(frappe.request.data)
    frappe.publish_realtime("mpesa_payment_timeout", data, user=frappe.session.user)
    # Log the incoming data for debugging
    frappe.log_error(message=json.dumps(data), title="M-Pesa Payment Timeout")

    