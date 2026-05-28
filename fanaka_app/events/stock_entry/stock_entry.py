import frappe
import re


def generate_plot_serial_numbers(doc, event):
    """Legacy: write a project-derived serial onto each item row.

    Skip entirely when:
      - doc has no project linked (no source to derive from), OR
      - any item uses its own Serial Number Series (auto-generated serials
        from Item.serial_no_series take precedence — overwriting them would
        force duplicate serials across rows and break serialized inventory).
    """
    if not doc.get("project"):
        return

    items = list(doc.get("items") or [])
    if not items:
        return

    for it in items:
        if not it.get("item_code"):
            continue
        if frappe.db.get_value("Item", it.item_code, "serial_no_series"):
            return

    project = frappe.get_doc("Project", doc.project)
    serial = re.sub(r"[\W]+", "_", (project.project_name or "").lower()).strip("_")
    if not serial:
        return

    for item in items:
        item.serial_no = serial
