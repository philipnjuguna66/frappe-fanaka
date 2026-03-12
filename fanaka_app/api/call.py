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
            "id": frappe.generate_hash(length=10),
            "call_type": "Outgoing",
            "from": outbound_number,
            "to": phone_number,
            "status": "Initiated",
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
        {"custom_session_id": session_id}
    )

    values = {
        "doctype": "Call Log",
        "custom_session_id": session_id,
        "call_type": "Incoming" if data.get("direction") == "Inbound" else "Outgoing",
        "from": data.get("callerNumber"),
        "to": data.get("destinationNumber"),
        "duration": data.get("durationInSeconds"),
        "status": data.get("status"),
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

    request = frappe.local.request
    data = request.form.to_dict()

    frappe.logger().info({
        "voice_callback_data": data,
        "headers": dict(request.headers)
    })

    session_id = data.get("sessionId")
    direction = data.get("direction")
    is_active = data.get("isActive")

    log_call(data)

    # Only act when call is active
    if is_active == "1":

        # -------------------------------------------------
        # INBOUND CALL
        # -------------------------------------------------

        if direction == "Inbound":

            xml_response = """
<Response>
    <Say voice="en-US-Standard-C" playBeep="false">
        Welcome to Fanaka Real Estate Limited.
        Your Ideal Real Estate Partner.
    </Say>

    <Dial
        phoneNumbers="+254714686511"
        record="true"
        maxDuration="10"
        sequential="true"
    />
</Response>
"""

            frappe.local.response["type"] = "text/xml"
            frappe.local.response["message"] = xml_response
            return


        # -------------------------------------------------
        # OUTBOUND CALL
        # -------------------------------------------------

        if direction == "Outbound":

            user_phone = frappe.db.get_value(
                "Call Log",
                {"custom_session_id": session_id},
                "custom_user_phone_number"
            )

            if not user_phone:
                user_phone = "+254714686511"

            xml_response = f"""
<Response>
    <Dial
        phoneNumbers="{user_phone}"
        record="true"
        maxDuration="10"
        sequential="true"
    />
</Response>
"""

            frappe.local.response["type"] = "text/xml"
            frappe.local.response["message"] = xml_response
            return


        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------

        xml_response = """
<Response>
    <Say>
        Welcome to Fanaka Real Estate Limited.
    </Say>
</Response>
"""

        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml_response
        return


    return ""


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