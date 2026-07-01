# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document

MIS_ERP_ENDPOINT = "/api/v1/webhook/staff-plot-payment"


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
