import json
import requests
import base64
import os
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import frappe
from frappe import _

class MpesaDisbursement:
    def __init__(self):
        self.settings = frappe.get_single("Mpesa B2B Settings")
        self.env = self.settings.environment
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
            "Amount": int(requisition.total_amount),
            "PartyA": self.shortcode,
            "PartyB": self.format_phone(requisition.pay_to),
            "Remarks": requisition.description[:20] if requisition.description else "Payment",
            "QueueTimeOutURL": f"{self.settings.callback_url_timeout}?requisition_id={requisition.name}",
            "ResultURL": f"{self.settings.callback_url_result}?requisition_id={requisition.name}",
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
            "Amount": int(requisition.total_amount),
            "PartyA": self.shortcode,
            "PartyB": requisition.pay_to,
            "AccountReference": requisition.name,
            "Remarks": requisition.description[:20] if requisition.description else "Payment",
            "QueueTimeOutURL": f"{self.settings.callback_url_timeout}?requisition_id={requisition.name}",
            "ResultURL": f"{self.settings.callback_url_result}?requisition_id={requisition.name}",
        }

        response = requests.post(f"{self.base_url}/mpesa/b2b/v1/paymentrequest", json=payload, headers=headers)
        return response.json()


@frappe.whitelist()
def process_disbursement(requisition_id):
    doc = frappe.get_doc("Requisitions", requisition_id)
    if doc.status == "Paid":
        frappe.throw(_("Requisition {0} is already paid").format(requisition_id))
    
    service = MpesaDisbursement()
    method = doc.payment_method.lower() if doc.payment_method else ""
    
    try:
        if "phone" in method or "mpesa" in method:
            res = service.b2c_payment(doc)
        elif "till" in method:
            res = service.b2b_payment(doc, "2")
        elif "paybill" in method:
            res = service.b2b_payment(doc, "4")
        else:
            frappe.throw(_("Method {0} not supported").format(method))
            
        doc.add_comment("Info", f"M-Pesa Disbursement initiated. ConversationID: {res.get('ConversationID')}")
        return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Disbursement Error")
        frappe.throw(_("Disbursement failed: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def payment_result():
    """Callback handler – works for BOTH B2C (phone) and B2B (Till/PayBill)"""
    try:
        data = json.loads(frappe.request.data)
        result = data.get('Result', {})
        result_code = result.get('ResultCode')
        result_desc = result.get('ResultDesc')
        
        # Robust requisition lookup (B2C uses Occasion, B2B uses AccountReference)
        requisition_name = None
        if result.get('Occasion'):
            requisition_name = result.get('Occasion')
        elif result.get('AccountReference'):
            requisition_name = result.get('AccountReference')
        else:
            # Official Daraja fallback
            ref_items = result.get('ReferenceData', {}).get('ReferenceItem', [])
            if isinstance(ref_items, dict):
                ref_items = [ref_items]
            for item in ref_items:
                if item.get('Key') in ['Occasion', 'AccountReference', 'BillReferenceNumber']:
                    requisition_name = item.get('Value')
                    break

        if result_code == 0:
            transaction_id = result.get('TransactionID')
            parameters = result.get('ResultParameters', {}).get('ResultParameter', [])
            
            payment_data = {'transaction_id': transaction_id, 'requisition_id': requisition_name}
            
            for item in parameters:
                key = item.get('Key')
                val = item.get('Value')
                if key in ['ReceiverPartyPublicName', 'ReceiverPublicName']:
                    payment_data['receiver_name'] = val
                elif key in ['TransactionAmount', 'Amount']:
                    payment_data['amount'] = val
                elif key in ['TransactionCompletedDateTime', 'TransCompletedTime']:
                    payment_data['transaction_date'] = val

            if requisition_name:
                req = frappe.get_doc("Requisitions", requisition_name)
                req.db_set('status', 'Paid')
                req.db_set('payment_reference', transaction_id)
                req.add_comment("Info", f"M-Pesa Success: {transaction_id}. Amount: {payment_data.get('amount')}")
                
                frappe.publish_realtime("payment_success", {
                    "requisitionId": requisition_name,
                    "message": result_desc,
                    "transaction_id": transaction_id
                })
        else:
            if requisition_name:
                frappe.publish_realtime("payment_error", {
                    "requisitionId": requisition_name,
                    "message": result_desc
                })
            frappe.log_error(message=json.dumps(data), title=f"M-Pesa Payment Failed: {result_code}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Callback Error")
    
    return {"ResponseCode": "0", "ResponseDesc": "Success"}


@frappe.whitelist(allow_guest=True)
def payment_timeout():
    data = json.loads(frappe.request.data)
    frappe.log_error(message=json.dumps(data), title="M-Pesa Payment Timeout")
    return {"ResponseCode": "0", "ResponseDesc": "Success"}


@frappe.whitelist()
def send_otp_notification():
    settings = frappe.get_single("Mpesa B2B Settings")
    target_number = settings.notification_phone
    if not target_number:
        frappe.throw(_("Notification Phone Number is missing in Mpesa B2B Settings"))
        
    otp = frappe.generate_hash(length=6).upper()
    frappe.cache().set_value(f"mpesa_auth_otp_{frappe.session.user}", otp, expires_in_sec=600)
    
    frappe.msgprint(_("OTP sent to {0} (Simulated: {1})").format(target_number, otp))
    return True


@frappe.whitelist()
def verify_authorisation_otp(otp):
    stored_otp = frappe.cache().get_value(f"mpesa_auth_otp_{frappe.session.user}")
    if not stored_otp:
        return False
    if str(otp).upper() == str(stored_otp).upper():
        frappe.cache().delete_value(f"mpesa_auth_otp_{frappe.session.user}")
        return True
    return False