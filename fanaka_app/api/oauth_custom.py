import frappe
from frappe.integrations.oauth2_logins import login_via_oauth2

@frappe.whitelist(allow_guest=True)
def login_via_custom_oauth(code=None, state=None):
    # Here, "CustomOAuth" should match the provider name in Social Login Key
    login_via_oauth2("CustomOAuth", code, state)
