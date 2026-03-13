import frappe
import africastalking
from frappe import _

# 2026-03-13 20:31:45 - Fixed ValidationError: Explicitly setting 'id' field for new_log naming
# 2026-03-13 20:25:30 - Improved Lookup: Using custom_session_id for database queries instead of doc name
# 2026-03-13 20:22:15 - Final Fix: Removed unused ElementTree and secured form_dict extraction

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
            try:
                # 2026-03-13: Setting custom_session_id and id for consistency
                doc = frappe.new_doc("Call Log")
                doc.id = session_id
                doc.custom_session_id = session_id
                doc.call_type = "Outgoing"
                doc.set("from", outbound_number)
                doc.set("to", phone_number)
                doc.status = "Ringing"
                doc.reference_doctype = reference_doctype
                doc.reference_name = reference_name
            
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


@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Main routing callback for Africa's Talking Voice (Action URL)."""
    try:
        data = frappe.form_dict
        is_active = data.get('isActive')
        direction = data.get('direction')

        if is_active == "1":
            if direction == "Inbound":
                xml = """<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd</Say>
                    <Dial phoneNumbers="+254714686511" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            elif direction == "Outbound":
                user_phone = "+254714686511"
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
    """Event callback for call status updates (Status Callback URL)."""
    try:
        data = frappe.form_dict
        session_id = data.get('sessionId')
        status = data.get('status')

        if session_id and status:
            # Lookup the document name by the custom_session_id field
            doc_name = frappe.db.get_value("Call Log", {"custom_session_id": session_id}, "name")

            if doc_name:
                doc = frappe.get_doc("Call Log", doc_name)
                doc.status = status
                
                if status == "Answered":
                    doc.call_start_time = data.get('callStartTime')
                
                if data.get('durationInSeconds'):
                    doc.call_duration = data.get('durationInSeconds')
                
                if data.get('hangupCause'):
                    doc.hangup_cause = data.get('hangupCause')
                
                doc.save(ignore_permissions=True)
            else:
                # 2026-03-13: Ensure 'id' is set to session_id to satisfy naming requirements
                new_log = frappe.new_doc("Call Log")
                new_log.id = session_id
                new_log.custom_session_id = session_id
                new_log.status = status
                new_log.call_type = data.get('direction', 'Inbound')
                new_log.set("from", data.get('callerNumber'))
                new_log.set("to", data.get('destinationNumber'))
                
                if data.get('durationInSeconds'):
                    new_log.call_duration = data.get('durationInSeconds')
                
                if data.get('callStartTime'):
                    new_log.call_start_time = data.get('callStartTime')
                
                new_log.insert(ignore_permissions=True)
            
            frappe.db.commit()

        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'