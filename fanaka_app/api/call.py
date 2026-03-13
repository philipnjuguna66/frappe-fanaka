import frappe
import africastalking
import traceback
from frappe import _

# ---------------------------------------------------------
# UTILITY: Send valid XML response
# ---------------------------------------------------------
def xml_response(body: str):
    """Set Frappe response to valid XML with proper headers."""
    frappe.local.response["type"] = "xml"
    frappe.local.response["response"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n{body.strip()}\n</Response>'
    )

STATUS_MAP = {
    # Common final / terminal states
    "Completed":        "COMPLETED",         # fully connected & ended normally
    "Aborted":          "ABORTED",           # dropped very early (network, user hung up immediately)
    "Busy":             "BUSY",
    "No Answer":        "NO_ANSWER",
    "Failed":           "FAILED",            # network/carrier failure
    "Rejected":         "REJECTED",          # callee rejected
    # Mid-call / transitional (sometimes appear in events)
    "Ringing":          "RINGING",
    "Ongoing":          "IN_PROGRESS",
    # Rare / AMD (answering machine detection) related if enabled
    "Machine":          "ANSWERING_MACHINE",
    # Fallback
    "UNKNOWN":          "UNKNOWN"
}

@frappe.whitelist(allow_guest=True)
def voice_event_callback():
    """Minimal Africa's Talking voice event/status callback — no DB writes."""
    try:
        data = frappe.form_dict or {}
        
        # Keep raw log for debugging (you'll see these in Error Log)
        frappe.log_error(frappe.as_json(data), "AT Voice Event - Raw Payload")

        # ────────────────────────────────────────────────
        # Extract the two most useful status fields
        # ────────────────────────────────────────────────
        at_status           = data.get("status", "").strip()                # main status
        call_session_state  = data.get("callSessionState", "").strip()      # sometimes more precise final cause

        # Prefer callSessionState when present (more detailed for final events)
        effective_status = call_session_state or at_status or "MISSING"

        # Map to internal friendly name
        internal_status = STATUS_MAP.get(effective_status, "UNKNOWN")

        # Quick summary line — easy to grep / monitor
        summary = (
            f"Call Event | "
            f"session: {data.get('sessionId', '—')} | "
            f"direction: {data.get('direction', '—')} | "
            f"raw_status: {effective_status} → {internal_status} | "
            f"duration: {data.get('durationInSeconds', '—')}s | "
            f"from: {data.get('callerNumber', '—')} → {data.get('destinationNumber', '—')}"
        )

        # Log the summary (visible in Error Log or site console)
        frappe.log_error(summary, "AT Voice Event - Summary")

        # Optional: extra logging for specific cases you care about right now
        if internal_status in ("ABORTED", "NO_ANSWER", "BUSY"):
            frappe.log_error(
                f"Missed/Short call detected: {summary}\nRaw: {frappe.as_json(data)}",
                "AT Voice - Potential Missed Call"
            )

        # ────────────────────────────────────────────────
        # Always respond quickly with 200 OK + minimal XML
        # ────────────────────────────────────────────────
        xml_response("""
            <Response>
                <Say>Event received.</Say>
            </Response>
        """)

    except Exception:
        frappe.log_error(traceback.format_exc(), "AT Voice Event Callback - Exception")
        # Still return 200 — critical!
        xml_response("""
            <Response>
                <Say>System received event.</Say>
            </Response>
        """)