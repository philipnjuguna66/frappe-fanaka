import frappe
import re
import json  # To format doc data nicely


def generate_plot_serial_numbers(doc, event):


    # Get project
    if not doc.get("project"):
        frappe.throw("Project is not set on the Purchase Invoice.")

    project = frappe.get_doc("Project", doc.project)

    # Generate serial from project name
    serial = re.sub(r'[\W]+', '_', project.project_name.lower()).strip('_')

    # Assign serial number to each item
    for item in doc.items:
        item.serial_no = serial

    # Optional: throw just to inspect
