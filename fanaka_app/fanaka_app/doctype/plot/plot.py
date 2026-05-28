# Copyright (c) 2025, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


SERIAL_STATUS_MAP = {
    "Active": "In Stock",
    "Inactive": "Reserved",
    "Delivered": "Sold",
    "Expired": "Not in Stock",
}


class Plot(Document):
    def validate(self):
        if self.custom_item:
            item = frappe.db.get_value(
                "Item", self.custom_item, ["is_stock_item", "has_serial_no"], as_dict=True
            )
            if not item:
                frappe.throw(f"Item {self.custom_item} not found")
            if not item.is_stock_item or not item.has_serial_no:
                frappe.throw(
                    f"Item {self.custom_item} must be a stock item with serial tracking enabled"
                )

        if self.custom_serial_no:
            sn_status = frappe.db.get_value("Serial No", self.custom_serial_no, "status")
            mapped = SERIAL_STATUS_MAP.get(sn_status)
            if mapped:
                self.custom_stock_status = mapped

        if self.status == "SOLD" and self.custom_serial_no:
            sn_status = frappe.db.get_value("Serial No", self.custom_serial_no, "status")
            if sn_status != "Delivered":
                frappe.throw(
                    "Cannot mark Plot as SOLD until its Serial No has been delivered via "
                    "Delivery Note / Sales Invoice (Update Stock). Serial currently: "
                    f"{sn_status or 'unset'}."
                )


@frappe.whitelist()
def make_stock_entry(plot, valuation_rate=None, target_warehouse=None):
    """Create a Material Receipt for one serialized plot unit.
    Returns the Stock Entry name."""
    plot_doc = frappe.get_doc("Plot", plot)
    if not plot_doc.custom_item:
        frappe.throw("Plot has no Stock Item linked (custom_item)")

    warehouse = target_warehouse or plot_doc.custom_warehouse
    if not warehouse:
        frappe.throw("Target Warehouse is required (custom_warehouse on Plot)")

    if not plot_doc.company:
        frappe.throw("Plot.company is required")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company = plot_doc.company

    item_row = se.append(
        "items",
        {
            "item_code": plot_doc.custom_item,
            "qty": 1,
            "t_warehouse": warehouse,
            "basic_rate": flt(valuation_rate) or flt(plot_doc.purchase_cost) or 0,
        },
    )

    se.flags.ignore_permissions = True
    se.insert()
    se.submit()

    return se.name
