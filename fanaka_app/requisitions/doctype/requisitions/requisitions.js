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
        
         if (!frm.doc.initiated_at && !frm.doc.__islocal) {
            frm.add_custom_button(__('Initiate Payment'), function() {
                frm.events.initiate_requisition_payment(frm);
            }, __('Actions'));
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
    },
    initiate_requisition_payment: function(frm) {
        frappe.confirm(__('Are you sure you want to initiate payment for this requisition?'), () => {
            frappe.call({
                method: 'fanaka_app.api.requisition.initiate_payment',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Payment successfully initiated'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        });
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

