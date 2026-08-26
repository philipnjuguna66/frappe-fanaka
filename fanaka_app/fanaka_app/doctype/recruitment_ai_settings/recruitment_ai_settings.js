// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

// "Provider" options are static (the adapter registry, see api/llm_providers) so no
// server round-trip is needed to populate that dropdown -- it's just declared directly
// in the doctype JSON. Only the Model list needs fetching, and needs the API key to do
// it for every provider except OpenRouter (whose model list is public).
const PROVIDERS_NEEDING_KEY_TO_LIST_MODELS = ["Anthropic", "OpenAI", "Google"];

frappe.ui.form.on("Recruitment AI Settings", {
	onload(frm) {
		// Every Password-fieldtype control fires frappe.core.doctype.user.user.
		// test_password_strength() on keyup by default (see
		// frappe/public/js/frappe/form/controls/password.js) -- that endpoint's
		// crack-time estimate can overflow orjson's 64-bit int handling for a long,
		// high-entropy value like a real API key, crashing the request. This field
		// holds a machine-generated key, not a human-chosen password, so a strength
		// meter makes no sense here anyway -- disable_password_checks() is the
		// control's own public toggle for exactly this.
		frm.get_field("llm_api_key").disable_password_checks();
	},

	refresh(frm) {
		// OpenRouter needs no key, so it's safe/useful to refresh its list on load.
		// Other providers only refresh when the user actively edits provider/key below,
		// since a saved key shows as a masked placeholder on reload, not the real value.
		if (frm.doc.llm_provider === "OpenRouter") {
			frm.trigger("set_model_options");
		}
	},

	llm_provider(frm) {
		frm.set_value("llm_model", "");
		frm.trigger("set_model_options");
	},

	llm_api_key(frm) {
		frm.trigger("set_model_options");
	},

	set_model_options(frm) {
		const provider = frm.doc.llm_provider;
		if (!provider) {
			frm.set_df_property("llm_model", "options", []);
			frm.refresh_field("llm_model");
			return;
		}
		if (PROVIDERS_NEEDING_KEY_TO_LIST_MODELS.includes(provider) && !frm.doc.llm_api_key) {
			frm.set_df_property("llm_model", "options", []);
			frm.refresh_field("llm_model");
			return;
		}

		frappe.call({
			method: "fanaka_app.api.llm_settings.get_models",
			args: { provider, api_key: frm.doc.llm_api_key || "" },
			callback(r) {
				const options = (r.message || []).map((m) => m.value);
				frm.set_df_property("llm_model", "options", options);
				frm.refresh_field("llm_model");
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
