import frappe

from frappe.integrations.oauth2_logins import login_via_oauth2


@frappe.whitelist()
def update_clearance_date(journal_name):
    journal = frappe.get_doc('Journal Entry', journal_name)
    journal.db_set("clearance_date", journal.posting_date)

@frappe.whitelist(allow_guest=True)
def login_via_custom_oauth(code=None, state=None):
    try:
        # Attempt to log in via the custom OAuth provider
        login_via_oauth2("CustomOAuth", code, state)
    except frappe.exceptions.ValidationError as e:
        # Bypass email verification check
        if "Email not verified" in str(e):
            user_info = frappe._dict(frappe.session["user_info"])
            user = frappe.db.get_value("User", {"email": user_info.get("email")})
            if not user:
                # Create user with unverified email
                frappe.get_doc({
                    "doctype": "User",
                    "email": user_info.get("email"),
                    "first_name": user_info.get("first_name"),
                    "enabled": 1,
                    "user_type": "Website User"
                }).insert(ignore_permissions=True)
            frappe.local.login_manager.user = user_info.get("email")
            frappe.local.login_manager.post_login()
        else:
            raise e
