import frappe
import africastalking
from frappe import _

# 2026-03-12 14:48:00 - Optimized for stability and XML response handling

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
                "name": session_id,  # Use sessionId as the primary key
                "call_type": "Outgoing",
                "from": outbound_number,
                "to": phone_number,
                "status": "Ringing",
                "reference_doctype": reference_doctype,
                "reference_name": reference_name
            })
            call_log.insert(ignore_permissions=True)
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
    """Updates or creates a Call Log based on AT webhook data."""
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

        status = status_map.get(data.get("status"), "Failed")
        
        values = {
            "from": data.get("callerNumber"),
            "to": data.get("destinationNumber"),
            "duration": data.get("durationInSeconds") or 0,
            "status": status
        }

        if frappe.db.exists("Call Log", session_id):
            frappe.db.set_value("Call Log", session_id, values, update_modified=True)
        else:
            doc = frappe.get_doc({
                "doctype": "Call Log",
                "name": session_id,
                "call_type": "Incoming" if data.get("direction") == "Inbound" else "Outgoing",
                **values
            })
            doc.insert(ignore_permissions=True)
        
        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("AT Call Log Update Failed"))


@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Main routing callback for Africa's Talking Voice."""
    try:
        # Use frappe.form_dict to capture POST data reliably
        data = frappe.form_dict
        
        log_call(data)

        is_active = data.get("isActive")
        direction = data.get("direction")

        if is_active == "1":
            if direction == "Inbound":
                xml = """<Response>
                            <Say>Welcome to Fanaka Real Estate Limited.</Say>
                            <Dial phoneNumbers="+254714686511" record="true"/>
                         </Response>"""
            else:
                # For outbound calls, we usually just want to connect
                xml = """<Response>
                            <Say>Connecting your call</Say>
                         </Response>"""
        else:
            xml = "<Response></Response>"

        # Set response headers and content
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Voice Callback Error"))
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = "<Response></Response>"


@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Event callback for call status updates."""
    try:
        data = frappe.form_dict
        log_call(data)

        # Standard acknowledgment for AT
        xml = "<Response></Response>"
        
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = xml
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Voice Event Callback Error"))
        frappe.local.response["type"] = "text/xml"
        frappe.local.response["message"] = "<Response></Response>"