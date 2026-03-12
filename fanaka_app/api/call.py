import frappe
import africastalking
from frappe import _

# 2026-03-12 15:01:45 - Debugged Internal Server Error for guest callbacks

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

        frappe.logger().info(f"AT Call Response: {response}")

        session_id = None
        if response.get("entries"):
            session_id = response["entries"][0].get("sessionId")

        # Create Initial Call Log
        if session_id:
            call_log = frappe.get_doc({
                "doctype": "Call Log",
                "id": session_id,
                "custom_session_id": session_id,
                "call_type": "Outgoing",
                "from": outbound_number,
                "to": phone_number,
                "status": "Ringing",
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "user_phone_number": phone_number
            })
            call_log.insert(ignore_permissions=True, ignore_mandatory=True)
            frappe.db.commit()

        return {
            "status": "success",
            "session_id": session_id
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("AT Make Call Failed"))
        return {
            "status": "error",
            "message": str(e)
        }


def log_call(data):
    """Updates or creates a Call Log based on AT webhook data using 'id'."""
    try:
        session_id = data.get("sessionId")
        if not session_id:
            return

        status_map = {
            "NotAnswered": "No Answer",
            "Completed": "Completed",
            "Busy": "Busy",
            "Failed": "Failed",
            "Ringing": "Ringing",
            "Queued": "Queued",
            "Cancelled": "Cancelled",
            "Aborted": "Failed"
        }

        status = status_map.get(data.get("status"), data.get("status", "Ringing"))
        
        # Capture Recording Info
        recording_url = data.get("recordingUrl")
        recording_html = ""
        if recording_url:
            recording_html = f'<audio controls src="{recording_url}" style="width: 100%; height: 35px;"></audio>'

        values = {
            "from": data.get("callerNumber"),
            "to": data.get("destinationNumber"),
            "duration": data.get("durationInSeconds") or 0,
            "status": status,
            "recording_url": recording_url,
            "recording_html": recording_html,
            "call_session_state": data.get("callSessionState"),
            "amount": data.get("amount") or 0,
            "currency_code": data.get("currencyCode")
        }

        # Query using the 'id' field. Using get_all to avoid permission issues sometimes present in get_value
        logs = frappe.get_all("Call Log", filters={"id": session_id}, fields=["name"], limit=1)
        existing_log_name = logs[0].name if logs else None

        if existing_log_name:
            frappe.db.set_value("Call Log", existing_log_name, values, update_modified=True)
        else:
            doc = frappe.get_doc({
                "doctype": "Call Log",
                "id": session_id,
                "custom_session_id": session_id,
                "call_type": "Incoming" if data.get("direction") == "Inbound" else "Outgoing",
                **values
            })
            doc.insert(ignore_permissions=True, ignore_mandatory=True)
        
        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("AT Call Log Update Failed"))


@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Main routing callback for Africa's Talking Voice."""
    try:
        data = frappe.form_dict
        frappe.logger().info(f"Voice Callback Request Data: {data}")
        
        log_call(data)

        is_active = str(data.get("isActive", "0"))
        direction = data.get("direction")
        session_id = data.get("sessionId")

        if is_active == "1":
            if direction == "Inbound":
                xml = """<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd: Your Ideal Real Estate Partner</Say>
                    <Dial phoneNumbers="+254714686511" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            elif direction == "Outbound":
                # Lookup user_phone_number by filtering on 'id'
                user_phone = None
                if session_id:
                    logs = frappe.get_all("Call Log", filters={"id": session_id}, fields=["user_phone_number"], limit=1)
                    if logs:
                        user_phone = logs[0].user_phone_number
                
                if not user_phone:
                    user_phone = "+254714686511"

                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Dial phoneNumbers="{user_phone}" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            else:
                xml = """<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd</Say>
                </Response>"""
        else:
            xml = """<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say>Hello, thank you for calling. This call is now connected.</Say>
            </Response>"""

        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Voice Callback Error"))
        # Ensure we always return valid XML even on error to prevent AT from retrying indefinitely
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>An internal error occurred.</Say></Response>'


@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Event callback for call status updates."""
    try:
        data = frappe.form_dict
        log_call(data)

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Hello, thank you for calling. This call is now connected.</Say>
        </Response>"""
        
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Voice Event Callback Error"))
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'