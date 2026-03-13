import frappe
import africastalking
from frappe import _
import xml.etree.ElementTree as ET

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
    frappe.log_error(str(data), "AT Callback Data")


@frappe.whitelist(allow_guest=True)
def voice_callback():
    """Main routing callback for Africa's Talking Voice."""
    try:
        xml_data = frappe.request.data.decode('utf-8')
        log_call(xml_data)

        root = ET.fromstring(xml_data)
        is_active = root.find('isActive').text

        if is_active == "1":
            direction = root.find('direction').text
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
    """Event callback for call status updates."""
    try:
        xml_data = frappe.request.data.decode('utf-8')
        log_call(xml_data)
        
        root = ET.fromstring(xml_data)
        
        session_id = root.find('sessionId').text
        status = root.find('status').text

        if session_id and status:
            if frappe.db.exists("Call Log", session_id):
                doc = frappe.get_doc("Call Log", session_id)
                doc.status = status
                if status == "Answered":
                    doc.call_start_time = root.find('callStartTime').text
                elif status == "Hangup":
                    doc.hangup_cause = root.find('hangupCause').text
                    doc.call_duration = root.find('durationInSeconds').text
                
                doc.save(ignore_permissions=True)
                frappe.db.commit()

        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'