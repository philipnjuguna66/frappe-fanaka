frappe.ui.form.on("Requisitions", {
    is_inter_company: function(frm) {
        if (frm.doc.is_inter_company) {
            //frm.set_value('voucher_type', 'Inter Company Journal Entry');
        } else {
            //frm.set_value('voucher_type', 'Journal Entry');
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
                    company: frm.doc.company
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