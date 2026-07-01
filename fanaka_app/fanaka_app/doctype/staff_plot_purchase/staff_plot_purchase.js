// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Staff Plot Purchase", {
	setup(frm) {
		// Show plots for the chosen project (search still works by plot_no).
		frm.set_query("plot", () => {
			const filters = {};
			if (frm.doc.project) {
				filters.project = frm.doc.project;
			}
			return { filters };
		});
	},

	project(frm) {
		// Clear the plot when the project changes so it can't mismatch.
		frm.set_value("plot", null);
	},
});
