"""Daily expiry reminders for vehicle insurance and driver licences.

Scheduled via ``scheduler_events.daily`` in hooks.py. For every Vehicle whose
insurance (``end_date``) or Driver whose licence (``expiry_date``) falls due in
exactly one month, in seven days, or today, an email is sent to the linked
Employee. Matching on the exact milestone date means each record is mailed once
per milestone without any extra bookkeeping.
"""

import frappe
from frappe.utils import add_days, formatdate, getdate, nowdate

# days-before-expiry -> human label, in send order
MILESTONES = {
    30: "in one month",
    7: "in 7 days",
    0: "today",
}


def run():
    """Scheduler entry point."""
    today = getdate(nowdate())

    # milestone date (as 'YYYY-MM-DD') -> label
    targets = {str(add_days(today, days)): label for days, label in MILESTONES.items()}

    _remind_vehicles(targets)
    _remind_drivers(targets)


def _remind_vehicles(targets):
    rows = frappe.get_all(
        "Vehicle",
        filters={"end_date": ["in", list(targets.keys())]},
        fields=["name", "license_plate", "make", "model", "end_date",
                "employee", "insurance_company"],
    )

    for v in rows:
        email = _employee_email(v.employee)
        if not email:
            frappe.logger().info(f"Vehicle {v.name}: no employee email, skipped")
            continue

        label = targets.get(str(getdate(v.end_date)))
        vehicle = " ".join(filter(None, [v.license_plate or v.name, v.make, v.model]))
        insurer = f" with {v.insurance_company}" if v.insurance_company else ""

        _send(
            email,
            subject=f"Vehicle insurance expiring {label}: {v.license_plate or v.name}",
            body=(
                f"<p>The insurance{insurer} for vehicle <b>{vehicle}</b> "
                f"expires <b>{label}</b> ({formatdate(v.end_date)}).</p>"
                f"<p>Please arrange renewal.</p>"
            ),
        )


def _remind_drivers(targets):
    rows = frappe.get_all(
        "Driver",
        filters={"expiry_date": ["in", list(targets.keys())]},
        fields=["name", "full_name", "expiry_date", "employee",
                "license_number"],
    )

    for d in rows:
        email = _employee_email(d.employee)
        if not email:
            frappe.logger().info(f"Driver {d.name}: no recipient email, skipped")
            continue

        label = targets.get(str(getdate(d.expiry_date)))
        number = f" ({d.license_number})" if d.license_number else ""

        _send(
            email,
            subject=f"Driving licence expiring {label}: {d.full_name or d.name}",
            body=(
                f"<p>The driving licence{number} for <b>{d.full_name or d.name}</b> "
                f"expires <b>{label}</b> ({formatdate(d.expiry_date)}).</p>"
                f"<p>Please arrange renewal.</p>"
            ),
        )


def _employee_email(employee):
    if not employee:
        return None

    row = frappe.db.get_value(
        "Employee",
        employee,
        ["user_id", "company_email", "personal_email", "prefered_email"],
        as_dict=True,
    )

    if not row:
        return None

    return row.user_id or row.company_email or row.personal_email or row.prefered_email


def _send(recipient, subject, body):
    try:
        frappe.sendmail(recipients=[recipient], subject=subject, message=body)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Expiry reminder email failed")
