// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// AI recruitment screening: score card render + HR approve/reject actions for the
// "Shortlisted by AI" status. Registered alongside hrms's own job_applicant.js (Frappe
// concatenates doctype_js from every app, it does not replace it).
// See specs/recruitment_ai_screening.md (Phase 3).

const AI_REVIEW_ROLES = ["System Manager", "HR Manager", "HR User"];
const AI_SCORE_CATEGORIES = ["Skills", "Experience", "Education"];

frappe.ui.form.on("Job Applicant", {
	refresh(frm) {
		frm.trigger("render_ai_score_card");
		frm.trigger("add_ai_review_buttons");
	},

	render_ai_score_card(frm) {
		const field = frm.get_field("custom_ai_score_card_html");
		if (!field) return;

		const rows = frm.doc.custom_ai_score_breakdown || [];
		if (frm.doc.custom_ai_score == null && !rows.length) {
			field.$wrapper.empty();
			return;
		}

		const score = frm.doc.custom_ai_score != null ? frm.doc.custom_ai_score : "?";
		const summary = frappe.utils.escape_html(frm.doc.custom_ai_analysis_summary || "");
		const analyzed_on = frm.doc.custom_ai_analyzed_on
			? frappe.datetime.str_to_user(frm.doc.custom_ai_analyzed_on)
			: "";

		const by_category = {};
		rows.forEach((row) => {
			(by_category[row.category] = by_category[row.category] || []).push(row);
		});

		const category_html = AI_SCORE_CATEGORIES.filter(
			(cat) => by_category[cat] && by_category[cat].length,
		)
			.map((cat) => {
				const items = by_category[cat]
					.map((row) => {
						const points = row.points > 0 ? `+${row.points}` : row.points;
						const cls = row.points < 0 ? "text-danger" : "text-success";
						const remark = row.remark
							? ` &mdash; <span class="text-muted">${frappe.utils.escape_html(row.remark)}</span>`
							: "";
						return `<li><span class="${cls}">${points}</span> ${frappe.utils.escape_html(
							row.criteria,
						)}${remark}</li>`;
					})
					.join("");
				return `<div><strong>${__(cat)}</strong><ul style="margin:4px 0 10px 18px;">${items}</ul></div>`;
			})
			.join("");

		field.$wrapper.html(`
			<div class="ai-score-card" style="border:1px solid var(--border-color); border-radius:8px; padding:12px 16px; margin-bottom:8px;">
				<div style="font-size:20px; font-weight:600;">${score}%</div>
				${analyzed_on ? `<div class="text-muted" style="font-size:11px; margin-bottom:8px;">${__("Analyzed on")} ${analyzed_on}</div>` : ""}
				${summary ? `<div style="margin-bottom:10px;">${summary}</div>` : ""}
				${category_html}
			</div>
		`);
	},

	add_ai_review_buttons(frm) {
		if (frm.doc.__islocal || frm.doc.status !== "Shortlisted by AI") return;
		if (!frappe.user_roles.some((role) => AI_REVIEW_ROLES.includes(role))) return;

		frm.add_custom_button(
			__("Approve"),
			() => {
				frappe.confirm(__("Move {0} to Shortlisted?", [frm.doc.applicant_name]), () => {
					frappe.call({
						method: "fanaka_app.events.job_applicant.job_applicant.approve_ai_shortlist",
						args: { name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				});
			},
			__("AI Screening"),
		);

		frm.add_custom_button(
			__("Reject"),
			() => {
				frappe.confirm(__("Reject {0}?", [frm.doc.applicant_name]), () => {
					frappe.call({
						method: "fanaka_app.events.job_applicant.job_applicant.reject_ai_shortlist",
						args: { name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				});
			},
			__("AI Screening"),
		);
	},
});
