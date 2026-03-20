import frappe
import json
from frappe.integrations.oauth2_logins import login_via_oauth2

def custom_decoder(response):

    # Attempt to parse the JSON content
    try:
        data = json.loads(response.decode('utf-8'))  # Ensure proper decoding
    except json.JSONDecodeError:
        raise ValueError("Response content is not valid JSON")

    # Extract tokens and set defaults where necessary
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    token_type = data.get("token_type", "Bearer")
    expires_in = data.get("expires_in")
    email = data.get("email")

    user = frappe.get_doc("User", {"email": email})

    sub = data.get("sub", user.name)  # This ensures 'sub' is always set

    # Raise an error if the access token is missing
    if not access_token:
        raise KeyError("Access token not found in response.")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type,
        "expires_in": expires_in,
        "sub": sub,  # Add 'sub' directly
        "email": data.get("email"),
        "raw_response": data
    }

@frappe.whitelist(allow_guest=True)
def login_via_fanaka_oauth(code=None, state=None):
    """Handle login via the Fanaka OAuth provider."""
    provider = "fanaka_mis"
    login_via_oauth2(provider, code, state, decoder=custom_decoder)



import frappe
from frappe import _

@frappe.whitelist()
def get_user_api_keys(user_id):
    """
    Returns API Key and API Secret for a given user.
    Note: This will regenerate the API Secret every time it is called.
    """
    # 1. Verify the user exists
    if not frappe.db.exists("User", user_id):
        frappe.throw(_("User {0} not found").format(user_id))

    user = frappe.get_doc("User", user_id)

    # 2. Handle API Key
    if not user.api_key:
        user.api_key = frappe.generate_hash(length=15)
    
    # 4. Generate a new API Secret every time this function is called
    api_secret = frappe.generate_hash(length=15)
    user.api_secret = api_secret
    
    user.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "api_key": user.api_key,
        "api_secret": api_secret
    }
