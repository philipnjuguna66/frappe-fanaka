import frappe
import json
from frappe.integrations.oauth2_logins import login_via_oauth2, decoder_compat

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
    login_via_oauth2('fanaka_', code=code, state=state, decoder=decoder_compat)
