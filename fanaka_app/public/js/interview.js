// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// Interview form actions for the pipeline automation in Phase 8:
// - "Send Interview Invite": reachable from any round's Interview form (Phase 6 only
//   wired this send from the Shortlisted Candidates page, for the first round).
// - On a Cleared, submitted interview, one of three mutually exclusive actions,
//   decided server-side by get_pipeline_status (never guessed client-side):
//     - "View Job Offer" if one already exists (auto-drafted, or from a previous
//       "Proceed to Job Offer" click).
//     - "Schedule Next Round" if the Job Opening has a configured round sequence and
//       this wasn't the last round -- creates + schedules + invites for the next
//       round in one step (same pattern as the Shortlisted Candidates page's Approve
//       & Schedule dialog). Interview's own set_only_once schedule fields mean this
//       can't be a blank auto-created draft HR fills in later, so it's a
//       click-through dialog instead.
//     - "Proceed to Job Offer" otherwise -- no next round configured at all (most
//       openings, since round sequences are opt-in) or the last configured round's
//       automatic draft failed silently. Drafts the same bare Job Offer manually.
// See specs/recruitment_ai_screening.md (Phase 8).

const RECRUITMENT_ROLES = ["System Manager", "HR Manager", "HR User"];

frappe.ui.form.on("Interview", {
	refresh(frm) {
		if (frm.doc.__islocal) return;
		if (!frappe.user_roles.some((role) => RECRUITMENT_ROLES.includes(role))) return;

		frm.trigger("add_send_invite_button");
		frm.trigger("add_pipeline_action_button");
	},

	add_send_invite_button(frm) {
		frm.add_custom_button(__("Send Interview Invite"), () => {
			frappe.confirm(
				__("Email the interview invite to {0}?", [frm.doc.job_applicant]),
				() => {
					frappe.call({
						method: "fanaka_app.events.interview.interview.send_invite",
						args: { interview_name: frm.doc.name },
						freeze: true,
						callback: () => {
							frappe.show_alert({ message: __("Invite queued."), indicator: "green" });
						},
					});
				},
			);
		});
	},

	add_pipeline_action_button(frm) {
		if (frm.doc.status !== "Cleared" || frm.doc.docstatus !== 1) return;

		frappe.call({
			method: "fanaka_app.events.interview.interview.get_pipeline_status",
			args: { interview_name: frm.doc.name },
			callback: (r) => {
				const pipeline = r.message || {};

				if (pipeline.job_offer) {
					frm.add_custom_button(__("View Job Offer"), () =>
						frappe.set_route("Form", "Job Offer", pipeline.job_offer),
					);
				} else if (pipeline.next_round) {
					frm.add_custom_button(__("Schedule Next Round"), () =>
						frm.trigger("open_schedule_next_round_dialog"),
					);
				} else {
					frm.add_custom_button(__("Proceed to Job Offer"), () =>
						frm.trigger("open_proceed_to_offer_dialog"),
					);
				}
			},
		});
	},

	open_schedule_next_round_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Schedule Next Round"),
			fields: [
				{ label: __("Date"), fieldname: "scheduled_on", fieldtype: "Date", reqd: 1 },
				{ label: __("From Time"), fieldname: "from_time", fieldtype: "Time", reqd: 1 },
				{ label: __("To Time"), fieldname: "to_time", fieldtype: "Time", reqd: 1 },
			],
			primary_action_label: __("Schedule & Send Invite"),
			primary_action: (values) => {
				frappe.call({
					method: "fanaka_app.events.interview.interview.schedule_next_round",
					args: { interview_name: frm.doc.name, ...values },
					freeze: true,
					callback: (r) => {
						dialog.hide();
						frappe.show_alert({
							message: __("Next round scheduled, invite queued."),
							indicator: "green",
						});
						if (r.message && r.message.interview) {
							frappe.set_route("Form", "Interview", r.message.interview);
						}
					},
				});
			},
		});
		dialog.$wrapper.addClass("fanaka-slideover");
		dialog.show();
	},

	open_proceed_to_offer_dialog(frm) {
		frappe.confirm(
			__(
				"No further interview round is configured for this Job Opening. Draft a Job Offer for {0}?",
				[frm.doc.job_applicant],
			),
			() => {
				frappe.call({
					method: "fanaka_app.events.interview.interview.proceed_to_offer",
					args: { interview_name: frm.doc.name },
					freeze: true,
					callback: (r) => {
						frappe.show_alert({ message: __("Job Offer drafted."), indicator: "green" });
						if (r.message && r.message.offer) {
							frappe.set_route("Form", "Job Offer", r.message.offer);
						}
					},
				});
			},
		);
	},
});
