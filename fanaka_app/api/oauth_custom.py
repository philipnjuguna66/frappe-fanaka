import frappe
from frappe.integrations.oauth2_logins import login_via_oauth2, decoder_compat

@frappe.whitelist(allow_guest=True)
def login_via_custom_oauth(code=None, state=None):
    try:
        # Attempt to log in via Fanaka_ OAuth provider
        login_via_oauth2("fanaka_", code, state ,decoder=decoder_compat)
    except frappe.exceptions.ValidationError as e:
        # Check if the error is due to unverified email
        if "Email not verified" in str(e):
            # Retrieve user info from session and manually create/login user
            user_info = frappe._dict(frappe.session["user_info"])
            email = user_info.get("email")
            if not frappe.db.exists("User", email):
                # Create user without verifying email
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
            # Raise other validation errors
            raise e
