import frappe
import base64
import json
import requests
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# Load the environment variables
@frappe.whitelist()
def get_access_token():
    consumer_key =   os.environ.get("MPESA_BUSINESS_CONSUMER_KEY")
    consumer_secret =  os.environ.get("MPESA_BUSINESS_CONSUMER_SECRET")

    response = requests.get(
        "https://api.safaricom.co.ke/oauth/v1/generate",
        auth=(consumer_key, consumer_secret),
        params={"grant_type": "client_credentials"},
    )

    return response.json()['access_token']
