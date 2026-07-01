// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

const PLOT_QUERY =
	"fanaka_app.fanaka_app.doctype.staff_plot_purchase.staff_plot_purchase.get_project_plots";

frappe.ui.form.on("Staff Plot Purchase", {
	refresh(frm) {
		// Default the payroll date to the last day of the previous month
		// (editable). month_start() = 1st of this month, minus 1 day.
		if (frm.is_new() && !frm.doc.payroll_date) {
			frm.set_value(
				"payroll_date",
				frappe.datetime.add_days(frappe.datetime.month_start(), -1)
			);
		}
	},

	setup(frm) {
		// Plots of the selected sale order, else the selected project. Shows all
		// statuses (available + sold, sold plots show the buyer).
		frm.set_query("plot", () => {
			const filters = {};
			if (frm._sale_order_plots && frm._sale_order_plots.length) {
				filters.plots = frm._sale_order_plots;
			} else if (frm.doc.project) {
				filters.project = frm.doc.project;
			}
			return { query: PLOT_QUERY, filters };
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

		// Pull the plots referenced on the sale order's item lines (any docstatus).
		frappe.db.get_doc("Sales Order", frm.doc.sale_order).then((so) => {
			const plots = (so.items || []).map((row) => row.custom_plot).filter(Boolean);
			frm._sale_order_plots = plots;
			if (plots.length === 1) {
				frm.set_value("plot", plots[0]);
			}
		});
	},
});
