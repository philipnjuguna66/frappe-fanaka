// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// Job Offer form action: "Send Offer Letter" -- emails the offer to the candidate
// with the offer letter PDF attached (frappe.attach_print via
// fanaka_app.events.job_offer.job_offer.send_offer_letter). Nothing sends the offer
// to the candidate on its own when the draft is created or submitted -- this is that
// explicit step, the counterpart to Phase 6's "Send Interview Invite" on Interview.
// Registered alongside hrms's own job_offer.js (Frappe concatenates doctype_js from
// every app, it does not replace it).
// See specs/recruitment_ai_screening.md (Phase 8).

const RECRUITMENT_ROLES = ["System Manager", "HR Manager", "HR User"];

frappe.ui.form.on("Job Offer", {
	refresh(frm) {
		if (frm.doc.__islocal || frm.doc.docstatus !== 1) return;
		if (!frappe.user_roles.some((role) => RECRUITMENT_ROLES.includes(role))) return;

		const label = frm.doc.custom_offer_letter_sent ? __("Resend Offer Letter") : __("Send Offer Letter");
		const confirm_message = frm.doc.custom_offer_letter_sent
			? __("Offer letter was already sent on {0}. Send again?", [
					frappe.datetime.str_to_user(frm.doc.custom_offer_letter_sent_on),
				])
			: __("Email the offer letter to {0}, with the offer PDF attached?", [frm.doc.job_applicant]);

		frm.add_custom_button(label, () => {
			frappe.confirm(confirm_message, () => {
				frappe.call({
					method: "fanaka_app.events.job_offer.job_offer.send_offer_letter",
					args: { job_offer: frm.doc.name },
					freeze: true,
					callback: () => {
						frappe.show_alert({ message: __("Offer letter queued."), indicator: "green" });
						frm.reload_doc();
					},
				});
			});
		});
	},
});
