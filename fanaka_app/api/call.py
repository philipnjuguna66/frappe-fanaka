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
    pass


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
                #frappe.db.get_value("Call Log", {"id": session_id}, "user_phone_number") or
            elif direction == "Outbound":
                user_phone =  "+254714686511"
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