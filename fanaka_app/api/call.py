import frappe
import africastalking
from frappe import _


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


# ---------------------------------------------------------
# VOICE ACTION CALLBACK
# Africa's Talking calls this URL during call routing
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():

    try:

        data = frappe.form_dict

        frappe.logger().info({
            "AT Voice Callback": data
        })

        is_active = int(data.get("isActive", 0))
        direction = data.get("direction")

        if is_active == 1:

            # -------------------------------------------------
            # INBOUND CALL
            # -------------------------------------------------
            if direction == "Inbound":

                body = """
<Response>
<Say voice="en-US-Standard-C" playBeep="false">
Welcome to Fanaka Real Estate Ltd: Your Ideal Real Estate Partner
</Say>
<Dial phoneNumbers="+254714686511"
record="true"
maxDuration="10"
sequential="true"/>
</Response>
"""

                xml_response(body)
                return

            # -------------------------------------------------
            # OUTBOUND CALL
            # -------------------------------------------------
            elif direction == "Outbound":

                user_phone = "+254714686511"

                body = f"""
<Response>
<Dial phoneNumbers="{user_phone}"
record="true"
maxDuration="10"
sequential="true"/>
</Response>
"""

                xml_response(body)
                return

            # -------------------------------------------------
            # OTHER CASE
            # -------------------------------------------------
            else:

                body = """
<Response>
<Say voice="en-US-Standard-C" playBeep="false">
Welcome to Fanaka Real Estate Ltd
</Say>
</Response>
"""

                xml_response(body)
                return

        # -------------------------------------------------
        # CALL NOT ACTIVE
        # -------------------------------------------------
        body = """
<Response>
<Say>Hello, thank you for calling. This call is now connected.</Say>
</Response>
"""

        xml_response(body)

    except Exception:

        frappe.log_error(frappe.get_traceback(), "Voice Callback Error")

        xml_response("""
<Response>
<Say>System error occurred</Say>
</Response>
""")


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