import frappe
from frappe import _
from datetime import datetime


# Last Updated: 2026-04-01 10:11 AM

class CommissionEngine:
    @staticmethod
    @frappe.whitelist()
    def calculate_junior_commission(collection_amount):
        amount = float(collection_amount)
        if amount > 7000000:
            rate = 0.035
        elif amount > 6000000:
            rate = 0.03
        elif amount > 4000000:
            rate = 0.025
        else:
            rate = 0.02
        return amount * rate, rate

    @staticmethod
    @frappe.whitelist()
    def calculate_senior_commission(collection_amount):
        amount = float(collection_amount)
        if amount > 7000000:
            rate = 0.04
        elif amount > 6000000:
            rate = 0.035
        elif amount > 4000000:
            rate = 0.03
        else:
            rate = 0.025
        return amount * rate, rate

    @staticmethod
    @frappe.whitelist()
    def calculate_hod_commission(collection_amount):
        amount = float(collection_amount)
        return amount * 0.03, 0.03

    @staticmethod
    @frappe.whitelist()
    def calculate_manager_performance_commission(collection_amount, plots_sold):
        """
        Calculates branch performance commission based on the better performing metric.

        Logic:
        Highest tier reached based on EITHER plots sold or collection amount.
        Targets: 42M Collection & 40 Plots.

        Tiers:
        - 100%+ Performance: 1.5%
        - 75% - 99.9% Performance: 1.2%
        - 50% - 74.9% Performance: 1.0%
        - Below 50% Performance: 0.75%
        """
        # Targets
        coll_target = 42000000.0
        plot_target = 40.0

        # Calculate individual performance ratios
        coll_ratio = (float(collection_amount) / coll_target) * 100
        plot_ratio = (float(plots_sold) / plot_target) * 100

        # Select the highest performance percentage between the two
        perf_percent = max(coll_ratio, plot_ratio)

        # Determine rate based on the highest tier reached
        if perf_percent >= 100:
            rate = 0.015
        elif perf_percent >= 75:
            rate = 0.012
        elif perf_percent >= 50:
            rate = 0.01
        else:
            rate = 0.0075

        # Calculate final commission based on total collection
        commission = float(collection_amount) * rate

        return commission, perf_percent, rate


@frappe.whitelist()
def get_commission_details(sales_person, collection_amount, personal_collection, plots_sold):
    sales_person_doc = frappe.get_doc("Sales Person", sales_person)
    role = str(sales_person_doc.custom_role or "").strip()

    engine = CommissionEngine()

    if "Manager" in role:
        branch_comm, perf_percent, branch_rate = engine.calculate_manager_performance_commission(
            collection_amount,
            plots_sold
        )
        personal_comm = float(personal_collection) * 0.03
        total_commission = branch_comm + personal_comm
        return {
            "total_commission": total_commission,
            "applied_rate": f"{branch_rate * 100}% (Performance) + 3% (Personal)",
        }
    elif "HOD" in role:
        total_commission, applied_rate = engine.calculate_hod_commission(collection_amount)
        return {
            "total_commission": total_commission,
            "applied_rate": f"{applied_rate * 100}%"
        }
    elif "Senior Sales" in role:
        total_commission, applied_rate = engine.calculate_senior_commission(collection_amount)
        return {
            "total_commission": total_commission,
            "applied_rate": f"{applied_rate * 100}%"
        }
    else:
        total_commission, applied_rate = engine.calculate_junior_commission(collection_amount)
        return {
            "total_commission": total_commission,
            "applied_rate": f"{applied_rate * 100}%"
        }


def calculate_commission(doc, method=None):
    """
    Triggered by after_insert hook.
    """
    sales_person_doc = frappe.get_doc("Sales Person", doc.sales_person)
    role = str(sales_person_doc.custom_role or "").strip()

    engine = CommissionEngine()
    total_commission = 0.0
    updates = {}

    if "Manager" in role:
        # 1. Personal Contribution Calculation (Fixed at 3%)
        p_coll = float(doc.personal_collection or 0)
        personal_comm = p_coll * 0.03

        # 2. Branch Performance Calculation (Variable Rate)
        branch_comm, perf, branch_rate = engine.calculate_manager_performance_commission(
            doc.collection_amount,
            doc.plots_sold
        )

        total_commission = branch_comm + personal_comm
        updates["rate"] = f"{branch_rate * 100}% (Performance) + 3% (Personal)"

    elif "Senior Sales" in role:
        total_commission, applied_rate = engine.calculate_senior_commission(doc.collection_amount)
        updates["rate"] = f"{applied_rate * 100}%"
    elif "HOD" in role:
        total_commission, applied_rate = engine.calculate_hod_commission(doc.collection_amount)
        updates["rate"] = f"{applied_rate * 100}%"
    else:
        total_commission, applied_rate = engine.calculate_junior_commission(doc.collection_amount)
        updates["rate"] = f"{applied_rate * 100}%"

    updates["commission_amount"] = total_commission

    # Update fields in the database
    for field, value in updates.items():
        doc.db_set(field, value)


def process_commission_to_salary(doc, method=None):
    """
    Triggered by on_submit hook.
    """
    if doc.commission_amount > 0:
        create_additional_salary(doc, doc.commission_amount)


def create_additional_salary(doc, amount):
    try:
        sales_person = frappe.get_doc("Sales Person", doc.sales_person)
        if not sales_person.employee:
            return

        employee = frappe.get_doc("Employee", sales_person.employee)

        add_sal = frappe.get_doc({
            "doctype": "Additional Salary",
            "employee": employee.name,
            "salary_component": "COMMISSIONS",
            "amount": amount,
            "payroll_date": doc.posting_date or datetime.now().date(),
            "ref_doctype": "Commission Entry",
            "ref_docname": doc.name,
            "overwrite_salary_structure_amount": 0
        })
        add_sal.insert(ignore_permissions=True)
        add_sal.submit()

    except Exception as e:
        frappe.log_error(message=str(e), title="Commission Salary Push Error")