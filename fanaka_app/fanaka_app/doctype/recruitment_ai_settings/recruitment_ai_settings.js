// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Recruitment AI Settings", {
	onload(frm) {
		frm.trigger("set_provider_options");
	},

	refresh(frm) {
		frm.trigger("set_model_options");
	},

	openrouter_provider(frm) {
		frm.set_value("openrouter_model", "");
		frm.trigger("set_model_options");
	},

	set_provider_options(frm) {
		frappe.call({
			method: "fanaka_app.api.openrouter.get_providers",
			callback(r) {
				frm.set_df_property("openrouter_provider", "options", r.message || []);
				frm.refresh_field("openrouter_provider");
				frm.trigger("set_model_options");
			},
		});
	},

	set_model_options(frm) {
		if (!frm.doc.openrouter_provider) {
			frm.set_df_property("openrouter_model", "options", []);
			frm.refresh_field("openrouter_model");
			return;
		}
		frappe.call({
			method: "fanaka_app.api.openrouter.get_models",
			args: { provider: frm.doc.openrouter_provider },
			callback(r) {
				const options = (r.message || []).map((m) => m.value);
				frm.set_df_property("openrouter_model", "options", options);
				frm.refresh_field("openrouter_model");
			},
		});
	},

	send_test_email_button(frm) {
		if (!frm.doc.test_email_template) {
			frappe.msgprint(__("Select a Template to Test first."));
			return;
		}
		if (!frm.doc.test_email_applicant) {
			frappe.msgprint(__("Select a Job Applicant to render the placeholders against first."));
			return;
		}
		frappe.call({
			method: "fanaka_app.api.recruitment_emails.send_test_email",
			args: {
				template: frm.doc.test_email_template,
				job_applicant: frm.doc.test_email_applicant,
				recipient: frm.doc.test_email_recipient,
			},
			freeze: true,
			freeze_message: __("Sending test email..."),
			callback(r) {
				if (r.message) {
					frappe.show_alert({
						message: __("Test email sent to {0}", [r.message]),
						indicator: "green",
					});
				}
			},
		});
	},
});
