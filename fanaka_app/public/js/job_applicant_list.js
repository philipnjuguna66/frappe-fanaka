// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// Manual/bulk "Send Regret Email" action -- works regardless of the Recruitment AI
// Settings auto-send toggle. See specs/recruitment_ai_screening.md (Phase 4).
//
// hrms's own job_applicant_list.js (doctype-owned _list.js) always loads before this
// hook-registered one -- confirmed in frappe/desk/form/meta.py's add_code(), own-module
// code is appended to __list_js before doctype_list_js hooks are. It already assigns
// frappe.listview_settings["Job Applicant"] with add_fields/get_indicator for status
// colour-coding, so this merges onto that object rather than replacing it outright --
// a flat re-assignment here would silently delete hrms's settings.

Object.assign(frappe.listview_settings["Job Applicant"] || (frappe.listview_settings["Job Applicant"] = {}), {
	onload(listview) {
		listview.page.add_action_item(__("Send Regret Email"), () => {
			const selected = listview.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Select at least one applicant first."));
				return;
			}

			const names = selected.map((d) => d.name);
			const dialog = new frappe.ui.Dialog({
				title: __("Send Regret Email"),
				fields: [
					{
						fieldtype: "HTML",
						options: `<p>${__("Queue a regret email for {0} selected applicant(s).", [names.length])}</p>`,
					},
					{
						fieldname: "force",
						fieldtype: "Check",
						label: __("Resend even if a regret email was already sent"),
						default: 0,
					},
				],
				primary_action_label: __("Send"),
				primary_action(values) {
					frappe.call({
						method: "fanaka_app.events.job_applicant.regret_email.bulk_send_regret_emails",
						args: { applicant_names: names, force: values.force },
						freeze: true,
						callback(r) {
							dialog.hide();
							const { queued, skipped } = r.message || {};
							frappe.show_alert({
								message: __("Queued {0} regret email(s), skipped {1}.", [queued, skipped]),
								indicator: queued ? "green" : "orange",
							});
							listview.refresh();
						},
					});
				},
			});
			dialog.show();
		});
	},
});
