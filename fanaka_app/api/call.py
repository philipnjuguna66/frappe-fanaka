import frappe
import africastalking
import traceback
from frappe import _

# ---------------------------------------------------------
# UTILITY: Send XML response safely
# ---------------------------------------------------------
def xml_response(body: str):
    """Set frappe local response to valid XML."""
    frappe.local.response["type"] = "xml"
    frappe.local.response["response"] = f'<?xml version="1.0" encoding="UTF-8"?>{body}'


# ---------------------------------------------------------
# INITIATE OUTBOUND CALL
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    """Initiates an outbound call via Africa's Talking."""
    try:
        # Normalize Kenyan numbers
        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        settings = frappe.get_single("Africa Talking Settings")
        username = settings.username
        api_key = settings.get_password("api_key")
        outbound_number = settings.outbound_number

        africastalking.initialize(username, api_key)
        voice = africastalking.Voice

        response = voice.call(
            callFrom=outbound_number,
            callTo=[phone_number]
        )

        session_id = None
        if response.get("entries"):
            session_id = response["entries"][0].get("sessionId")

        return {
            "status": "success",
            "session_id": session_id
        }

    except Exception:
        frappe.log_error(traceback.format_exc(), _("AT Make Call Failed"))
        return {
            "status": "error",
            "message": "Call initiation failed"
        }


# ---------------------------------------------------------
# VOICE CALLBACK
# Africa's Talking calls this URL to control the call
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Inbound/outbound call routing callback."""
    try:
        data = frappe.form_dict or {}

        # Log incoming data safely
        frappe.log_error(frappe.as_json(data), "AT Voice Callback Incoming Data")

        is_active = int(data.get("isActive", 0))
        direction = data.get("direction")

        if is_active == 1:
            if direction == "Inbound":
                body = """
<Response>
<Say voice="en-US-Standard-C" playBeep="false">
Welcome to Fanaka Real Estate Ltd: Your Ideal Real Estate Partner
</Say>
<Dial phoneNumbers="+254714686511" record="true" maxDuration="600" sequential="true"/>
</Response>
"""
                xml_response(body)
                return

            elif direction == "Outbound":
                body = """
<Response>
<Dial phoneNumbers="+254714686511" record="true" maxDuration="600" sequential="true"/>
</Response>
"""
                xml_response(body)
                return

        # Default fallback
        body = """
<Response>
<Say>Hello, thank you for calling. This call is now connected.</Say>
</Response>
"""
        xml_response(body)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Callback Crash")
        xml_response("""
<Response>
<Say>System error occurred</Say>
</Response>
""")


# ---------------------------------------------------------
# VOICE EVENT CALLBACK
# Africa's Talking sends call status updates here
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Receive call status updates from Africa's Talking."""
    try:
        data = frappe.form_dict or {}

        # Log safely
        frappe.log_error(frappe.as_json(data), "AT Voice Event Incoming Data")

        # Here you could update CallLog or another DocType if desired
        # For example:
        # frappe.get_doc({
        #     "doctype": "Call Log",
        #     "sessionId": data.get("sessionId"),
        #     ...
        # }).insert(ignore_permissions=True)

        # Respond with simple XML to AT
        xml_response("""
<Response>
<Say>Hello, thank you for calling. This call is now connected.</Say>
</Response>
""")

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Event Callback Crash")
        xml_response("""
<Response>
<Say>System error occurred</Say>
</Response>
""")