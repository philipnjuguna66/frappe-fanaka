# Copyright (c) 2025, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Plot(Document):
    def validate(self):
        """Validate plot data before saving"""
        if not self.name:
            frappe.throw("Plot name/ID is required")

    def before_insert(self):
        """Create Item Master before plot is saved"""
        self.create_item_master()

    def after_insert(self):
        """Create Serial Number and register stock after plot is saved"""
        self.create_serial_number()
        self.register_initial_stock()

    def on_update(self):
        """Handle updates to plot"""
        if self.has_value_changed("item_code"):
            # Item code shouldn't change, but handle if it does
            pass

    def create_item_master(self):
        """Create Item Master for this plot (called before insert)"""
        try:
            # Check if item already exists
            item_code = f"PLT-{self.name}"
            if frappe.db.exists("Item", item_code):
                self.item_code = item_code
                return

            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = f"Plot {self.name}"
            item.description = f"Land plot - {self.name}"
            item.item_group = self.get_or_create_item_group()
            item.stock_uom = "Nos"
            item.has_serial_no = 1  # Enable serial number tracking
            item.serial_no_series = "SN-"  # Serial number format
            item.is_stock_item = 1
            item.disabled = 0
            item.insert(ignore_permissions=True)

            self.item_code = item.name
            frappe.msgprint(f"Item Master created: {item_code}", alert=True)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error creating Item Master")
            frappe.throw(f"Failed to create Item Master: {str(e)}")

    def create_serial_number(self):
        """Create Serial Number for tracking this plot"""
        try:
            if not self.item_code:
                frappe.throw("Item Code is required to create Serial Number")

            # Check if serial already exists
            if frappe.db.exists("Serial No", self.name):
                return self.name

            serial = frappe.new_doc("Serial No")
            serial.item_code = self.item_code
            serial.serial_no = self.name
            serial.insert(ignore_permissions=True)

            self.serial_number = serial.name
            frappe.msgprint(f"Serial Number created: {self.name}", alert=True)
            return serial.name

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error creating Serial Number")
            frappe.throw(f"Failed to create Serial Number: {str(e)}")

    def register_initial_stock(self):
        """Register plot as initial stock (receipt/purchase)"""
        try:
            if not self.item_code or not self.name:
                return

            warehouse = self.get_warehouse()

            # Create Stock Entry for initial receipt
            se = frappe.new_doc("Stock Entry")
            se.doctype = "Stock Entry"
            se.stock_entry_type = "Material Receipt"
            se.purpose = "Material Receipt"
            se.from_warehouse = None
            se.to_warehouse = warehouse
            se.posting_date = frappe.utils.today()
            se.posting_time = frappe.utils.now().split(" ")[1]
            se.remarks = f"Initial stock registration for Plot {self.name}"

            se.append("items", {
                "item_code": self.item_code,
                "qty": 1,
                "serial_no": self.name,
                "uom": "Nos",
                "conversion_factor": 1,
                "warehouse": warehouse,
                "batch_no": None
            })

            se.insert(ignore_permissions=True)
            se.submit()

            frappe.msgprint(f"Stock Entry created: {se.name}", alert=True)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error registering initial stock")
            # Don't throw here - plot should still be created even if stock entry fails
            frappe.msgprint(f"Warning: Could not register stock: {str(e)}", indicator="orange")

    def mark_as_sold(self, customer=None, sale_price=None):
        """Mark this plot as sold by creating Material Issue"""
        try:
            if not self.item_code:
                frappe.throw("Item Code is required")

            warehouse = self.get_warehouse()

            # Create Stock Entry for sale
            se = frappe.new_doc("Stock Entry")
            se.doctype = "Stock Entry"
            se.stock_entry_type = "Material Issue"
            se.purpose = "Material Issue"
            se.from_warehouse = warehouse
            se.to_warehouse = None
            se.posting_date = frappe.utils.today()
            se.posting_time = frappe.utils.now().split(" ")[1]
            se.remarks = f"Plot sold to {customer or 'Customer'}" if customer else f"Plot {self.name} sold"

            se.append("items", {
                "item_code": self.item_code,
                "qty": 1,
                "serial_no": self.name,
                "uom": "Nos",
                "conversion_factor": 1,
                "warehouse": warehouse
            })

            se.insert(ignore_permissions=True)
            se.submit()

            # Update serial status
            frappe.db.set_value("Serial No", self.name, "status", "Sold")

            self.db_set("status", "sold")
            self.db_set("sold_date", frappe.utils.today())

            frappe.msgprint(f"Plot marked as sold. Stock Entry: {se.name}", alert=True)
            return se.name

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error marking as sold")
            frappe.throw(f"Failed to mark plot as sold: {str(e)}")

    def get_warehouse(self):
        """Get warehouse for this plot (from project or default)"""
        try:
            # Try to get warehouse from project
            if self.project:
                project_warehouse = frappe.db.get_value(
                    "Project",
                    self.project,
                    "warehouse"
                )
                if project_warehouse:
                    return project_warehouse

            # Default to 'Main Warehouse'
            if not frappe.db.exists("Warehouse", "Stores - FRE"):
                # Create default warehouse if it doesn't exist
                wh = frappe.new_doc("Warehouse")
                wh.warehouse_name = "Stores - FRE"
                wh.parent_warehouse = None
                wh.insert(ignore_permissions=True)

            return "Stores - FRE"

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error getting warehouse")
            return "Stores - FRE"

    def get_or_create_item_group(self):
        """Get or create 'Plots' item group"""
        try:
            item_group = "Plot"

            if frappe.db.exists("Item Group", item_group):
                return item_group

            # Create parent group first
            if not frappe.db.exists("Item Group", "Plot"):
                parent = frappe.new_doc("Item Group")
                parent.item_group_name = "Plot"
                parent.parent_item_group = "All Item Groups"
                parent.insert(ignore_permissions=True)

            # Create child group
            child = frappe.new_doc("Item Group")
            child.item_group_name = "Plots"
            child.parent_item_group = "Land"
            child.insert(ignore_permissions=True)

            return item_group

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error creating item group")
            # Return default if creation fails
            return "Products"

    @staticmethod
    def get_stock_status(plot_name):
        """Get current stock status of a plot"""
        try:
            serial = frappe.db.get_value(
                "Serial No",
                plot_name,
                ["status", "item_code"],
                as_dict=True
            )

            if not serial:
                return {"status": "Not Found", "qty": 0}

            sle = frappe.db.get_value(
                "Stock Ledger Entry",
                filters={"serial_no": plot_name, "item_code": serial.item_code},
                fieldname=["actual_qty", "warehouse"],
                order_by="posting_date desc, posting_time desc",
                as_dict=True
            )

            return {
                "status": serial.status,
                "warehouse": sle.warehouse if sle else None,
                "item_code": serial.item_code,
                "qty": sle.actual_qty if sle else 0
            }

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error getting stock status")
            return {"status": "Error", "error": str(e)}

    @staticmethod
    def get_plot_movements(plot_name):
        """Get all stock movements for a plot (viewing history)"""
        try:
            movements = frappe.db.get_list(
                "Stock Ledger Entry",
                filters={"serial_no": plot_name},
                fields=[
                    "item_code",
                    "warehouse",
                    "qty",
                    "posting_date",
                    "posting_time",
                    "voucher_type",
                    "voucher_no",
                    "actual_qty"
                ],
                order_by="posting_date asc"
            )

            return movements

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Plot: Error getting movements")
            return []