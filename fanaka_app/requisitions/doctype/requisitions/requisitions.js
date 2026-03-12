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

    onload(listview) {

        const statuses = ["pending","approved","rejected","paid","submitted"];

        // wait for page to fully render
        setTimeout(() => {

            let container = listview.page.wrapper.find('.custom-status-buttons');

            // prevent duplicate buttons on refresh
            if (container.length) return;

            container = $(`<div class="custom-status-buttons" style="margin-bottom:10px;"></div>`);
            listview.page.wrapper.find('.layout-main-section').prepend(container);

            // ALL BUTTON
            let all_btn = $(`<button class="btn btn-sm btn-default">All</button>`);
            all_btn.click(() => {
                listview.filter_area.clear();
                listview.refresh();
            });
            container.append(all_btn);

            // STATUS BUTTONS
            statuses.forEach(status => {

                let label = status.charAt(0).toUpperCase() + status.slice(1);

                let btn = $(`<button class="btn btn-sm btn-default" style="margin-left:5px;">${label}</button>`);

                btn.click(() => {
                    listview.filter_area.clear();

                    listview.filter_area.add_filter([
                        "Requisitions",
                        "status",
                        "=",
                        status
                    ]);

                    listview.refresh();
                });

                container.append(btn);
            });

        }, 300);
    }
};