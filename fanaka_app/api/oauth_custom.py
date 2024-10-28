import frappe
import json
from frappe.integrations.oauth2_logins import login_via_oauth2

def custom_decoder(response):
    """Custom decoder to handle Fanaka_ provider's OAuth token response."""
    # Log the raw response for debugging
    print(f"Raw response content: {response.content}")  # Log the raw response

    # Attempt to parse the JSON content
    try:
        data = json.loads(response.content.decode('utf-8'))  # Ensure proper decoding
    except json.JSONDecodeError:
        raise ValueError("Response content is not valid JSON")

    # Extract tokens and set defaults where necessary
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    token_type = data.get("token_type", "Bearer")
    expires_in = data.get("expires_in")

    # Raise an error if the access token is missing
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
    """Handle login via the Fanaka OAuth provider."""
    provider = "fanaka_"  # Your provider name in Frappe's OAuth settings

    # Use custom decoder to interpret the OAuth response
    user_info = login_via_oauth2(provider, code, state, decoder=custom_decoder)

    # Ensure the email is verified (set default if not provided)
    if not user_info.get("email_verified"):
        user_info["email_verified"] = True

    # Retrieve the user's email
    email = user_info.get("email")
    if not email:
        raise ValueError("Email not found in user information.")


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

    # Set up the session for the user
    frappe.local.login_manager.user = email
    frappe.local.login_manager.post_login()
