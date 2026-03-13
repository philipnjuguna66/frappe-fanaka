import frappe
import africastalking
import traceback
from frappe import _

# ---------------------------------------------------------
# UTILITY: Send valid XML response
# ---------------------------------------------------------
def xml_response(body: str):
    """Set Frappe response to valid XML with proper headers."""
    frappe.local.response["type"] = "xml"
    frappe.local.response["response"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n{body.strip()}\n</Response>'
    )


# ---------------------------------------------------------
# INITIATE OUTBOUND CALL
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    """
    Initiates an outbound call via Africa's Talking Voice API.
    Returns session ID on success.
    """
    try:
        # Normalize phone number to E.164 format (Kenya)
        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        # Load settings
        settings = frappe.get_single("Africa Talking Settings")
        username = settings.username
        api_key = settings.get_password("api_key")
        outbound_number = settings.outbound_number

        if not all([username, api_key, outbound_number]):
            return {"status": "error", "message": "Missing Africa Talking credentials"}

        africastalking.initialize(username, api_key)
        voice = africastalking.Voice

        # Make the call
        response = voice.call(
            callFrom=outbound_number,
            callTo=[phone_number]
        )

        session_id = None
        if response and response.get("entries"):
            session_id = response["entries"][0].get("sessionId")

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Call initiated"
        }

    except Exception as e:
        frappe.log_error(
            f"AT Make Call Failed\n{traceback.format_exc()}\nPhone: {phone_number}",
            "Africa's Talking - Outbound Call Error"
        )
        return {
            "status": "error",
            "message": f"Call initiation failed: {str(e)}"
        }


# ---------------------------------------------------------
# VOICE CALLBACK (controls call flow)
# Africa's Talking hits this endpoint to get call instructions
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Handles call routing logic for both inbound and outbound calls."""
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Callback - Incoming Data")

        is_active = int(data.get("isActive", 0))
        direction = data.get("direction", "").strip()

        if is_active != 1:
            # Call has ended or not active → minimal response
            xml_response("""
                <Say voice="en-US-Wavenet-C">Thank you for calling. Goodbye.</Say>
                <Hangup/>
            """)
            return

        # Common agent number (you can make this dynamic later via DB/settings)
        agent_number = "+254714686511"

        if direction == "Inbound":
            # Greeting for people calling your line
            body = f"""
                <Say voice="en-US-Wavenet-C" playBeep="false">
                    Welcome to Fanaka Real Estate Ltd – your ideal real estate partner.
                    Please hold while we connect you to an agent.
                </Say>
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """

        elif direction == "Outbound":
            # Outbound call – straight to agent (no greeting needed usually)
            body = f"""
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """

        else:
            # Unknown direction fallback
            body = """
                <Say voice="en-US-Wavenet-C">Connecting you now.</Say>
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600"/>
            """

        xml_response(body)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Callback - Crash")
        xml_response("""
            <Say voice="en-US-Wavenet-C">Sorry, we are experiencing technical difficulties.</Say>
            <Hangup/>
        """)


# ---------------------------------------------------------
# VOICE EVENTS / STATUS CALLBACK
# Africa's Talking sends call status updates here (completed, failed, etc.)
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Receives call status events from Africa's Talking."""
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Event - Incoming Data")

        # You can now:
        # - Create/Update a Call Log doctype
        # - Send WhatsApp/email notification on missed call
        # - Track call duration, cost, status, etc.

        # Minimal ACK response required by Africa's Talking
        xml_response("""
            <Say voice="en-US-Wavenet-C">Call status received. Thank you.</Say>
        """)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Event Callback - Crash")
        xml_response("""
            <Say>Sorry, system error.</Say>
        """)