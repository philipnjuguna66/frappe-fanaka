"""On submit of a Staff Plot Purchase Additional Salary, tell mis-erp to record
the salary deduction as a payment against the staff member's plot sale.

mis-erp endpoint + shared secret are read from the site config:

    bench --site <site> set-config mis_erp_url https://v3.fanaka.co.ke
    bench --site <site> set-config mis_erp_webhook_secret <secret>
"""

import frappe
import requests

SALARY_COMPONENT = "Staff Plot Purchase"
ENDPOINT = "/api/v1/webhook/staff-plot-payment"


def notify_mis_erp(doc, method=None):
    if doc.salary_component != SALARY_COMPONENT or not doc.get("custom_plot"):
        return

    plot = frappe.db.get_value(
        "Plot", doc.custom_plot,
        ["plot_id", "project_name", "plot_no"], as_dict=True,
    )
    if not plot:
        frappe.log_error(f"Plot {doc.custom_plot} not found", "staff plot payment")
        return

    base_url = frappe.conf.get("mis_erp_url")
    secret = frappe.conf.get("mis_erp_webhook_secret")
    if not base_url or not secret:
        frappe.log_error("mis_erp_url / mis_erp_webhook_secret not configured", "staff plot payment")
        return

    payload = {
        "plot_id": plot.plot_id,
        "project": plot.project_name,
        "plot_no": plot.plot_no,
        "amount": doc.amount,
        "payroll_date": str(doc.payroll_date or frappe.utils.nowdate()),
        "payment_method": doc.get("custom_payment_method") or "Salary",
        "comment": f"Salary deduction {doc.name} for {doc.employee_name}",
    }

    try:
        response = requests.post(
            base_url.rstrip("/") + ENDPOINT,
            json=payload,
            headers={"X-Webhook-Secret": secret, "Accept": "application/json"},
            timeout=30,
        )
        if response.status_code >= 300:
            frappe.log_error(response.text, "staff plot payment webhook failed")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "staff plot payment webhook error")
