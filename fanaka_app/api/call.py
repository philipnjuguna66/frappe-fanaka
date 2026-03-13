import frappe
import africastalking
from frappe import _
import traceback


# ---------------------------------------------------------
# Helper: Return XML Response
# ---------------------------------------------------------
def xml_response(body: str):
    xml = f'<?xml version="1.0" encoding="UTF-8"?>{body}'
    frappe.local.response["type"] = "xml"
    frappe.local.response["response"] = xml


# ---------------------------------------------------------
# INITIATE OUTBOUND CALL
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    """Initiates an outbound call via Africa's Talking"""

    try:

        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        settings = frappe.get_single("Africa Talking Settings")

        africastalking.initialize(
            settings.username,
            settings.get_password("api_key")
        )

        voice = africastalking.Voice

        response = voice.call(
            callFrom=settings.outbound_number,
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
        frappe.log_error(frappe.get_traceback(), _("AT Make Call Failed"))

        return {
            "status": "error",
            "message": "Call initiation failed"
        }


@frappe.whitelist(allow_guest=True)
def voice_callback():
    try:
        # Capture all incoming data
        data = frappe.form_dict or {}

        # Log everything safely
        frappe.log_error(frappe.as_json(data), "AT Voice Callback Incoming Data")

        # Return simple XML immediately
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Say>Test response working</Say>
</Response>"""

        frappe.local.response["type"] = "xml"
        frappe.local.response["response"] = xml

    except Exception:
        # Log full traceback
        frappe.log_error(traceback.format_exc(), "AT Voice Callback Crash")

        # Safe fallback XML
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Say>System error occurred</Say>
</Response>"""
        frappe.local.response["type"] = "xml"
        frappe.local.response["response"] = xml

        
# ---------------------------------------------------------
# VOICE EVENT CALLBACK
# Africa's Talking sends call lifecycle events here
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():

    try:

        data = frappe.form_dict

        frappe.logger().info({
            "AT Voice Event": data
        })

        body = """
<Response>
<Say>Hello, thank you for calling. This call is now connected.</Say>
</Response>
"""

        xml_response(body)

    except Exception:

        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")

        xml_response("""
<Response>
<Say>System error occurred</Say>
</Response>
""")