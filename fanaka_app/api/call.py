import frappe
import africastalking
from frappe import _

# 2026-03-13 20:58:15 - Logic Update: Disabled Call Log database persistence to focus on callback stability
# 2026-03-13 20:53:10 - Fixed LinkValidationError: Bypassed after_insert hooks using db_insert for new logs

def map_at_status(at_status):
    """Maps Africa's Talking status to Fanaka Call Log Select options."""
    mapping = {
        "Aborted": "Cancelled",
        "Hangup": "Completed",
        "Completed": "Completed",
        "Answered": "In Progress",
        "Ringing": "Ringing",
        "Dialing": "Ringing",
        "Failed": "Failed",
        "Busy": "Busy",
        "NoAnswer": "No Answer"
    }
    return mapping.get(at_status, "Completed")

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

        # Database saving is currently ignored to prevent insertion/validation errors
        # if session_id:
        #     pass 

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
        # 2026-03-13: Database saving is currently disabled. 
        # We only acknowledge the event to keep Africa's Talking happy.
        
        # We can still log the data to the Error Log for debugging if needed, 
        # but we avoid 'Call Log' document operations.
        # data = frappe.form_dict
        # frappe.log_error(str(data), "AT Voice Event Debug")

        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'