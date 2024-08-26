// Copyright (c) 2024, Philip Njuguna and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Requisition", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Requisition', {
    refresh: function (frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('View Ledger'), function () {
                frappe.set_route('query-report', 'General Ledger', {
                    from_date: frm.doc.paying_date,
                    to_date: frm.doc.paying_date,
                    account: frm.doc.expense_account,
                });
            });
        }
    },


});


frappe.ui.form.on("Requisition Item", {
    amount: function (frm, cdt, cdn) {

        total  = 0;

        frm.doc.items.forEach(function(row) {
            total += row.amount;
        });
        frm.set_value('total_amount', total);

    },

    items_remove: function(frm, cdt, cdn) {
        total  = 0;

        frm.doc.items.forEach(function(row) {
            total += row.amount;
        });
        frm.set_value('total_amount', total);
    }

});

