import frappe
import africastalking
import traceback
from frappe import _
from werkzeug.wrappers import Response as WerkzeugResponse

# ---------------------------------------------------------
# STATUS MAP (used in event callback)
# ---------------------------------------------------------
STATUS_MAP = {
    "Completed":        "COMPLETED",
    "Aborted":          "ABORTED",
    "Busy":             "BUSY",
    "No Answer":        "NO_ANSWER",
    "Failed":           "FAILED",
    "Rejected":         "REJECTED",
    "Ringing":          "RINGING",
    "Ongoing":          "IN_PROGRESS",
    "Machine":          "ANSWERING_MACHINE",
    "UNKNOWN":          "UNKNOWN"
}


# ---------------------------------------------------------
# UTILITY: Return pure raw XML (critical for Africa's Talking)
# ---------------------------------------------------------
def xml_response(body: str):
    """Return pure raw XML – bypasses Frappe JSON wrapper completely."""
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n{body.strip()}\n</Response>'
    ).encode('utf-8')

    response = WerkzeugResponse(
        xml_content,
        status=200,
        mimetype='text/xml; charset=utf-8'
    )
    response.headers['Content-Length'] = str(len(xml_content))

    return response


# ---------------------------------------------------------
# INITIATE OUTBOUND CALL
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    """
    Initiates an outbound call via Africa's Talking Voice API.
    Returns session ID on success (JSON response – this one is not XML).
    """
    try:
        # Normalize phone number to E.164 format (Kenya-focused)
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
# VOICE CALLBACK (controls call flow – returns XML)
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

        agent_number = "+254714686511"

        if is_active != 1:
            return xml_response("""
                <Say voice="en-US-Wavenet-C">Thank you for calling. Goodbye.</Say>
                <Hangup/>
            """)

        if direction == "Inbound":
            body = f"""
                <Say voice="en-US-Wavenet-C" playBeep="false">
                    Welcome to Fanaka Real Estate Ltd – your ideal real estate partner.
                    Please hold while we connect you to an agent.
                </Say>
                
            """
        elif direction == "Outbound":
            body = f"""
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """
        else:
            body = f"""
                <Say voice="en-US-Wavenet-C">Connecting you now.</Say>
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """

        return xml_response(body)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Callback - Crash")
        return xml_response("""
            <Say voice="en-US-Wavenet-C">Sorry, we are experiencing technical difficulties.</Say>
            <Hangup/>
        """)


# ---------------------------------------------------------
# VOICE EVENTS / STATUS CALLBACK (returns minimal XML)
# Africa's Talking sends call status updates here
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Receives call status events from Africa's Talking. No DB writes yet."""
    try:
        data = frappe.form_dict or {}

        # Log full raw payload (useful for debugging)
        frappe.log_error(frappe.as_json(data), "AT Voice Event - Raw Payload")

        # Extract key fields
        at_status = data.get("status", "").strip()
        session_state = data.get("callSessionState", "").strip()

        # Prefer callSessionState for final status
        effective_status = session_state if session_state else at_status
        effective_status = effective_status or "MISSING"

        internal_status = STATUS_MAP.get(effective_status, "UNKNOWN")

        duration = data.get("durationInSeconds", "0")

        summary = (
            f"Call Event | "
            f"session: {data.get('sessionId', '—')} | "
            f"direction: {data.get('direction', '—')} | "
            f"raw: {at_status} / {session_state} → {internal_status} | "
            f"duration: {duration}s | "
            f"from: {data.get('callerNumber', '—')} → {data.get('destinationNumber', '—')}"
        )

        frappe.log_error(summary, "AT Voice Event - Summary")

        # Highlight zero-second calls
        if duration == "0" and internal_status in ("COMPLETED", "ABORTED"):
            frappe.log_error(
                f"Zero-second call: {summary}\nLikely: caller hung up instantly or early network drop\nRaw: {frappe.as_json(data)}",
                "AT Voice - Zero-Second Call"
            )

        # Minimal response – Africa's Talking accepts almost anything here
        return xml_response("""
            <Say voice="en-US-Wavenet-C">Event received.</Say>
        """)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Event Callback - Exception")
        return xml_response("""
            <Say voice="en-US-Wavenet-C">System received event.</Say>
        """)