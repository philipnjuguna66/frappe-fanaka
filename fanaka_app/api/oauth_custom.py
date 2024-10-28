import frappe
import json
from frappe import _
from frappe.utils.oauth import get_info_via_oauth
from frappe.utils.oauth import login_oauth_user

@frappe.whitelist(allow_guest=True)
def login_via_fanaka_oauth(code=None, state=None):
    frappe.throw(_("Please login via Fanaka OAuth"))

    """
    Custom OAuth login function for Fanaka_ to bypass email verification.
    """
    provider = "fanaka_"

    # Get user information without enforcing email verification
    user_info = get_info_via_oauth(provider, code)

    # Manually set email as verified if not provided
    if not user_info.get("email_verified"):
        user_info["email_verified"] = True

    email = user_info.get("email")

    # Check if user exists, or create if not
    user = frappe.db.get_value("User", {"email": email})
    if not user:
        user_doc = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": user_info.get("first_name"),
            "enabled": 1,
            "user_type": "Website User"
        })
        user_doc.insert(ignore_permissions=True)

    # Log in user
    frappe.local.login_manager.user = email
    frappe.local.login_manager.post_login()

