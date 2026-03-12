import frappe
import africastalking
from frappe import _

# 2026-03-12 15:05:10 - Fixed 500 Error: Optimized guest access and database lookups

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

        if session_id:
            # Create Initial Call Log using a dict to be safer with guest permissions
            try:
                doc = frappe.new_doc("Call Log")
                doc.id = session_id
                doc.custom_session_id = session_id
                doc.call_type = "Outgoing"
                doc.set("from", outbound_number)
                doc.set("to", phone_number)
                doc.status = "Ringing"
                doc.reference_doctype = reference_doctype
                doc.reference_name = reference_name
                doc.user_phone_number = phone_number
                doc.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Initial Log Creation Failed: {str(e)}", "AT Make Call")

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
            "Ringing": "Ringing"
        }

        status = status_map.get(data.get("status"), data.get("status", "Ringing"))
        
        recording_url = data.get("recordingUrl")
        recording_html = f'<audio controls src="{recording_url}" style="width: 100%; height: 35px;"></audio>' if recording_url else ""

        # Using frappe.db.get_value with a simple filter is the safest for guest SQL access
        existing_log = frappe.db.get_value("Call Log", {"id": session_id}, "name")

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

        if existing_log:
            frappe.db.set_value("Call Log", existing_log, values, update_modified=True)
        else:
            doc = frappe.new_doc("Call Log")
            doc.id = session_id
            doc.custom_session_id = session_id
            doc.call_type = "Incoming" if data.get("direction") == "Inbound" else "Outgoing"
            doc.update(values)
            doc.insert(ignore_permissions=True)
        
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Log Call Failed: {str(e)}", "AT Webhook Update")


@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Main routing callback for Africa's Talking Voice."""
    try:
        # data = frappe.form_dict
        data = frappe.request.form.to_dict() # More reliable for some WSGI configs
        
        log_call(data)

        is_active = str(data.get("isActive", "0"))
        direction = data.get("direction")
        session_id = data.get("sessionId")

        if is_active == "1":
            if direction == "Inbound":
                xml = """<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd</Say>
                    <Dial phoneNumbers="+254714686511" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            elif direction == "Outbound":
                user_phone = frappe.db.get_value("Call Log", {"id": session_id}, "user_phone_number") or "+254714686511"
                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Dial phoneNumbers="{user_phone}" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            else:
                xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Welcome</Say></Response>'
        else:
            xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Call ending</Say></Response>'

        frappe.response["type"] = "text/xml"
        frappe.response["message"] = xml

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Callback Error")
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'


@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Event callback for call status updates."""
    try:
        data = frappe.request.form.to_dict()
        log_call(data)
        
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        
    except Exception:
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'