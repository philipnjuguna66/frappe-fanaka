import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as ERPNextStockEntry


class StockEntry(ERPNextStockEntry):
    def generate_and_attach_plot_serials(self):
        """
        Generates serial numbers for 'Plot' items in a 'Repack' Stock Entry
        based on the linked Project name and attaches them.
        """

        # 1. Basic Validations
        if self.purpose != "Repack":
            frappe.throw("This function is only applicable for 'Repack' Stock Entries.")

        if not self.project:
            frappe.throw("Please link a 'Project' to this Stock Entry first.")

        # 2. Find the 'Plot' item in the 'Repacked Items' table
        plot_item_row = None
        for item_row in self.repacked_items:
            # IMPORTANT: Replace "PLOT-001" with the actual Item Code of your 'Plot' item
            if item_row.item_code == "PLOT-001":
                plot_item_row = item_row
                break

        if not plot_item_row:
            frappe.throw("No 'Plot' item found in the 'Repacked Items' table. Please add it first.")

        # Ensure the quantity for Plot is valid
        if not plot_item_row.qty or plot_item_row.qty <= 0:
            frappe.throw("Quantity for 'Plot' item must be greater than 0.")

        # 3. Get Project Name Prefix for Serial Numbers
        try:
            # Fetch the Project document to ensure it exists and get its name (which is the document's primary key)
            project_doc = frappe.get_doc("Project", self.project)
            # Sanitize the project name for use in serial numbers (e.g., replace spaces with hyphens, convert to uppercase)
            project_name_prefix = project_doc.name.replace(" ", "-").upper()
        except frappe.DoesNotExistError:
            frappe.throw(f"Linked Project '{self.project}' does not exist.")
        except Exception as e:
            frappe.throw(f"Error fetching project details: {e}")

        # 4. Generate Serial Numbers
        quantity_to_generate = int(plot_item_row.qty)
        generated_serials = []

        # Get existing serial numbers for the 'Plot' item to prevent creating duplicates in the system
        # This is a safeguard, as the sequential generation below should ideally prevent conflicts
        existing_serials_in_db = frappe.get_list(
            "Serial No",
            filters={"item_code": plot_item_row.item_code},
            pluck="name"
        )
        existing_serial_names_set = set(existing_serials_in_db)

        # Loop to create serial numbers in the format PROJECT-NAME-001, PROJECT-NAME-002, etc.
        for i in range(1, quantity_to_generate + 1):
            serial_candidate = f"{project_name_prefix}-{i:03d}"  # Example: SUNRISE-VALLEY-001

            # Simple check for existing serial numbers, increment index if necessary
            # (highly unlikely for this sequential pattern within a single batch, but good practice)
            original_i = i
            while serial_candidate in existing_serial_names_set:
                i += 1
                serial_candidate = f"{project_name_prefix}-{i:03d}"

            generated_serials.append(serial_candidate)
            existing_serial_names_set.add(serial_candidate)  # Add to our temporary set for this generation batch
            i = original_i  # Reset i for the next iteration of the main loop

        # 5. Attach generated serial numbers to the Plot item row
        # ERPNext expects serial numbers in the 'serial_no' field as a newline-separated string
        plot_item_row.serial_no = "\n".join(generated_serials)

        # 6. Save the Stock Entry document
        # This will update the 'repacked_items' child table with the new serial numbers
        self.save()

        frappe.msgprint(
            f"Successfully generated and attached {len(generated_serials)} serial numbers to the 'Plot' item. "
            "Please review them before submitting the Stock Entry."
        )