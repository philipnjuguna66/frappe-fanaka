// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt
//
// Shortlisted Candidates: HR's main working surface for AI-screened candidates.
// Lists everyone at "Shortlisted by AI" or human-approved "Shortlisted", with filters
// and row/bulk actions to either approve + invite for interview, or reject + send a
// regret email. See specs/recruitment_ai_screening.md (Phase 6).

frappe.pages["shortlisted-candidates"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Shortlisted Candidates"),
		single_column: true,
	});
	new ShortlistedCandidates(page);
};

class ShortlistedCandidates {
	constructor(page) {
		this.page = page;
		this.filters = {};
		this.rows = [];
		this.selected = new Set();

		this.inject_tailwind();
		this.render_shell();
		this.load();
	}

	inject_tailwind() {
		if (!document.getElementById("sc-tailwind-cdn")) {
			const tw = document.createElement("script");
			tw.id = "sc-tailwind-cdn";
			tw.src = "https://cdn.tailwindcss.com";
			tw.onload = () => {
				if (window.tailwind) {
					window.tailwind.config = { corePlugins: { preflight: false } };
				}
			};
			document.head.appendChild(tw);
		}
	}

	render_shell() {
		this.page.main.empty();
		this.$root = $(`
			<div class="sc-root" style="padding: 4px 2px 24px;">
				<div class="sc-filters flex flex-wrap items-end gap-3 mb-4 p-3 border rounded-lg bg-gray-50">
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Job Opening")}</label>
						<input type="text" data-filter="job_opening" class="form-control" style="width:160px" placeholder="${__("Job Opening")}">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Status")}</label>
						<select data-filter="status" class="form-control" style="width:150px">
							<option value="">${__("Shortlisted by AI / Shortlisted")}</option>
							<option value="Shortlisted by AI">${__("Shortlisted by AI")}</option>
							<option value="Shortlisted">${__("Shortlisted")}</option>
						</select>
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Designation")}</label>
						<input type="text" data-filter="designation" class="form-control" style="width:150px" placeholder="${__("Designation")}">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Min Score")}</label>
						<input type="number" data-filter="min_score" class="form-control" style="width:90px" min="0" max="100">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Max Score")}</label>
						<input type="number" data-filter="max_score" class="form-control" style="width:90px" min="0" max="100">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Applied From")}</label>
						<input type="date" data-filter="from_date" class="form-control" style="width:150px">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Applied To")}</label>
						<input type="date" data-filter="to_date" class="form-control" style="width:150px">
					</div>
					<div>
						<label class="block text-xs font-semibold text-gray-500 mb-1">${__("Regret Sent")}</label>
						<select data-filter="email_sent" class="form-control" style="width:120px">
							<option value="">${__("Any")}</option>
							<option value="1">${__("Yes")}</option>
							<option value="0">${__("No")}</option>
						</select>
					</div>
				</div>

				<div class="sc-bulk-bar hidden flex items-center gap-2 mb-3 p-2 border rounded-lg bg-blue-50">
					<span class="sc-selected-count text-sm font-medium text-gray-700"></span>
					<button class="btn btn-xs btn-primary sc-bulk-approve">${__("Approve Selected")}</button>
					<button class="btn btn-xs btn-danger sc-bulk-reject">${__("Reject + Send Regret")}</button>
				</div>

				<div class="border rounded-lg overflow-hidden">
					<table class="table sc-table" style="margin-bottom:0;">
						<thead>
							<tr class="text-xs uppercase text-gray-500">
								<th style="width:36px"><input type="checkbox" class="sc-master-check"></th>
								<th>${__("Candidate")}</th>
								<th>${__("Job Opening")}</th>
								<th>${__("Status")}</th>
								<th>${__("Score")}</th>
								<th>${__("Applied")}</th>
								<th style="text-align:right">${__("Actions")}</th>
							</tr>
						</thead>
						<tbody class="sc-tbody"></tbody>
					</table>
					<div class="sc-empty hidden text-center text-gray-400 py-10">${__("No candidates match these filters.")}</div>
				</div>
			</div>
		`);
		this.page.main.append(this.$root);

		this.$root.find("[data-filter]").on("change", (e) => {
			const el = $(e.currentTarget);
			const key = el.data("filter");
			const val = el.val();
			if (val) this.filters[key] = val;
			else delete this.filters[key];
			this.load();
		});

		this.$root.find(".sc-master-check").on("change", (e) => {
			const checked = e.currentTarget.checked;
			this.$root.find(".sc-row-check").prop("checked", checked);
			this.selected = new Set(checked ? this.rows.map((r) => r.name) : []);
			this.update_bulk_bar();
		});

		this.$root.find(".sc-bulk-approve").on("click", () => this.bulk_approve());
		this.$root.find(".sc-bulk-reject").on("click", () => this.bulk_reject_and_regret());
	}

	load() {
		frappe.call({
			method: "fanaka_app.api.shortlisted_candidates.get_shortlisted_candidates",
			args: { filters: this.filters },
			freeze: true,
			callback: (r) => {
				this.rows = r.message || [];
				this.selected.clear();
				this.render_rows();
				this.update_bulk_bar();
			},
		});
	}

	render_rows() {
		const $tbody = this.$root.find(".sc-tbody");
		const $empty = this.$root.find(".sc-empty");
		$tbody.empty();

		if (!this.rows.length) {
			$empty.removeClass("hidden");
			return;
		}
		$empty.addClass("hidden");

		this.rows.forEach((row) => {
			const score = row.custom_ai_score != null ? `${row.custom_ai_score}%` : "-";
			const status_color = row.status === "Shortlisted" ? "green" : "orange";
			const regret_badge = row.custom_regret_email_sent
				? `<span class="indicator-pill red" style="margin-left:6px;">${__("Regret sent")}</span>`
				: "";

			const $tr = $(`
				<tr>
					<td><input type="checkbox" class="sc-row-check" data-name="${frappe.utils.escape_html(row.name)}"></td>
					<td>
						<a href="/app/job-applicant/${encodeURIComponent(row.name)}" class="font-medium">
							${frappe.utils.escape_html(row.applicant_name || row.name)}
						</a>
						<div class="text-xs text-gray-400">${frappe.utils.escape_html(row.email_id || "")}</div>
					</td>
					<td>${frappe.utils.escape_html(row.job_title || "")}</td>
					<td><span class="indicator-pill ${status_color}">${frappe.utils.escape_html(row.status)}</span>${regret_badge}</td>
					<td class="font-mono">${score}</td>
					<td>${frappe.datetime.str_to_user(row.creation)}</td>
					<td style="text-align:right; white-space:nowrap;">
						<button class="btn btn-xs btn-primary sc-approve-invite" data-name="${frappe.utils.escape_html(row.name)}">
							${__("Approve + Invite")}
						</button>
						<button class="btn btn-xs btn-danger sc-reject-regret" data-name="${frappe.utils.escape_html(row.name)}">
							${__("Reject")}
						</button>
					</td>
				</tr>
			`);
			$tbody.append($tr);
		});

		$tbody.find(".sc-row-check").on("change", (e) => {
			const name = $(e.currentTarget).data("name");
			if (e.currentTarget.checked) this.selected.add(name);
			else this.selected.delete(name);
			this.update_bulk_bar();
		});
		$tbody.find(".sc-approve-invite").on("click", (e) => {
			this.open_approve_invite_dialog($(e.currentTarget).data("name"));
		});
		$tbody.find(".sc-reject-regret").on("click", (e) => {
			this.reject_and_regret($(e.currentTarget).data("name"));
		});
	}

	update_bulk_bar() {
		const $bar = this.$root.find(".sc-bulk-bar");
		if (this.selected.size) {
			$bar.removeClass("hidden");
			this.$root.find(".sc-selected-count").text(__("{0} selected", [this.selected.size]));
		} else {
			$bar.addClass("hidden");
		}
	}

	open_approve_invite_dialog(name) {
		const row = this.rows.find((r) => r.name === name);
		const dialog = new frappe.ui.Dialog({
			title: __("Approve & Schedule Interview"),
			fields: [
				{
					label: __("Interview Type"),
					fieldname: "interview_type",
					fieldtype: "Link",
					options: "Interview Type",
					reqd: 1,
					get_query: () =>
						row && row.designation ? { filters: [["designation", "=", row.designation]] } : {},
				},
				{ label: __("Date"), fieldname: "scheduled_on", fieldtype: "Date", reqd: 1 },
				{ label: __("From Time"), fieldname: "from_time", fieldtype: "Time", reqd: 1 },
				{ label: __("To Time"), fieldname: "to_time", fieldtype: "Time", reqd: 1 },
			],
			primary_action_label: __("Approve & Send Invite"),
			primary_action: (values) => {
				frappe.call({
					method: "fanaka_app.api.shortlisted_candidates.approve_and_invite",
					args: { job_applicant: name, ...values },
					freeze: true,
					callback: () => {
						dialog.hide();
						frappe.show_alert({ message: __("Interview scheduled, invite queued."), indicator: "green" });
						this.load();
					},
				});
			},
		});
		dialog.show();
	}

	reject_and_regret(name) {
		frappe.confirm(__("Reject this candidate and queue a regret email?"), () => {
			frappe.call({
				method: "fanaka_app.api.shortlisted_candidates.reject_and_regret",
				args: { job_applicant: name },
				freeze: true,
				callback: () => {
					frappe.show_alert({ message: __("Rejected, regret email queued."), indicator: "orange" });
					this.load();
				},
			});
		});
	}

	bulk_approve() {
		const names = Array.from(this.selected);
		if (!names.length) return;
		frappe.confirm(__("Approve {0} selected candidate(s)? Interviews are not scheduled in bulk.", [names.length]), () => {
			frappe.call({
				method: "fanaka_app.api.shortlisted_candidates.bulk_approve",
				args: { job_applicants: names },
				freeze: true,
				callback: (r) => {
					const { processed, skipped } = r.message || {};
					frappe.show_alert({
						message: __("Approved {0}, skipped {1}.", [processed, skipped]),
						indicator: "green",
					});
					this.load();
				},
			});
		});
	}

	bulk_reject_and_regret() {
		const names = Array.from(this.selected);
		if (!names.length) return;
		frappe.confirm(__("Reject {0} selected candidate(s) and queue regret emails?", [names.length]), () => {
			frappe.call({
				method: "fanaka_app.api.shortlisted_candidates.bulk_reject_and_regret",
				args: { job_applicants: names },
				freeze: true,
				callback: (r) => {
					const { processed } = r.message || {};
					frappe.show_alert({ message: __("Rejected {0}, regret emails queued.", [processed]), indicator: "orange" });
					this.load();
				},
			});
		});
	}
}
