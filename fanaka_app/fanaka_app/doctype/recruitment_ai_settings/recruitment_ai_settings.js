// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

// "Provider" options are static (the adapter registry, see api/llm_providers) so no
// server round-trip is needed to populate that dropdown -- it's just declared directly
// in the doctype JSON. Only the Model list needs fetching, and needs the API key to do
// it for every provider except OpenRouter (whose model list is public).
const PROVIDERS_NEEDING_KEY_TO_LIST_MODELS = ["Anthropic", "OpenAI", "Google"];

// After a save+reload, a Password field shows only a string of "*" placeholders in
// frm.doc, never the real value -- sending that straight to the server as if it were
// the real key breaks both the Model picker and Test Connection for any already-saved
// non-OpenRouter provider. Both call sites below need "the real key, or nothing" --
// this is the one place that decides which.
function real_key_or_blank(frm) {
	const value = frm.doc.llm_api_key || "";
	return /^\*+$/.test(value) ? "" : value;
}

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
		// get_models() now falls back server-side to the saved key when none is passed,
		// so this is safe to run unconditionally on every provider, not just OpenRouter.
		if (frm.doc.llm_provider) {
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
		const api_key = real_key_or_blank(frm);
		if (PROVIDERS_NEEDING_KEY_TO_LIST_MODELS.includes(provider) && !api_key && frm.doc.__islocal) {
			// New, unsaved doc with no key typed yet -- nothing to fetch with. On a
			// saved doc a blank api_key here is fine: get_models() falls back to the
			// key already on file.
			frm.set_df_property("llm_model", "options", []);
			frm.refresh_field("llm_model");
			return;
		}

		frappe.call({
			method: "fanaka_app.api.llm_settings.get_models",
			args: { provider, api_key },
			callback(r) {
				const options = (r.message || []).map((m) => m.value);
				frm.set_df_property("llm_model", "options", options);
				frm.refresh_field("llm_model");
			},
		});
	},

	test_connection_button(frm) {
		if (!frm.doc.llm_provider) {
			frappe.msgprint(__("Select a Provider first."));
			return;
		}
		if (!frm.doc.llm_model) {
			frappe.msgprint(__("Select a Model first."));
			return;
		}
		if (!frm.doc.llm_api_key) {
			frappe.msgprint(__("Enter an API Key first."));
			return;
		}
		frappe.call({
			method: "fanaka_app.api.llm_settings.test_connection",
			args: {
				provider: frm.doc.llm_provider,
				model: frm.doc.llm_model,
				api_key: real_key_or_blank(frm),
			},
			freeze: true,
			freeze_message: __("Testing connection..."),
			callback(r) {
				if (r.message && r.message.ok) {
					frappe.show_alert({
						message: __("Connection OK -- {0} responded correctly.", [frm.doc.llm_provider]),
						indicator: "green",
					});
				}
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
