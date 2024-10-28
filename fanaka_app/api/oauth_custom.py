import frappe
import json
from frappe.utils.oauth import login_oauth_user, get_info_via_oauth

def custom_decoder(response):
    """Custom decoder to handle Fanaka_ provider's OAuth token response."""
    data = json.loads(response.content)
    # Map response data to expected keys if necessary
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    token_type = data.get("token_type", "Bearer")
    expires_in = data.get("expires_in")

    if not access_token:
        raise KeyError("Access token not found in response.")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type,
        "expires_in": expires_in
    }
@frappe.whitelist(allow_guest=True)
def login_via_fanaka_oauth(code=None, state=None):
    provider = "fanaka_"
    # Use custom decoder to interpret the OAuth response
    user_info = get_info_via_oauth(provider, code, decoder=custom_decoder)

    if not user_info.get("email_verified"):
        user_info["email_verified"] = True

    email = user_info.get("email")
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

    frappe.local.login_manager.user = email
    frappe.local.login_manager.post_login()
