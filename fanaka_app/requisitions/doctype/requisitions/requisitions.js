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
    
    refresh: function(listview) {
        // We use refresh instead of onload to ensure the DOM is ready 
        // and to re-inject if the list is navigated back to.
        
        if (listview.$page.find('.list-status-filter').length) {
            return; // Don't add buttons if they already exist
        }

        const status_filters = ['pending', 'approved', 'rejected', 'paid', 'submitted'];
        
        let html = `
            <div class="btn-group list-status-filter" role="group" style="margin-right: 10px; display: inline-flex; align-items: center;">
                <button type="button" class="btn btn-default btn-sm btn-all active" data-status="All" style="font-weight: 500;">${__('All')}</button>
        `;

        status_filters.forEach(status => {
            // Capitalize for UI display but keep data-status lowercase for filtering
            let label = status.charAt(0).toUpperCase() + status.slice(1);
            html += `<button type="button" class="btn btn-default btn-sm" data-status="${status}">${__(label)}</button>`;
        });

        html += `</div>`;

        // More robust injection point: find the primary action container or breadcrumbs
        const $container = listview.$page.find('.page-actions-block');
        if ($container.length) {
            $(html).prependTo($container);
        } else {
            // Fallback to the standard list actions area
            $(html).prependTo(listview.$page.find('.list-view-actions'));
        }

        // Click Event Handler
        listview.$page.on('click', '.list-status-filter button', function() {
            const $btn = $(this);
            const status = $btn.data('status');

            // Visual toggle
            $btn.siblings().removeClass('active btn-primary').addClass('btn-default');
            $btn.addClass('active btn-primary').removeClass('btn-default');

            // Apply filter logic
            listview.filter_area.remove('status');
            if (status !== 'All') {
                listview.filter_area.add('Requisitions', 'status', '=', status);
            } else {
                listview.refresh();
            }
        });
    },

    formatters: {
        requisition_owner(val) {
            return frappe.utils.get_fullname(val);
        }
    }
};