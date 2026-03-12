// Copyright (c) 2025, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Requisitions", {
    is_inter_company: function(frm) {
        if (frm.doc.is_inter_company) {
            // frm.set_value('voucher_type', 'Inter Company Journal Entry');
        } else {
            // frm.set_value('voucher_type', 'Journal Entry');
        }
    },
    
    refresh: function(frm) {
        // Hide posting fields if already submitted to prevent confusion
        if (frm.doc.docstatus === 1) {
            frm.set_df_property('posting_requisitions_section', 'hidden', 0);
        }
        
        // Existing View Ledger Button logic...
        if (frm.doc.docstatus === 1 && frm.doc.journal_entry) {
            frm.add_custom_button(__('View Ledger'), function() {
                frappe.set_route('query-report', 'General Ledger', {
                    voucher_no: frm.doc.journal_entry,
                    // company: frm.doc.company
                });
            }, __("View"));
        }
    }
});

function calculate_total(frm) {
    let total = 0;
    if (frm.doc.requisition_items) {
        frm.doc.requisition_items.forEach(function(d) {
            total += d.subtotal;
        });
    }
    frm.set_value('total_amount', total);
    frm.refresh_field('total_amount');
}

frappe.ui.form.on('Requisition Items', {
    subtotal(frm) {
        calculate_total(frm);
    },
    requisition_items_remove(frm) {
        calculate_total(frm);
    }
});

frappe.listview_settings['Requisitions'] = {
    add_fields: ["status", "requisition_owner"],

    onload: function(listview) {

        const statuses = ["pending", "approved", "rejected", "paid", "submitted"];

        // Show all records
        listview.page.add_inner_button(__('All'), function () {
            listview.filter_area.clear();
            listview.refresh();
        });

        statuses.forEach(function(status) {

            const label = status.charAt(0).toUpperCase() + status.slice(1);

            listview.page.add_inner_button(__(label), function () {

                // clear existing filters first
                listview.filter_area.clear();

                // add the selected filter
                listview.filter_area.add(
                    'Requisitions',
                    'status',
                    '=',
                    status
                );

                // refresh list
                listview.refresh();
            });

        });

    },

    formatters: {
        requisition_owner(val) {
            return frappe.utils.get_fullname(val);
        }
    }
};