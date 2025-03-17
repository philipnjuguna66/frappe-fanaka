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

    return f"{no_of_plots} plots created successfully!"