// ================================================
// UNPAID REQUISITIONS PAGE
// Modern & Beautiful Version – 19 March 2026
// Clean architecture, modern UX, professional styling
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
                message: __('{0}: Payment successful. TransID: {1}', [
                    data.requisitionId,
                    data.transaction_id
                ]),
                indicator: 'green'
            });
            wrapper.refresh();
        });

        frappe.realtime.on('payment_error', (data) => {
            frappe.msgprint({
                title: __('M-Pesa Payment Failed'),
                message: __('{0}: {1}', [data.requisitionId, data.message]),
                indicator: 'red'
            });
            wrapper.refresh();
        });
    }

    setupRealtimeListeners();

    // ====================== TABS SETUP ======================
    const tabs = [
        { label: __('Authorise'),     id: 'authorise', filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null] } },
        { label: __('Release Funds'), id: 'release',   filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] } },
        { label: __('Paid'),          id: 'paid',      filter: { 'status': ['=', 'Paid'] } },
        { label: __('Rejected'),      id: 'rejected',  filter: { 'rejected_at': ['!=', null] } }
    ];

    page.main.find('.btn-group-tabs').remove();

    const tabContainer = $('<div class="btn-group btn-group-tabs" role="group" style="margin-bottom: 24px; display: flex; gap: 4px;"></div>')
        .appendTo(page.main);

    tabs.forEach(tab => {
        $(`<button type="button" class="btn btn-default btn-sm tab-btn" data-id="${tab.id}">${tab.label}</button>`)
            .appendTo(tabContainer)
            .on('click', function() {
                tabContainer.find('.btn-primary')
                    .removeClass('btn-primary')
                    .addClass('btn-default');
                $(this).addClass('btn-primary').removeClass('btn-default');
                renderList(tab.filter, tab.id);
            });
    });

    // ====================== TABLE RENDER ======================
    function renderList(filters, contextId) {
        page.main.find('.list-container').remove();
        page.clear_primary_action();
        page.clear_secondary_action();

        const listWrapper = $('<div class="list-container" style="min-height: 320px;"></div>').appendTo(page.main);

        const tableHtml = `
            <table class="table table-hover table-light" style="background:#fff; border-radius:8px; overflow:hidden; border:1px solid #ebeff2;">
                <thead>
                    <tr style="background:#f7fafc; color:#8d99a6; font-size:12px; text-transform:uppercase; letter-spacing:0.02em;">
                        <th style="width:40px; text-align:center;"><input type="checkbox" class="master-checker"></th>
                        <th>${__('Description')}</th>
                        <th>${__('Amount')}</th>
                        <th>${__('Method')}</th>
                        <th>${__('Pay To')}</th>
                        <th class="text-right" style="padding-right:20px;">${__('Actions')}</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `;

        const table = $(tableHtml).appendTo(listWrapper);

        const formattedFilters = Object.keys(filters).map(k => [k, filters[k][0], filters[k][1]]);

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

                if (r.message?.length) {
                    r.message.forEach(data => {
                        const row = $(`
                            <tr style="font-size:13px;">
                                <td style="text-align:center;"><input type="checkbox" class="row-checker" data-name="${data.name}"></td>
                                <td style="padding:14px 8px;">
                                    <div style="font-weight:600;color:#1f272e;">${data.name}</div>
                                    <div class="text-muted" style="font-size:11px;">${data.description || ''}</div>
                                </td>
                                <td><span style="font-weight:bold;">${frappe.format(data.total_amount, { fieldtype: 'Currency' })}</span></td>
                                <td><span class="label label-info" style="font-weight:500;">${data.payment_method || 'N/A'}</span></td>
                                <td class="text-muted">${data.pay_to || ''}</td>
                                <td class="text-right action-area" style="padding-right:20px;"></td>
                            </tr>
                        `).appendTo(tbody);

                        if (contextId === 'authorise' || contextId === 'release') {
                            $('<button class="btn btn-default btn-xs text-danger" title="Undo Action"><i class="fa fa-undo"></i></button>')
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

        // Master checkbox
        table.find('.master-checker').on('change', function() {
            table.find('.row-checker').prop('checked', this.checked);
        });
    }

    // ====================== BULK ACTIONS ======================
    function setupBulkActions(contextId) {
        if (contextId === 'authorise') {
            page.set_primary_action(__('Bulk Authorise'), () => {
                const selected = getSelectedNames();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));

                requestOtpVerification((otp) => {
                    performBulkUpdate(selected, {
                        authorised_at: frappe.datetime.now_datetime(),
                        authorised_by: frappe.session.user
                    }, __('Requisitions Authorised'));
                });
            });

            page.set_secondary_action(__('Bulk Undo'), handleBulkUndo, { icon: 'fa fa-trash', class: 'btn-danger' });

        } else if (contextId === 'release') {
            page.set_primary_action(__('Bulk Release'), () => {
                const selected = getSelectedNames();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));

                frappe.confirm(__('Release payments for {0} items?', [selected.length]), () => {
                    frappe.call({
                        method: 'fanaka_app.api.MpesaDisbursement.bulk_release_disbursements',
                        args: { requisition_ids: selected },
                        callback: () => {
                            frappe.show_alert({
                                message: __('Disbursements queued in background. You can continue working.'),
                                indicator: 'green'
                            });
                            setTimeout(() => wrapper.refresh(), 1500);
                        }
                    });
                });
            });

            page.set_secondary_action(__('Bulk Undo'), handleBulkUndo, { icon: 'fa fa-trash', class: 'btn-danger' });
        }

        // Style undo button
        setTimeout(() => {
            page.wrapper.find('.btn-secondary:contains("Bulk Undo")')
                .removeClass('btn-default')
                .addClass('btn-danger')
                .css({ backgroundColor: '#ff5858', color: '#fff', border: 'none' });
        }, 10);
    }

    function handleBulkUndo() {
        const selected = getSelectedNames();
        if (!selected.length) return frappe.msgprint(__('Please select at least one item'));

        const msg = selected.length > 1
            ? __('Undo Action for {0} selected items?', [selected.length])
            : __('Undo Action for {0}? Record will move back to draft.', [selected[0]]);

        frappe.confirm(msg, () => {
            performBulkUpdate(selected, {
                initiated_at: null,
                initiated_by: null,
                authorised_at: null,
                authorised_by: null
            }, __('Action undone successfully'));
        });
    }

    // ====================== OTP VERIFICATION (Clean & Modern) ======================
    function requestOtpVerification(onSuccess) {
        frappe.call({
            method: "fanaka_app.api.MpesaDisbursement.send_otp_notification",
            callback: function(r) {
                if (r.exc) return;

                const dialog = new frappe.ui.Dialog({
                    title: __('Verify Authorisation'),
                    fields: [
                        {
                            label: __('Enter OTP sent to your phone'),
                            fieldname: 'otp',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'timer_html',
                            content: `<div id="otp-timer" style="color:#ff5858;font-weight:bold;margin:12px 0;text-align:center;">Expires in: 05:00</div>`
                        }
                    ],
                    primary_action_label: __('Verify & Authorise'),
                    primary_action(values) {
                        dialog.get_primary_btn().prop('disabled', true);

                        frappe.call({
                            method: "fanaka_app.api.MpesaDisbursement.verify_authorisation_otp",
                            args: { otp: values.otp },
                            callback: function(res) {
                                if (res.message === true) {
                                    dialog.hide();
                                    onSuccess(values.otp);
                                } else {
                                    frappe.msgprint(__('Invalid or expired OTP. Please try again.'));
                                    dialog.get_primary_btn().prop('disabled', false);
                                }
                            }
                        });
                    }
                });

                dialog.show();

                // Timer
                let duration = 300;
                const timerEl = dialog.get_field('timer_html').$wrapper.find('#otp-timer');
                const interval = setInterval(() => {
                    const min = String(Math.floor(duration / 60)).padStart(2, '0');
                    const sec = String(duration % 60).padStart(2, '0');
                    timerEl.text(`Expires in: ${min}:${sec}`);

                    if (--duration < 0) {
                        clearInterval(interval);
                        timerEl.text('OTP Expired. Please close and try again.');
                        dialog.get_primary_btn().prop('disabled', true);
                    }
                }, 1000);

                dialog.on_hide = () => clearInterval(interval);
            }
        });
    }

    // ====================== HELPERS ======================
    function getSelectedNames() {
        return page.main.find('.row-checker:checked').map(function() {
            return $(this).data('name');
        }).get();
    }

    function performBulkUpdate(names, values, successMsg) {
        const promises = names.map(name => new Promise(resolve => {
            frappe.call({
                method: 'frappe.client.set_value',
                args: { doctype: 'Requisitions', name, fieldname: values },
                callback: r => resolve(r),
                error: () => resolve(null)
            });
        }));

        Promise.all(promises).then(() => {
            frappe.show_alert({ message: successMsg, indicator: 'blue' });
            wrapper.refresh();
        });
    }

    function handleUndo(names) {
        const msg = names.length > 1
            ? __('Undo Action for {0} selected items?', [names.length])
            : __('Undo Action for {0}? Record will move back to draft.', [names[0]]);

        frappe.confirm(msg, () => {
            performBulkUpdate(names, {
                initiated_at: null,
                initiated_by: null,
                authorised_at: null,
                authorised_by: null
            }, __('Action undone successfully'));
        });
    }

    // ====================== REFRESH ======================
    wrapper.refresh = function() {
        const activeBtn = tabContainer.find('.btn-primary');
        if (activeBtn.length) {
            activeBtn.trigger('click');
        } else {
            tabContainer.find('button:first').trigger('click');
        }
    };

    // Initial load
    wrapper.refresh();
};