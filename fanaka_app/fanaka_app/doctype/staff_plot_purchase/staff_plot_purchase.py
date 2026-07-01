# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document

MIS_ERP_ENDPOINT = "/api/v1/webhook/staff-plot-payment"


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_plots(doctype, txt, searchfield, start, page_len, filters):
    """Plot picker for Staff Plot Purchase. Lists plots of the selected project
    (matched by project link OR project_name, since plots may only carry the
    name) or of a specific plot list (from a sale order). Shows every status and
    appends the buyer for sold plots.
    """
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})

    conditions = []
    values = {"txt": f"%{txt or ''}%", "start": start, "page_len": page_len}

    if filters.get("plots"):
        placeholders = ", ".join([f"%(plot{i})s" for i in range(len(filters["plots"]))])
        for i, p in enumerate(filters["plots"]):
            values[f"plot{i}"] = p
        conditions.append(f"p.name in ({placeholders})")
    elif filters.get("project"):
        values["project"] = filters["project"]
        values["project_name"] = frappe.db.get_value("Project", filters["project"], "project_name")
        conditions.append("(p.project = %(project)s or p.project_name = %(project_name)s)")

    where = " and ".join(conditions) if conditions else "1 = 1"

    return frappe.db.sql(
        f"""
        select p.name,
               concat(
                   coalesce(p.plot_no, p.name),
                   ' — ', coalesce(p.status, ''),
                   case when p.status = 'SOLD' and coalesce(p.customer_name, '') != ''
                        then concat(' · ', p.customer_name) else '' end
               ) as description
        from `tabPlot` p
        where {where}
          and (p.plot_no like %(txt)s or p.name like %(txt)s or p.customer_name like %(txt)s)
        order by p.plot_no asc
        limit %(start)s, %(page_len)s
        """,
        values,
    )


class StaffPlotPurchase(Document):
    def on_submit(self):
        self.create_additional_salary()
        self.notify_mis_erp()

    def on_cancel(self):
        # Cancel the linked Additional Salary so payroll doesn't keep deducting.
        if self.additional_salary and frappe.db.exists("Additional Salary", self.additional_salary):
            ad = frappe.get_doc("Additional Salary", self.additional_salary)
            if ad.docstatus == 1:
                ad.cancel()

    def create_additional_salary(self):
        if self.additional_salary:
            return

        company = frappe.db.get_value("Employee", self.staff, "company")

        additional_salary = frappe.get_doc({
            "doctype": "Additional Salary",
            "employee": self.staff,
            "salary_component": self.salary_component,
            "amount": self.amount,
            "payroll_date": self.payroll_date,
            "company": company,
            "custom_plot": self.plot,
            "custom_payment_method": self.payment_method,
            "overwrite_salary_structure_amount": 1,
        })
        additional_salary.insert()
        additional_salary.submit()

        self.db_set("additional_salary", additional_salary.name)

    def notify_mis_erp(self):
        plot = frappe.db.get_value(
            "Plot", self.plot, ["plot_id", "project_name", "plot_no"], as_dict=True
        )
        if not plot:
            frappe.log_error(f"Plot {self.plot} not found", "staff plot purchase")
            return

        base_url = frappe.conf.get("mis_erp_url")
        secret = frappe.conf.get("mis_erp_webhook_secret")
        if not base_url or not secret:
            frappe.log_error("mis_erp_url / mis_erp_webhook_secret not configured", "staff plot purchase")
            return

        payload = {
            "plot_id": plot.plot_id,
            "project": plot.project_name,
            "plot_no": plot.plot_no,
            "amount": self.amount,
            "payroll_date": str(self.payroll_date or frappe.utils.nowdate()),
            "payment_method": self.payment_method,
            "bank": self.bank,
            "comment": f"Staff Plot Purchase {self.name} for {self.staff}",
        }

        try:
            response = requests.post(
                base_url.rstrip("/") + MIS_ERP_ENDPOINT,
                json=payload,
                headers={"X-Webhook-Secret": secret, "Accept": "application/json"},
                timeout=30,
            )
            if response.status_code >= 300:
                frappe.log_error(response.text, "staff plot purchase webhook failed")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "staff plot purchase webhook error")
