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





