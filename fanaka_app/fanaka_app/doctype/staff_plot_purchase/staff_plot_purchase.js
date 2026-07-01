// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Staff Plot Purchase", {
	setup(frm) {
		// Restrict the plot list: to the selected sale order's plots if set,
		// otherwise to the selected project. Search still works by plot_no.
		frm.set_query("plot", () => {
			if (frm._sale_order_plots && frm._sale_order_plots.length) {
				return { filters: { name: ["in", frm._sale_order_plots] } };
			}
			if (frm.doc.project) {
				return { filters: { project: frm.doc.project } };
			}
			return {};
		});
	},

	project(frm) {
		frm.set_value("plot", null);
	},

	sale_order(frm) {
		frm._sale_order_plots = [];
		frm.set_value("plot", null);

		if (!frm.doc.sale_order) {
			return;
		}

		// Pull the plots referenced on the sale order's item lines.
		frappe.db
			.get_doc("Sales Order", frm.doc.sale_order)
			.then((so) => {
				const plots = (so.items || [])
					.map((row) => row.custom_plot)
					.filter(Boolean);
				frm._sale_order_plots = plots;

				if (plots.length === 1) {
					frm.set_value("plot", plots[0]);
				}
			});
	},
});
