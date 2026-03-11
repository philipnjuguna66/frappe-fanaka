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

frappe.listview_settings['Requisitions'] = {
    add_fields: ["requisition_owner"],
    onload: function(listview) {
        listview.page.fields_dict['requisition_owner'].get_query = function() {
            return { filters: { enabled: 1 } };
        };
    },
    formatters: {
        requisition_owner(val, df, doc) {
            // This replaces the email with the Full Name in the list UI without changing data
            return frappe.user.full_name(val);
        }
    }
};
