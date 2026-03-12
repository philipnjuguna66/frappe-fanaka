import frappe
import africastalking

@frappe.whitelist(allow_guest=True)
def make_call(phone_number, reference_doctype=None, reference_name=None):

    try:

        # Normalize Kenyan numbers
        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]

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

        frappe.logger().info(response)

        session_id = None
        if response.get("entries"):
            session_id = response["entries"][0].get("sessionId")

        # Create Call Log
        call_log = frappe.get_doc({
            "doctype": "Call Log",
            "id": session_id,
            "call_type": "Outgoing",
            "from": outbound_number,
            "to": phone_number,
            "status": "Ringing",
            "custom_session_id": session_id,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name
        })

        call_log.insert(ignore_permissions=True, ignore_mandatory=True)

        return {
            "status": "success",
            "session_id": session_id
        }

    except Exception as e:

        frappe.log_error(frappe.get_traceback(), "Call Failed")

        return {
            "status": "error",
            "message": str(e)
        }

def log_call(data):

    session_id = data.get("sessionId")

    if not session_id:
        return

    existing = frappe.db.exists(
        "Call Log",
        {"id": session_id}
    )
    status_map = {
        "NotAnswered": "No Answer",
        "Completed": "Completed",
        "Busy": "Busy",
        "Failed": "Failed",
        "Ringing": "Ringing",
        "Queued": "Queued",
        "Cancelled": "Cancelled"
    }

    status = status_map.get(data.get("status"), "Failed")

    values = {
        "doctype": "Call Log",
        "id": session_id,
        "call_type": "Incoming" if data.get("direction") == "Inbound" else "Outgoing",
        "from": data.get("callerNumber"),
        "to": data.get("destinationNumber"),
        "duration": data.get("durationInSeconds"),
        "status": status,
        "custom_recording_url": data.get("recordingUrl"),
        "custom_caller_carrier": data.get("callerCarrierName"),
        "custom_currency_code": data.get("currencyCode"),
    }

    if existing:
        doc = frappe.get_doc("Call Log", existing)
        doc.update(values)
        doc.save(ignore_permissions=True)

    else:
        doc = frappe.get_doc(values)
        doc.insert(ignore_permissions=True)


# ---------------------------------------------------------
# Voice Callback (Main call routing)
# ---------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def voice_callback():

    try:

        data = frappe.local.request.form.to_dict()

        frappe.logger().info({
            "voice_callback": data
        })

        session_id = data.get("sessionId")
        direction = data.get("direction")
        is_active = data.get("isActive")

        log_call(data)

        if is_active == "1":

            if direction == "Inbound":

                xml = """
<Response>
<Say>
Welcome to Fanaka Real Estate Limited.
</Say>

<Dial phoneNumbers="+254714686511" record="true"/>
</Response>
"""

            else:

                xml = """
<Response>
<Say>Connecting your call</Say>
</Response>
"""

        else:

            xml = "<Response></Response>"

        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml

    except Exception:

        frappe.log_error(frappe.get_traceback(), "Voice Callback Error")

        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = "<Response></Response>"
# ---------------------------------------------------------
# Voice Event Callback (Call Updates)
# ---------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def voice_event_callback():

    request = frappe.local.request
    data = request.form.to_dict()

    frappe.logger().info({
        "voice_event_callback": data
    })

    log_call(data)

    xml_response = """
<Response>
    <Say>
        Thank you for calling Fanaka Real Estate.
    </Say>
</Response>
"""

    frappe.local.response["type"] = "text/xml"
    frappe.local.response["message"] = xml_response