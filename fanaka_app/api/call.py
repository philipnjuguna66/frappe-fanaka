import frappe
import africastalking
from frappe import _

# 2026-03-13 20:45:12 - Fixed LinkValidationError: Ensured reference fields are cleared for new logs to avoid ERPNext telephony hooks failing
# 2026-03-13 20:39:45 - Fixed DuplicateEntryError: Added ignore_if_duplicate and refined lookup logic
# 2026-03-13 20:35:10 - Fixed Status Mapping: Handled "Aborted" and "Hangup" to match DocType Select options

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

        if session_id:
            try:
                doc = frappe.new_doc("Call Log")
                doc.id = session_id
                doc.custom_session_id = session_id
                doc.call_type = "Outgoing"
                doc.set("from", outbound_number)
                doc.set("to", phone_number)
                doc.status = "Ringing"
                
                # Only set references if they are actually provided
                if reference_doctype and reference_name:
                    doc.reference_doctype = reference_doctype
                    doc.reference_name = reference_name
            
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
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
        at_status = data.get('status')

        if session_id and at_status:
            frappe_status = map_at_status(at_status)
            
            # Lookup the document name by the custom_session_id field
            doc_name = frappe.db.get_value("Call Log", {"custom_session_id": session_id}, "name")
            
            # Fallback to direct name lookup
            if not doc_name and frappe.db.exists("Call Log", session_id):
                doc_name = session_id

            if doc_name:
                doc = frappe.get_doc("Call Log", doc_name)
                doc.status = frappe_status
                
                if at_status == "Answered":
                    doc.call_start_time = data.get('callStartTime')
                
                if data.get('durationInSeconds'):
                    doc.call_duration = data.get('durationInSeconds')
                
                if data.get('hangupCause'):
                    doc.hangup_cause = data.get('hangupCause')
                
                doc.save(ignore_permissions=True)
            else:
                # 2026-03-13: Fixed LinkValidationError by ensuring references are empty for Inbound/Untracked calls
                # ERPNext telephony hooks fail if they find a reference name that isn't a valid DB link
                new_log = frappe.new_doc("Call Log")
                new_log.id = session_id
                new_log.custom_session_id = session_id
                new_log.status = frappe_status
                new_log.call_type = data.get('direction', 'Inbound')
                new_log.set("from", data.get('callerNumber'))
                new_log.set("to", data.get('destinationNumber'))
                
                # Explicitly clear these to prevent erpnext.telephony.doctype.call_log.call_log.after_insert from crashing
                new_log.reference_doctype = None
                new_log.reference_name = None
                
                if data.get('durationInSeconds'):
                    new_log.call_duration = data.get('durationInSeconds')
                
                if data.get('callStartTime'):
                    new_log.call_start_time = data.get('callStartTime')
                
                # Use ignore_if_duplicate to handle AT's multi-event bursts
                new_log.insert(ignore_permissions=True, ignore_if_duplicate=True)
            
            frappe.db.commit()

        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'
        
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Voice Event Callback Error")
        frappe.response["type"] = "text/xml"
        frappe.response["message"] = '<?xml version="1.0" encoding="UTF-8"?><Response/>'