import frappe
import africastalking
from frappe import _

# 2026-03-13 20:42:15 - Logic Sync: Refined voice_callback to match working PHP structure
# 2026-03-13 20:58:15 - Logic Update: Disabled Call Log database persistence to focus on callback stability

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
    """
    Main routing callback for Africa's Talking Voice (Action URL).
    Logic synced with working PHP implementation.
    """
    try:
        # Use frappe.request.values to handle both POST and GET parameters safely
        data = frappe.request.values
        is_active = data.get('isActive')
        direction = data.get('direction')
        
        # PHP equivalent: Log::info('Inbound ', request()->all());
        # frappe.log_error(f"Voice Callback: {direction}", str(data))

        xml_content = ""

        if str(is_active) == "1":
            if direction == 'Inbound':
                xml_content = """<Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd: Your Ideal Real Estate Partner</Say>
                    <Dial phoneNumbers="+254714686511" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            
            elif direction == 'Outbound':
                # In the PHP code, this fetched a specific user phone or defaulted
                user_phone = "+254714686511"
                xml_content = f"""<Response>
                    <Dial phoneNumbers="{user_phone}" record="true" maxDuration="10" sequential="true"/>
                </Response>"""
            
            else:
                xml_content = """<Response>
                    <Say voice="en-US-Standard-C" playBeep="false">Welcome to Fanaka Real Estate Ltd: </Say>
                </Response>"""
        else:
            # isActive is 0 or not present
            xml_content = """<Response>
                <Say>Hello, thank you for calling. This call is now connected.</Say>
            </Response>"""

        # Ensure the response is wrapped in the standard XML header
        full_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}'

        # Setting response headers correctly to avoid 500 errors
        frappe.response["type"] = "text/xml"
        frappe.response["display_content"] = full_xml
        # Direct return of the string helps some Frappe versions identify the response body
        return full_xml

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Callback Error")
        # Return a neutral empty response to stop AT from retrying with errors
        frappe.response["type"] = "text/xml"
        return '<?xml version="1.0" encoding="UTF-8"?><Response/>'


@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Event callback for call status updates (Status Callback URL)."""
    try:
        # PHP implementation simply acknowledged with a connected message
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Hello, thank you for calling. This call is now connected.</Say>
        </Response>"""
        
        frappe.response["type"] = "text/xml"
        frappe.response["display_content"] = xml_response
        return xml_response
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")
        frappe.response["type"] = "text/xml"
        return '<?xml version="1.0" encoding="UTF-8"?><Response/>'