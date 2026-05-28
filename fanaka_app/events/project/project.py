import frappe
from frappe.utils import flt


def validate(doc, method=None):
    """Sum block acreage + purchase price into Project totals.
    Enforce unique block numbers within the project."""
    blocks = list(getattr(doc, "custom_blocks", []) or [])

    seen = set()
    for b in blocks:
        if not b.block_number:
            continue
        key = (b.block_number or "").strip()
        if key in seen:
            frappe.throw(f"Block number {key} is duplicated. Each block must have a unique number within the project.")
        seen.add(key)

    doc.custom_total_acreage = sum(flt(b.acreage) for b in blocks)
    doc.custom_total_purchase_price = sum(flt(b.purchase_price) for b in blocks)


def after_insert(doc, method=None):
    """Create a Cost Center per Project under the company's main CC if not already linked."""
    if doc.cost_center:
        return
    if not doc.company:
        return

    parent_cc = frappe.db.get_value(
        "Cost Center",
        {"company": doc.company, "is_group": 1, "parent_cost_center": ["is", "not set"]},
        "name",
    ) or frappe.db.get_value(
        "Cost Center", {"company": doc.company, "is_group": 1}, "name"
    )

    if not parent_cc:
        return

    cc_name = f"{doc.project_name or doc.name} - {frappe.db.get_value('Company', doc.company, 'abbr')}"
    if frappe.db.exists("Cost Center", cc_name):
        doc.db_set("cost_center", cc_name)
        return

    cc = frappe.new_doc("Cost Center")
    cc.cost_center_name = doc.project_name or doc.name
    cc.parent_cost_center = parent_cc
    cc.company = doc.company
    cc.is_group = 0
    cc.flags.ignore_permissions = True
    try:
        cc.insert()
        doc.db_set("cost_center", cc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Fanaka Project: Cost Center create failed")
