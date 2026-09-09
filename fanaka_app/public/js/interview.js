// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// Interview form actions for the pipeline automation in Phase 8:
// - "Send Interview Invite": reachable from any round's Interview form (Phase 6 only
//   wired this send from the Shortlisted Candidates page, for the first round).
// - "Schedule Next Round": on a Cleared interview whose Job Opening has a configured
//   round sequence, creates + schedules + invites for the next round in one step
//   (same pattern as the Shortlisted Candidates page's Approve & Schedule dialog) --
//   Interview's own set_only_once schedule fields mean this can't be a blank
//   auto-created draft HR fills in later, so it's a click-through dialog instead.
// See specs/recruitment_ai_screening.md (Phase 8).

const RECRUITMENT_ROLES = ["System Manager", "HR Manager", "HR User"];

frappe.ui.form.on("Interview", {
	refresh(frm) {
		if (frm.doc.__islocal) return;
		if (!frappe.user_roles.some((role) => RECRUITMENT_ROLES.includes(role))) return;

		frm.trigger("add_send_invite_button");
		frm.trigger("add_schedule_next_round_button");
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

	add_schedule_next_round_button(frm) {
		if (frm.doc.status !== "Cleared" || frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Schedule Next Round"), () => {
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
			dialog.show();
		});
	},
});
