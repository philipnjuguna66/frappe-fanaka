# Seed SMS Template DocType with the keys previously stored as Laravel `settings` rows.
# Re-runnable: skips records that already exist.

import frappe

SEED = [
	{
		"name": "birthday_message",
		"category": "Client",
		"helper_text": "Sent to clients on their birthday.",
	},
	{
		"name": "onboarding_sms",
		"category": "Sale",
		"helper_text": "Sent when a new plot is attached to a client profile.",
	},
	{
		"name": "payment_reminder_sms",
		"category": "Payment",
		"helper_text": "Reminder for clients to pay for their plot.",
	},
	{
		"name": "payment_notification_sms",
		"category": "Payment",
		"helper_text": "Sent when a payment is approved by the supervisor.",
	},
	{
		"name": "payment_removed_sms",
		"category": "Payment",
		"helper_text": "Sent when a payment is removed from the client profile.",
	},
	{
		"name": "payment_overdue_sms",
		"category": "Payment",
		"helper_text": "Sent when a payment is overdue.",
	},
	{
		"name": "payment_completed_sms",
		"category": "Payment",
		"helper_text": "Sent when a plot is fully paid; requests completion document.",
	},
	{
		"name": "referral_message",
		"category": "Marketing",
		"helper_text": "Sent to referrers.",
	},
	{
		"name": "penalty_charge_sms",
		"category": "Payment",
		"helper_text": "Sent when a penalty is charged on a sale.",
	},
	{
		"name": "reservation_removal_reminder",
		"category": "Sale",
		"helper_text": "Reminder when a plot is not paid for at release 3 days.",
	},
	{
		"name": "reservation_removed",
		"category": "Sale",
		"helper_text": "Sent when a reservation is released due to lack of funds.",
	},
	{
		"name": "site_visit_booked",
		"category": "Site Visit",
		"helper_text": "Sent on site visit booking.",
	},
	{
		"name": "site_visit_reminder",
		"category": "Site Visit",
		"helper_text": "Reminder before site visit.",
	},
	{
		"name": "site_visit_absentee",
		"category": "Site Visit",
		"helper_text": "Sent when client missed scheduled site visit.",
	},
	{
		"name": "site_visit_thankyou_note",
		"category": "Site Visit",
		"helper_text": "Sent after a completed site visit.",
	},
]


def execute():
	for row in SEED:
		key = row["name"]

		if frappe.db.exists("SMS Template", key):
			continue

		doc = frappe.new_doc("SMS Template")
		doc.template_name = key
		doc.category = row["category"]
		doc.helper_text = row["helper_text"]
		doc.is_active = 1
		doc.is_automated = 1
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
