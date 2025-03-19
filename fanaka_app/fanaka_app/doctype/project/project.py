import frappe
from frappe.utils import flt

@frappe.whitelist()
def subdivide_plots(project, no_of_plots, plot_size, price_per_plot):
    # Loop to create individual plot records
    for i in range(1, int(no_of_plots) + 1):
        plot = frappe.get_doc({
            "doctype": "Plot",
            "plot_no":  {i},
            "size": flt(plot_size),
            "project": project,  # Link to the parent Project
            "parent": project,  # Link to the parent Project
            "parenttype": "Project",   # Link to the parent Project
            "parentfield": "custom_project_plots",   # Link to the parent Project
            "status": "Available",  # Default status
            "price": flt(price_per_plot),  # Price per plot

        })
        plot.insert()  # Save the plot record

        # Create Stock Entry for the plot
        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",  # Receiving plots into stock
            "project": project,  # Link to the parent Project
            "items": [
                {
                    "item_code": plot.name,  # Replace with your plot item
                    "qty": 1,  # Each plot is 1 unit
                    "t_warehouse": "Stores - FRE",  # Warehouse for the project
                    "basic_rate": flt(price_per_plot),  # Cost of the plot
                    "cost_center": "Main - Your Company"  # Replace with your cost center
                }
            ]
        })
        stock_entry.insert()  # Save the stock entry
        stock_entry.submit()

    return f"{no_of_plots} plots created successfully!"