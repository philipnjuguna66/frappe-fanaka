import frappe
import africastalking
import traceback
import re
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
    "Success":          "COMPLETED",  # map AT 'Success' to our COMPLETED
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


# Helper: Clean phone to strict E.164
def clean_phone(phone):
    if not phone:
        return ""
    phone = re.sub(r'[^0-9+]', '', str(phone).strip())
    if phone.startswith('0'):
        phone = '+254' + phone[1:]
    elif not phone.startswith('+'):
        phone = '+' + phone
    return phone


# ---------------------------------------------------------
# INITIATE OUTBOUND CALL + create Call Log
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):
    try:
        phone_number = clean_phone(phone_number)
        if not phone_number:
            return {"status": "error", "message": "Invalid phone number"}

        settings = frappe.get_single("Africa Talking Settings")
        username = settings.username
        api_key = settings.get_password("api_key")
        outbound_number = clean_phone(settings.outbound_number)

        if not all([username, api_key, outbound_number]):
            return {"status": "error", "message": "Missing Africa's Talking credentials"}

        africastalking.initialize(username, api_key)
        voice = africastalking.Voice

        response = voice.call(
            callFrom=outbound_number,
            callTo=[phone_number]
        )

        session_id = response.get("entries", [{}])[0].get("sessionId")

        # Create outbound Call Log
        if session_id:
            cl = frappe.new_doc("Call Log")
            cl.custom_session_id = session_id
            cl.from_ = outbound_number
            cl.to = phone_number
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
# VOICE CALLBACK – early logging + flow
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_callback():
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Callback - Incoming Data")

        session_id = data.get("sessionId", "").strip()
        is_active = int(data.get("isActive", 0))
        direction = data.get("direction", "").strip()
        caller = clean_phone(data.get("callerNumber", ""))
        destination = clean_phone(data.get("destinationNumber", ""))
        recording_url = data.get("recordingUrl", "")

        agent_number = "+254714686511"

        # Early logging for inbound
        if direction == "Inbound" and session_id:
            existing_name = frappe.db.get_value("Call Log", {"custom_session_id": session_id}, "name")
            if not existing_name:
                cl = frappe.new_doc("Call Log")
                cl.custom_session_id = session_id
                cl.from_ = caller
                cl.to = destination  # your virtual number
                cl.recording_url = recording_url  # usually empty here, but safe
                cl.status = "Ringing"
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

        # Call flow (simplified - no greeting for inbound as per your last change)
        if direction == "Inbound":
            body = f"""
                <Dial phoneNumbers="{agent_number}" record="true" maxDuration="600" sequential="true"/>
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
            <Say voice="en-US-Wavenet-C">Sorry, technical issue.</Say>
            <Hangup/>
        """)


# ---------------------------------------------------------
# VOICE EVENT CALLBACK – update Call Log (including recording_url)
# ---------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    try:
        data = frappe.form_dict or {}
        frappe.log_error(frappe.as_json(data), "AT Voice Event - Raw Payload")

        session_id = data.get("sessionId", "").strip()
        if not session_id:
            return xml_response("<Say>Invalid session</Say>")

        at_status = data.get("status", "").strip()
        session_state = data.get("callSessionState", "").strip()
        effective = session_state or at_status or "MISSING"
        status = STATUS_MAP.get(effective, "UNKNOWN")

        duration = int(data.get("durationInSeconds", 0))
        direction = data.get("direction", "Inbound")
        recording_url = data.get("recordingUrl", "")

        # Find and update (or create fallback)
        log_name = frappe.db.get_value("Call Log", {"custom_session_id": session_id}, "name")

        if log_name:
            doc = frappe.get_doc("Call Log", log_name)
        else:
            # Fallback: create if missing (rare, but safe)
            doc = frappe.new_doc("Call Log")
            doc.custom_session_id = session_id
            doc.from_ = clean_phone(data.get("callerNumber", ""))
            doc.to = clean_phone(data.get("destinationNumber", ""))
            doc.medium = "Africa's Talking"
            doc.start_time = data.get("callStartTime", frappe.utils.now_datetime())

        # Update fields
        doc.status = status
        doc.call_duration = duration
        if recording_url:
            doc.recording_url = recording_url  # this should now save!

        if duration == 0:
            doc.note = (doc.note or "") + "\nZero duration - possible early hangup or network issue"

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return xml_response("<Say>Event received and logged</Say>")

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "AT Event Callback - Crash")
        return xml_response("<Say>System error</Say>")