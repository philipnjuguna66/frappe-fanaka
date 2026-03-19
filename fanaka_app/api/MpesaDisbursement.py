import json
import requests
import base64
import os
import re
from frappe.utils import now_datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms

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

    def sanitize(self, text):
        if not text:
            return ""
        return str(text).translate(str.maketrans({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'
        }))[:100]

    def b2c_payment(self, requisition):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        released_by = frappe.session.user or "System"
        
        payload = {
            "InitiatorName": self.initiator_name,
            "SecurityCredential": self.generate_security_credential(),
            "CommandID": "BusinessPayment",
            "Amount": int(requisition.total_amount),
            "PartyA": self.shortcode,
            "PartyB": self.format_phone(requisition.pay_to),
            "Remarks":  "Payment",
            "QueueTimeOutURL": f"{self.settings.callback_url_timeout}?requisition_id={requisition.name}&released_by={released_by}",
            "ResultURL": f"{self.settings.callback_url_result}?requisition_id={requisition.name}&released_by={released_by}",
            "Occasion": self.sanitize(requisition.name)
        }

        response = requests.post(f"{self.base_url}/mpesa/b2c/v3/paymentrequest", json=payload, headers=headers)
        return response.json()

    def b2b_payment(self, requisition, command_id):
        
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        released_by = frappe.session.user or "System"
        
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
            "PartyB": self.sanitize(requisition.pay_to),
            "AccountReference": self.sanitize(requisition.name),
            "Remarks":  "Payment",
            "QueueTimeOutURL": f"{self.settings.callback_url_timeout}?requisition_id={requisition.name}&released_by={released_by}",
            "ResultURL": f"{self.settings.callback_url_result}?requisition_id={requisition.name}&released_by={released_by}",
        }

     
        for version in ["/mpesa/b2b/v1/paymentrequest"]:
            url = f"{self.base_url}{version}"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            # === EXACT ERROR YOU GOT ===
            try:
                err = response.json()
                if err.get("errorCode") == "401.002.01" or "apiproduct" in str(err).lower():
                    frappe.throw(_(
                        "B2B API not enabled for this Consumer Key.<br><br>"
                        "Fix: Daraja Portal → My Apps → Add Product → Subscribe to <b>B2B</b> (BusinessBuyGoods / BusinessPayBill)<br>"
                        "Then generate new keys and update Mpesa B2B Settings."
                    ))
            except:
                frappe.throw(_(
                        "an error occured"
                    ))

            # Log full error
            error_body = response.text
            try:
                error_body = json.dumps(response.json(), indent=2)
            except:
                pass
            frappe.log_error(f"B2B {version} failed\nStatus: {response.status_code}\nBody:\n{error_body}", "M-Pesa B2B Exact Error")

        raise frappe.ValidationError("M-Pesa B2B request failed. Check Error Log for details.")


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


def parse_mpesa_amount(amount_str):
    """Helper to extract BasicAmount from Safaricom's complex string format"""
    if not amount_str: return 0.0
    match = re.search(r"BasicAmount=([\d.]+)", str(amount_str))
    if match:
        return float(match.group(1))
    return 0.0





@frappe.whitelist(allow_guest=True)
def payment_result():

    timestamp = now_datetime()

    try:

        # Query parameters
        requisition_name = frappe.request.args.get("requisition_id")
        released_by = frappe.request.args.get("released_by") or "System"

        # Callback JSON
        data = json.loads(frappe.request.data) if frappe.request.data else {}
        result = data.get("Result", {})

        result_code = str(result.get("ResultCode"))
        result_desc = result.get("ResultDesc")
        transaction_id = result.get("TransactionID")

        frappe.log_error(
            f"Requisition: {requisition_name}\nResultCode: {result_code}\nDesc: {result_desc}",
            "MPESA RESULT CALLBACK"
        )

        if not requisition_name:
            return {"ResponseCode": "0", "ResponseDesc": "Received"}

        if not frappe.db.exists("Requisitions", requisition_name):
            frappe.log_error(
                f"Requisition {requisition_name} not found",
                "MPESA CALLBACK ERROR"
            )
            return {"ResponseCode": "0", "ResponseDesc": "Received"}

        req = frappe.get_doc("Requisitions", requisition_name)

        # SUCCESS
        if result_code == "0":

            req.db_set("status", "Paid")
            req.db_set("released_at", timestamp)
            req.db_set("released_by", released_by)
            req.db_set("reference", transaction_id)
            req.db_set("reference_date", timestamp)
            req.db_set("posting_date", timestamp)

            req.add_comment(
                "Info",
                f"[{timestamp}] M-Pesa SUCCESS. TransID: {transaction_id}. {result_desc}"
            )

            frappe.publish_realtime(
                "payment_success",
                {
                    "requisitionId": requisition_name,
                    "transaction_id": transaction_id,
                    "message": result_desc,
                },
            )

        # FAILURE
        else:

            req.db_set("status", "Failed")

            req.add_comment(
                "Comment",
                f"[{timestamp}] M-Pesa FAILED (Code {result_code}). {result_desc}"
            )

            frappe.publish_realtime(
                "payment_error",
                {
                    "requisitionId": requisition_name,
                    "message": result_desc,
                },
            )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MPESA CALLBACK ERROR")

    return {"ResponseCode": "0", "ResponseDesc": "Received"}

@frappe.whitelist(allow_guest=True)
def payment_timeout():
    try:
        data = json.loads(frappe.request.data)
        requisition_name = frappe.form_dict.get('requisition_id')
        title = f"M-Pesa Payment Timeout"
        if requisition_name:
            title += f" - {requisition_name}"
        frappe.log_error(message=json.dumps(data), title=title)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Timeout Callback Error")
    
    return {"ResponseCode": "0", "ResponseDesc": "Success"}


@frappe.whitelist()
def send_otp_notification():
    settings = frappe.get_single("Mpesa B2B Settings")
    target_number = settings.notification_phone
    if not target_number:
        frappe.throw(_("Notification Phone Number is missing in Mpesa B2B Settings"))
        
    otp = frappe.generate_hash(length=6).upper()
    frappe.cache().set_value(f"mpesa_auth_otp_{frappe.session.user}", otp, expires_in_sec=600)
    
    send_sms(
            receiver_list=[target_number],
            msg=f"Your M-Pesa B2B API OTP is: {otp}. It expires in 5 minutes.",
            sender_name="Fanaka_Ltd",
            success_msg="SMS sent successfully"
        )
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

@frappe.whitelist()
def get_mpesa_balance():
    """Fetch real M-Pesa balance (Working + Utility Account)"""
    try:
        service = MpesaDisbursement()
        access_token = service.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "Initiator": service.initiator_name,
            "SecurityCredential": service.generate_security_credential(),
            "CommandID": "AccountBalance",
            "PartyA": service.shortcode,
            "IdentifierType": "4",
            "Remarks": "Balance",
            "QueueTimeOutURL": service.settings.callback_url_timeout,
            "ResultURL": f"{frappe.utils.get_url()}/api/method/fanaka_app.api.MpesaDisbursement.balance_callback"
        }

        response = requests.post(f"{service.base_url}/mpesa/accountbalance/v1/query", json=payload, headers=headers)
        return response.json()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Balance Error")
        return {"error": str(e)}

@frappe.whitelist(allow_guest=True)
def balance_callback():
    try:
        data = json.loads(frappe.request.data)
        result = data.get('Result', {})
        result_code = result.get('ResultCode')
        
        if result_code == 0:
            # Extract parameters from the ResultParameters list
            params = result.get('ResultParameters', {}).get('ResultParameter', [])
            balance_string = ""
            
            for p in params:
                if p.get('Key') == 'AccountBalance':
                    balance_string = p.get('Value')
                    break
            
            if balance_string:
                # Format: Account1|KES|Balance|Available|...&Account2|...
                accounts_data = balance_string.split('&')
                
                working_balance = 0.0
                utility_balance = 0.0
                
                for account_entry in accounts_data:
                    parts = account_entry.split('|')
                    # Expected indices based on Safaricom spec: 
                    # 0: Account Name, 2: Current Balance (or Available)
                    if len(parts) >= 3:
                        acc_name = parts[0].strip()
                        # Remove commas and convert to float
                        try:
                            balance_val = float(parts[2].replace(',', ''))
                        except ValueError:
                            balance_val = 0.0
                            
                        if "Working Account" in acc_name:
                            working_balance = balance_val
                        elif "Utility Account" in acc_name:
                            utility_balance = balance_val

                # Save to Single Doc: Mpesa B2B Settings
                settings = frappe.get_doc("Mpesa B2B Settings")
                settings.db_set('utility_working_balance', working_balance)
                settings.db_set('working_account_balance', utility_balance)
                #settings.db_set('last_balance_update', frappe.utils.now_datetime())
                
                # Optional: Notify the UI if someone is waiting
                frappe.publish_realtime("mpesa_balance_updated", {
                    "working": working_balance,
                    "utility": utility_balance
                })

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "M-Pesa Balance Callback Error")
    
    return {"ResponseCode": "0", "ResponseDesc": "Success"}  

@frappe.whitelist()
def get_stored_mpesa_balance():
    """Returns the balances currently stored in the database"""
    settings = frappe.get_doc("Mpesa B2B Settings")
    return {
        "working_balance": frappe.format(settings.working_account_balance, "Currency"),
        "utility_balance": frappe.format(settings.utility_working_balance, "Currency"),
        "shortcode": settings.shortcode
    }      