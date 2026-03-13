import frappe
import africastalking
from frappe import _


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
        frappe.log_error(frappe.get_traceback(), _("AT Make Call Failed"))

        return {
            "status": "error",
            "message": "Call initiation failed"
        }


# ---------------------------------------------------------
# VOICE ACTION CALLBACK
# Africa's Talking hits this URL during call routing
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():
    """
    Main routing callback for Africa's Talking Voice.
    """

    try:

        data = frappe.request.values

        # Log callback payload
        frappe.logger().info({
            "AT Voice Callback": data
        })

        is_active = data.get("isActive")
        direction = data.get("direction")

        xml = ""

        if str(is_active) == "1":

            # -------------------------------------------------
            # INBOUND CALL
            # -------------------------------------------------
            if direction == "Inbound":

                xml = """
<Response>
    <Say>Welcome to Fanaka Real Estate. Please hold while we connect your call.</Say>
    <Dial record="true" sequential="true" maxDuration="600">
        <Number>+254714686511</Number>
    </Dial>
</Response>
"""

            # -------------------------------------------------
            # OUTBOUND CALL
            # -------------------------------------------------
            elif direction == "Outbound":

                xml = """
<Response>
    <Dial record="true" sequential="true" maxDuration="600">
        <Number>+254714686511</Number>
    </Dial>
</Response>
"""

            else:

                xml = """
<Response>
    <Say>Welcome to Fanaka Real Estate.</Say>
</Response>
"""

        else:

            xml = """
<Response>
    <Say>Thank you for calling Fanaka Real Estate.</Say>
</Response>
"""

        frappe.respond_as_xml(xml)

    except Exception:

        frappe.log_error(frappe.get_traceback(), "Voice Callback Error")

        frappe.respond_as_xml(
            '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        )


# ---------------------------------------------------------
# EVENT CALLBACK
# Africa's Talking sends call lifecycle events here
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():

    try:

        data = frappe.request.values

        # Log call status updates
        frappe.logger().info({
            "AT Voice Event": data
        })

        return "OK"

    except Exception:

        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")

        return "ERROR"