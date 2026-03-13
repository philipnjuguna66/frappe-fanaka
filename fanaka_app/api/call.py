import frappe
import africastalking
import traceback
from frappe import _
from werkzeug.wrappers import Response as WerkzeugResponse

# ---------------------------------------------------------
# STATUS MAP
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
# UTILITY: Raw XML response
# ---------------------------------------------------------
def xml_response(body: str):
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
# INITIATE OUTBOUND CALL + create Call Log
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    try:
        # Normalize phone
        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        settings = frappe.get_single("Africa Talking Settings")
        username = settings.username
        api_key = settings.get_password("api_key")
        outbound_number = settings.outbound_number

        if not all([username, api_key, outbound_number]):
            return {"status": "error", "message": "Missing Africa's Talking credentials"}

        africastalking.initialize(username, api_key)
        voice = africastalking.Voice

        response = voice.call(
            callFrom=outbound_number,
            callTo=[phone_number]
        )

        session_id = None
        if response and response.get("entries"):
            session_id = response["entries"][0].get("sessionId")

        # ─── CREATE CALL LOG FOR OUTBOUND ──────────────────────────────
        if session_id:
            cl = frappe.new_doc("Call Log")
            cl.custom_session_id = session_id
            cl.id=session_id
            cl.from_ = outbound_number           # your number
            cl.to = phone_number                 # customer
            cl.status = "Initiated"
            cl.medium = "Africa's Talking"
            cl.start_time = frappe.utils.now_datetime()
            cl.note = "Outbound call initiated"
            if reference_doctype and reference_name:
                cl.reference_doctype = reference_doctype
                cl.reference_name = reference_name

            cl.insert(ignore_permissions=True)
            frappe.db.commit()

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Call initiated"
        }

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "AT Make Call Failed")
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# VOICE CALLBACK – inbound early logging + flow
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Callback - Data")

        session_id = data.get("sessionId", "").strip()
        is_active = int(data.get("isActive", 0))
        direction = data.get("direction", "").strip()
        caller = data.get("callerNumber", "")
        destination = data.get("destinationNumber", "")  # your virtual number
        recording_url = data.get("recordingUrl", "")  # recording URL if available
        agent_number = "+254714686511"
        

        # ─── EARLY LOGGING FOR INBOUND ──────────────────────────────
        if direction == "Inbound" and session_id:
            existing = frappe.db.exists("Call Log", {"custom_session_id": session_id})
            if not existing:
                cl = frappe.new_doc("Call Log")
                cl.custom_session_id = session_id
                cl.id = session_id
                cl.from_ = caller
                cl.to = destination      
                cl.recording_url=recording_url
                cl.status = STATUS_MAP.get(data.get("status", "").strip(), "Ringing")        # initial state
                cl.medium = "Africa's Talking"
                cl.start_time = frappe.utils.now_datetime()
                cl.note = "Inbound call received - waiting for connect"
                cl.insert(ignore_permissions=True)
                frappe.db.commit()

        if is_active != 1:
            return xml_response("""
                <Say voice="en-US-Wavenet-C">Thank you for calling. Goodbye.</Say>
                <Hangup/>
            """)

        # Call flow
        if direction == "Inbound":
            body = f"""
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """
        elif direction == "Outbound":
    
            body = f"""
                <Dial phoneNumbers="{caller}" record="true" maxDuration="600" sequential="true"/>
            """
        else:
            body = f"""
                <Say voice="en-US-Wavenet-C">Connecting you now.</Say>
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
            """

        return xml_response(body)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Callback Crash")
        return xml_response("""
            <Say voice="en-US-Wavenet-C">Sorry, technical issue.</Say>
            <Hangup/>
        """)


# ---------------------------------------------------------
# VOICE EVENT CALLBACK – update Call Log
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Event Callback - Data")

        session_id = data.get("sessionId", "").strip()
        status = data.get("status", "").strip()
        recording_url = data.get("recordingUrl", "").strip()

        if session_id:
            cl_name = frappe.db.get_value("Call Log", {"custom_session_id": session_id})
            if cl_name:
                cl = frappe.get_doc("Call Log", cl_name)
                cl.status = STATUS_MAP.get(status, status)
                if recording_url:
                    cl.recording_url = recording_url
                if status in ["Completed", "Aborted", "Failed", "Rejected"]:
                    cl.end_time = frappe.utils.now_datetime()
                cl.save(ignore_permissions=True)
                frappe.db.commit()

        return {"status": "success"}

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Event Callback Crash")
        return {"status": "error"}