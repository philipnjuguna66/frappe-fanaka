# your_custom_app/overrides/insights.py

import frappe
import re
from insights.www.insights import (
        continue_to_v3, get_user_default, redirect_to_v2
)
import ibis.backends.mysql.connection as ibis_mysql_connection
import frappe.database.database
import frappe.utils.commands

def get_context(context):
    if not frappe.db.get_single_value("System Settings", "setup_complete"):
        frappe.local.flags.redirect_location = "/app/setup-wizard"
        raise frappe.Redirect

    is_v2_site = frappe.db.count("Insights Query", cache=True) > 0
    if not is_v2_site:
        continue_to_v3(context)
        return

    v2_routes_pattern = [
        r"\/insights\/query\/?",
        r"\/insights\/query\/build\/?",
        r"\/insights\/dashboard[^s]\/?",
        r"\/insights\/public\/dashboard\/?",
        r"\/insights\/public\/chart\/?",
    ]
    if any(re.match(route, frappe.request.path) for route in v2_routes_pattern):
        redirect_to_v2()
        return

    v3_routes = [
        "/insights/dashboards",
        "/insights/workbook", 
        "/insights/shared/chart",
        "/insights/shared/dashboard",
    ]
    if any(route in frappe.request.path for route in v3_routes):
        continue_to_v3(context)
        return

    # go to v2 if user has not visited v3 yet
    has_visited_v3 = (
        get_user_default("insights_has_visited_v3", frappe.session.user) == "1"
    )
    if not has_visited_v3:
        redirect_to_v2()
        return

    is_v3_default = (
        get_user_default("insights_default_version", frappe.session.user) == "v3"
    )
    is_v2_default = (
        get_user_default("insights_default_version", frappe.session.user) == "v2"
    )

    if is_v3_default:
        continue_to_v3(context)
    elif is_v2_default:
        redirect_to_v2()
    else:
        continue_to_v3(context)

original_raw_sql = ibis_mysql_connection.MySQLConnection.raw_sql

def custom_raw_sql(self, query, *args, **kwargs):
    if "SET MAX_STATEMENT_TIME" in query:
        frappe.msgprint("Skipping SET MAX_STATEMENT_TIME due to compatibility issue.", indicator='orange')
        return None # Or return a dummy result if expected
    return original_raw_sql(self, query, *args, **kwargs)

# Apply the patch when the app starts
def apply_ibis_patch():
    ibis_mysql_connection.MySQLConnection.raw_sql = custom_raw_sql
    # You might also need to patch frappe.db.sql, frappe.db.multisql, etc. if Insights uses those directly.
    # This part gets tricky because Frappe's DB layer is complex.

# Register this function to run on startup, e.g., in hooks.py
# app_startup = ["your_custom_app.your_module.apply_ibis_patch"]