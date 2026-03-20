// ================================================
// UNPAID REQUISITIONS – Modern Beautiful Dashboard
// Clean, professional design with realtime updates
// ================================================

frappe.pages['unpaid-requisitions'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Unpaid Requisitions'),
        single_column: true
    });

    // ====================== REALTIME LISTENERS ======================
    function setupRealtimeListeners() {
        frappe.realtime.on('payment_success', (data) => {
            frappe.show_alert({
                message: __(`✅ ${data.requisitionId}: Payment Successful<br>Transaction ID: ${data.transaction_id}`),
                indicator: 'green'
            });
            wrapper.refresh();
        });

        frappe.realtime.on('payment_error', (data) => {
            frappe.msgprint({
                title: __('❌ M-Pesa Payment Failed'),
                message: __(`${data.requisitionId}: ${data.message}`),
                indicator: 'red'
            });
            wrapper.refresh();
        });
    }

    setupRealtimeListeners();

    // ====================== DYNAMIC MPESA BALANCE CARD ======================
    const balanceHtml = `
        <div class="card mb-4 shadow-sm" style="border-radius:10px; overflow:hidden;">
            <div class="card-body" style="display:flex; justify-content:space-between; align-items:center; padding:20px;">
                <div>
                    <div style="font-size:13px; color:#6c757d; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Current M-Pesa Balance</div>
                    <div id="balance-text" style="font-size:22px; font-weight:700; color:#1f272e; margin-top:8px;">Loading balance...</div>
                </div>
                <button class="btn btn-success" id="refresh-balance-btn">
                    <i class="fa fa-refresh"></i> Refresh Balance
                </button>
            </div>
        </div>
    `;
    $(balanceHtml).appendTo(page.main);

    loadMpesaBalance();
    $('#refresh-balance-btn').on('click', loadMpesaBalance);

    // ====================== TABS ======================
    const tabs = [
        { label: __('Authorise'), id: 'authorise', filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null] } },
        { label: __('Release Funds'), id: 'release', filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] } },
        { label: __('Paid'), id: 'paid', filter: { 'status': ['=', 'Paid'] } },
        { label: __('Rejected'), id: 'rejected', filter: { 'rejected_at': ['!=', null] } }
    ];

    const tabContainer = $('<div class="btn-group btn-group-tabs" role="group" style="margin-bottom:24px;"></div>').appendTo(page.main);

    tabs.forEach(tab => {
        $(`<button type="button" class="btn btn-default btn-sm tab-btn" data-id="${tab.id}">${tab.label}</button>`)
            .appendTo(tabContainer)
            .on('click', function() {
                tabContainer.find('.btn-primary').removeClass('btn-primary').addClass('btn-default');
                $(this).addClass('btn-primary').removeClass('btn-default');
                renderList(tab.filter, tab.id);
            });
    });

    // ====================== RENDER LIST ======================
    function renderList(filters, contextId) {
        page.main.find('.list-container').remove();
        page.clear_primary_action();
        page.clear_secondary_action();

        const listWrapper = $('<div class="list-container" style="min-height:320px;"></div>').appendTo(page.main);

        const table = $(`
            <table class="table table-hover" style="background:#fff; border-radius:8px; border:1px solid #ebeff2;">
                <thead style="background:#f8f9fa;">
                    <tr>
                        <th style="width:40px;text-align:center;"><input type="checkbox" class="master-checker"></th>
                        <th>${__('Description')}</th>
                        <th>${__('Amount')}</th>
                        <th>${__('Method')}</th>
                        <th>${__('Pay To')}</th>
                        <th class="text-right">${__('Actions')}</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `).appendTo(listWrapper);

        const formattedFilters = Object.keys(filters).map(key => [key, filters[key][0], filters[key][1]]);

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: "Requisitions",
                fields: ["name", "pay_to", "total_amount", "payment_method", "description", "authorised_at", "initiated_at"],
                filters: formattedFilters,
                order_by: "modified desc"
            },
            callback: function(r) {
                const tbody = table.find('tbody');
                if (r.message && r.message.length) {
                    r.message.forEach(data => {
                        const row = $(`
                            <tr style="font-size:13px;">
                                <td style="text-align:center;"><input type="checkbox" class="row-checker" data-name="${data.name}"></td>
                                <td style="padding:14px 8px;">
                                    <div style="font-weight:600;color:#1f272e;">${data.name}</div>
                                    <div class="text-muted" style="font-size:11px;">${data.description || ''}</div>
                                </td>
                                <td><span style="font-weight:bold;">${frappe.format(data.total_amount, {fieldtype: 'Currency'})}</span></td>
                                <td><span class="badge badge-info">${data.payment_method || 'N/A'}</span></td>
                                <td class="text-muted">${data.pay_to || ''}</td>
                                <td class="text-right action-area"></td>
                            </tr>
                        `).appendTo(tbody);

                        if (contextId === 'authorise' || contextId === 'release') {
                            $('<button class="btn btn-default btn-xs text-danger" title="Undo"><i class="fa fa-undo"></i></button>')
                                .appendTo(row.find('.action-area'))
                                .on('click', () => handleUndo([data.name]));
                        }
                    });
                    setupBulkActions(contextId);
                } else {
                    tbody.append(`<tr><td colspan="6" class="text-center text-muted py-5">${__('No records found')}</td></tr>`);
                }
            }
        });

        table.find('.master-checker').on('change', function() {
            table.find('.row-checker').prop('checked', this.checked);
        });
    }

    // ====================== BULK ACTIONS (your original logic) ======================
    function setupBulkActions(contextId) {
        if (contextId === 'authorise') {
            page.set_primary_action(__('Bulk Authorise'), () => {
                let selected = getSelectedNames();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));
                requestOtpVerification((otp) => {
                    performBulkUpdate(selected, {
                        'authorised_at': frappe.datetime.now_datetime(),
                        'authorised_by': frappe.session.user
                    }, __('Requisitions Authorised'));
                });
            });
        } else if (contextId === 'release') {
            page.set_primary_action(__('Bulk Release'), () => {
                let selected = getSelectedNames();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));
                frappe.confirm(__('Release payments for {0} items?', [selected.length]), () => {
                    selected.forEach(name => {
                        frappe.call({
                            method: 'fanaka_app.api.MpesaDisbursement.process_disbursement',
                            args: { requisition_id: name }
                        });
                    });
                    frappe.show_alert({message: __('Disbursement started'), indicator: 'green'});
                    setTimeout(() => wrapper.refresh(), 2000);
                });
            });
        }
    }

    // ====================== YOUR ORIGINAL FUNCTIONS (kept unchanged) ======================
    function requestOtpVerification(onSuccess) { /* paste your original OTP function here */ }
    function getSelectedNames() { /* paste your original */ }
    function performBulkUpdate(names, values, successMsg) { /* paste your original */ }
    function handleUndo(names) { /* paste your original */ }

    wrapper.refresh = function() {
        let activeBtn = tab_container.find('.btn-primary');
        if (activeBtn.length) activeBtn.trigger('click');
        else tab_container.find('button:first').trigger('click');
    };

    wrapper.refresh();
};

// ====================== DYNAMIC BALANCE (from Python) ======================
function loadMpesaBalance() {
    const text = $('#balance-text');
    text.html('<i class="fa fa-spinner fa-spin"></i> Loading...');

    frappe.call({
        method: 'fanaka_app.api.MpesaDisbursement.get_mpesa_balance',
        callback: function(r) {
            if (r.message && !r.message.error) {
                text.html(`Working: <strong>${r.message.working || 'N/A'}</strong><br>Utility: <strong>${r.message.utility || 'N/A'}</strong>`);
            } else {
                text.html('<span style="color:red;">Failed to load balance</span>');
            }
        }
    });
}