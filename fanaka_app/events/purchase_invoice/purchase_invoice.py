import frappe
import re


def create_purchase_invoice(doc, event):
    """Tie a land Purchase Invoice to its Project.

    The Purchase Invoice itself posts to the GL on submit (standard ERPNext),
    so no manual Journal Entry is needed. Here we just make sure every line
    carries the project and its cost center, so the GL entries are attributed
    to the right project. The user still selects the company and the expense /
    asset accounts on the invoice.
    """
    # Track stock for the land/plot items.
    doc.update_stock = 1

    if not doc.get("project"):
        frappe.throw("Project is not set on the Purchase Invoice.")

    project = frappe.get_doc("Project", doc.project)

    # Per-project cost center (auto-created on the Project). Fall back to the
    # invoice header cost center if the project has none yet.
    project_cost_center = project.get("cost_center") or doc.get("cost_center")

    # Serial derived from the project name, e.g. "Green Park" -> "green_park".
    serial = re.sub(r"[\W]+", "_", (project.project_name or project.name).lower()).strip("_")

    for item in doc.items:
        item.serial_no = serial
        item.project = doc.project
        if project_cost_center and not item.get("cost_center"):
            item.cost_center = project_cost_center
