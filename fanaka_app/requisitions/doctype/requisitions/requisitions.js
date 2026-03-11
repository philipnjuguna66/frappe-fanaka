// Copyright (c) 2025, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Requisitions", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.journal_entry) {
            frm.add_custom_button(__('View Ledger'), function() {
                // Fetch the JE company to ensure the report filters correctly
                frappe.db.get_value('Journal Entry', frm.doc.journal_entry, 'company', (r) => {
                    frappe.set_route('query-report', 'General Ledger', {
                        voucher_no: frm.doc.journal_entry,
                        company: r.company
                    });
                });
            }, __("View"));
        }
    }
});

frappe.listview_settings['Requisitions'] = {
    add_fields: ["requisition_owner"],
    formatters: {
        requisition_owner(val, df, doc) {
            // Using frappe.user.full_name is correct for current user, 
            // but for any user ID, we should use the cache or a quick map
            return frappe.utils.get_fullname(val);
        }
    }
};