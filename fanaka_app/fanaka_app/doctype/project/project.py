import frappe
from frappe.utils import flt


@frappe.whitelist()
def subdivide_plots(project, no_of_plots, plot_size, price_per_plot):
    pass
