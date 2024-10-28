import frappe
from frappe.integrations.oauth2_logins import login_via_oauth2

@frappe.whitelist(allow_guest=True)
def login_via_fanaka_oauth(code=None, state=None):
    try:
        # Attempt to log in via Fanaka_ provider
        login_via_oauth2("Fanaka_", code, state)
    except frappe.exceptions.ValidationError as e:
        if "Email not verified" in str(e):
            # Get user info from the session data
            user_info = frappe._dict(frappe.session["user_info"])
            email = user_info.get("email")

            # Check if user exists; if not, create the user
            if not frappe.db.exists("User", email):
                frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": user_info.get("first_name"),
                    "enabled": 1,
                    "user_type": "Website User"
                }).insert(ignore_permissions=True)

            # Log in the user
            frappe.local.login_manager.user = email
            frappe.local.login_manager.post_login()
        else:
            raise e
