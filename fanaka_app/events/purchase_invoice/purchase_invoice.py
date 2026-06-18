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
        item.project = doc.project
        if project_cost_center and not item.get("cost_center"):
            item.cost_center = project_cost_center

        # Serialised items need either a Serial & Batch Bundle or the plain
        # serial_no field. Use the plain field (use_serial_batch_fields = 1) so
        # no Serial No Series is required on the item.
        has_serial_no = frappe.db.get_value("Item", item.item_code, "has_serial_no")
        if has_serial_no:
            item.use_serial_batch_fields = 1
            item.serial_no = serial
