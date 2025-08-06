// Copyright (c) 2025, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Requisitions", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) { // docstatus 1 means submitted
            frm.add_custom_button(__('View Ledger'), function() {
                if (frm.doc.journal_entry) {
                    frappe.set_route('query-report', 'General Ledger', {
                        voucher_no: frm.doc.journal_entry,
                        company: frm.doc.company // Pass company for context if needed
                    });
                } else {
                    frappe.msgprint(__('No Journal Entry linked to this transaction.'));
                }
            }, __("View"));
        }
    },
});
