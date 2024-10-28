import frappe
from frappe.integrations.oauth2_logins import login_via_oauth2
from frappe.utils.oauth import login_via_oauth2 as original_login_via_oauth2

def custom_get_info_via_oauth(provider, code, decoder=None):
    # Call the original function to fetch user info
    user_info = original_login_via_oauth2(provider, code, decoder)

    # Check for the provider and modify verification requirements for Fanaka_
    if provider == "Fanaka_" and not user_info.get("email_verified"):
        # Assume email is verified for this specific provider
        user_info["email_verified"] = True

    return user_info

# Override the function in your login function
@frappe.whitelist(allow_guest=True)
def login_via_fanaka_oauth(code=None, state=None):
    # Use the custom get_info_via_oauth to fetch user info
    info = custom_get_info_via_oauth("Fanaka_", code)
    email = info.get("email")

    # Proceed with login
    frappe.local.login_manager.user = email
    frappe.local.login_manager.post_login()
