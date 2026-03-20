// ================================================
// UNPAID REQUISITIONS – Beautiful Modern Dashboard
// Full merged version with realtime notifications + beautification
// ================================================

frappe.pages['unpaid-requisitions'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Unpaid Requisitions'),
        single_column: true
    });

    // ====================== REALTIME NOTIFICATIONS ======================
    function setup_realtime_listeners() {
        frappe.realtime.on('payment_success', (data) => {
            frappe.show_alert({
                message: __(`✅ ${data.requisitionId}: Payment Successful<br>TransID: ${data.transaction_id}`),
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
    setup_realtime_listeners();

  
// Inject Modern Styles
const styles = `
    <style>
        .mpesa-dashboard-header .stat-card {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            border-left: 4px solid transparent !important;
        }
        .mpesa-dashboard-header .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md) !important;
        }
        #working-balance-card { border-left-color: #28a745 !important; }
        #utility-balance-card { border-left-color: #007bff !important; }
        
        .tab-btn { margin-right: 5px; border-radius: 20px !important; padding: 5px 15px !important; font-weight: 500; }
        .tab-btn.btn-primary { box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        .list-container table { border-collapse: separate; border-spacing: 0 8px; background: transparent !important; border: none !important; }
        .list-container tr { background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-radius: 8px; }
        .list-container td { border: none !important; vertical-align: middle !important; }
        .list-container td:first-child { border-top-left-radius: 8px; border-bottom-left-radius: 8px; }
        .list-container td:last-child { border-top-right-radius: 8px; border-bottom-right-radius: 8px; }
        
        .otp-timer { font-weight: bold; color: #d63031; font-size: 1.2em; }
        .resend-link { cursor: pointer; color: #0984e3; text-decoration: underline; font-size: 13px; font-weight: 600; }
        .resend-link.disabled { color: #b2bec3; cursor: not-allowed; text-decoration: none; pointer-events: none; }
        .timer-container { background: #f1f2f6; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
    </style>
`;
$('head').append(styles);

// ====================== DYNAMIC MPESA BALANCE CARD ======================
const headerHtml = `
    <div class="mpesa-dashboard-header" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div id="working-balance-card" class="stat-card" style="background: #fff; border: 1px solid #d1d8dd; border-radius: 8px; padding: 16px; box-shadow: var(--shadow-sm);">
            <div style="color: #8d99a6; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Working Account</div>
            <div id="working-balance" style="font-size: 22px; font-weight: 700; color: #1f272e; margin-top: 4px;">KES 0.00</div>
        </div>
        <div id="utility-balance-card" class="stat-card" style="background: #fff; border: 1px solid #d1d8dd; border-radius: 8px; padding: 16px; box-shadow: var(--shadow-sm);">
            <div style="color: #8d99a6; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Utility Account</div>
            <div id="utility-balance" style="font-size: 22px; font-weight: 700; color: #2490ef; margin-top: 4px;">KES 0.00</div>
        </div>
        <div class="stat-card" style="background: #f8fafc; border: 1px dashed #d1d8dd; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
            <div id="last-updated-text" style="font-size: 11px; color: #8d99a6; margin-bottom: 8px; font-style: italic;">Syncing...</div>
            <button class="btn btn-xs btn-default" id="refresh-mpesa-btn" style="border-radius: 4px;">
                <i class="fa fa-refresh text-success"></i> Sync Balance
            </button>
        </div>
    </div>
`;

page.main.append(headerHtml);
renderDatabaseBalances();

$('#refresh-mpesa-btn').on('click', function() {
    const $btn = $(this);
    $btn.find('i').addClass('fa-spin');
    frappe.call({
        method: 'fanaka_app.api.MpesaDisbursement.get_mpesa_balance',
        callback: () => {
            frappe.show_alert({message: __('Syncing with Safaricom...'), indicator: 'orange'});
            setTimeout(() => {
                renderDatabaseBalances();
                $btn.find('i').removeClass('fa-spin');
            }, 4000);
        }
    });
});

function renderDatabaseBalances() {
    frappe.call({
        method: 'fanaka_app.api.MpesaDisbursement.get_stored_mpesa_balance',
        callback: function(r) {
            if(r.message) {
                $('#working-balance').text(r.message.working_balance);
                $('#utility-balance').text(r.message.utility_balance);
                $('#last-updated-text').text('Last Sync: ' + r.message.last_updated);
            }
        }
    });
}





    // ====================== TABS ======================
    let tabs = [
        { label: __('Authorise'), id: 'authorise', filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null] } },
        { label: __('Release Funds'), id: 'release', filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] } },
        { label: __('Paid'), id: 'paid', filter: { 'status': ['=', 'Paid'] } },
        { label: __('Rejected'), id: 'rejected', filter: { 'rejected_at': ['!=', null] } }
    ];

    page.main.find('.btn-group-tabs').remove();
    let tab_container = $('<div class="btn-group btn-group-tabs" role="group" style="margin-bottom: 20px;"></div>').appendTo(page.main);
    
    tabs.forEach(tab => {
        $(`<button type="button" class="btn btn-default btn-sm tab-btn" data-id="${tab.id}">${tab.label}</button>`)
            .appendTo(tab_container)
            .on('click', function() {
                tab_container.find('.btn-primary').removeClass('btn-primary').addClass('btn-default');
                $(this).addClass('btn-primary').removeClass('btn-default');
                render_list(tab.filter, tab.id);
            });
    });

    // ====================== RENDER LIST ======================
    function render_list(filters, context_id) {
        page.main.find('.list-container').remove();
        page.clear_primary_action();
        page.clear_secondary_action();

        let list_wrapper = $('<div class="list-container" style="min-height: 300px;"></div>').appendTo(page.main);

        let table = $(`<table class="table table-hover table-light" style="background: #fff; border-radius: 4px; overflow: hidden; border: 1px solid #ebeff2;">
            <thead>
                <tr style="background: #f7fafc; color: #8d99a6; font-size: 12px; text-transform: uppercase; letter-spacing: 0.02em;">
                    <th style="width: 40px; text-align: center;"><input type="checkbox" class="master-checker"></th>
                    <th>${__('Description')}</th>
                    <th>${__('Amount')}</th>
                    <th>${__('Method')}</th>
                    <th>${__('Pay To')}</th>
                    <th class="text-right" style="padding-right: 15px;">${__('Actions')}</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>`).appendTo(list_wrapper);

        let formatted_filters = [];
        for (let key in filters) {
            formatted_filters.push([key, filters[key][0], filters[key][1]]);
        }

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: "Requisitions",
                fields: ["name", "pay_to", "total_amount", "payment_method", "description", "authorised_at", "initiated_at"],
                filters: formatted_filters,
                order_by: "modified desc"
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    r.message.forEach(data => {
                        let row = $(`<tr style="font-size: 13px;">
                            <td style="text-align: center;"><input type="checkbox" class="row-checker" data-name="${data.name}"></td>
                            <td style="padding: 12px 8px;">
                                <div style="font-weight: 600; color: #1f272e;">${data.name}</div>
                                <div class="text-muted" style="font-size: 11px;">${data.description || ''}</div>
                            </td>
                            <td><span style="font-weight: bold;">${frappe.format(data.total_amount, {fieldtype: 'Currency'})}</span></td>
                            <td><span class="label label-info" style="font-weight: 500;">${data.payment_method || 'N/A'}</span></td>
                            <td class="text-muted">${data.pay_to || ''}</td>
                            <td class="text-right action-area" style="padding-right: 15px;"></td>
                        </tr>`).appendTo(table.find('tbody'));

                        if (context_id === 'authorise' || context_id === 'release') {
                            $(`<button class="btn btn-default btn-xs text-danger" title="${__('Undo Action')}"><i class="fa fa-undo"></i></button>`)
                                .appendTo(row.find('.action-area'))
                                .on('click', () => handle_undo([data.name]));
                        }
                    });

                    setup_bulk_actions(context_id);
                } else {
                    table.find('tbody').append(`<tr><td colspan="6" class="text-center text-muted" style="padding: 60px;">${__('No records found')}</td></tr>`);
                }
            }
        });

        table.find('.master-checker').on('change', function() {
            table.find('.row-checker').prop('checked', $(this).prop('checked'));
        });
    }

    // ====================== YOUR ORIGINAL FUNCTIONS (EXACTLY AS YOU PROVIDED) ======================
    function setup_bulk_actions(context_id) {
        if (context_id === 'authorise') {
            page.set_primary_action(__('Bulk Authorise'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));
                
                request_otp_verification((otp) => {
                    perform_bulk_update(selected, {
                        'authorised_at': frappe.datetime.now_datetime(),
                        'authorised_by': frappe.session.user
                    }, __('Requisitions Authorised'));
                });
            });

            page.set_secondary_action(__('Bulk Undo'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));
                handle_undo(selected);
            }, { icon: 'fa fa-trash', class: 'btn-danger' });

        } else if (context_id === 'release') {
            page.set_primary_action(__('Bulk Release'), () => {
                let selected = get_selected_names();
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

            page.set_secondary_action(__('Bulk Undo'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Please select at least one item'));
                handle_undo(selected);
            }, { icon: 'fa fa-trash', class: 'btn-danger' });
        }

        setTimeout(() => {
            page.wrapper.find('.btn-secondary:contains("Bulk Undo")')
                .removeClass('btn-default')
                .addClass('btn-danger')
                .css({'background-color': '#ff5858', 'color': 'white', 'border': 'none'});
        }, 10);
    }

    function request_otp_verification(on_success) {
        frappe.call({
            method: "fanaka_app.api.MpesaDisbursement.send_otp_notification", 
            callback: function(r) {
                if (r.exc) return;

                let d = new frappe.ui.Dialog({
                    title: __('Verify Authorisation'),
                    fields: [
                        {
                            label: __('Enter OTP sent to your phone/email'),
                            fieldname: 'otp',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'timer_html',
                            content: `<div id="otp-timer" style="color: #ff5858; font-weight: bold; margin-top: 10px; text-align: center;">
                                ${__('Expires in')}: 05:00
                            </div>`
                        }
                    ],
                    primary_action_label: __('Verify & Authorise'),
                    primary_action(values) {
                        d.get_primary_btn().prop('disabled', true);
                        
                        frappe.call({
                            method: "fanaka_app.api.MpesaDisbursement.verify_authorisation_otp",
                            args: { otp: values.otp },
                            callback: function(res) {
                                if (res.message === true) {
                                    d.hide();
                                    clearInterval(timer_interval);
                                    on_success(values.otp);
                                } else {
                                    frappe.msgprint(__('Invalid or expired OTP. Please try again.'));
                                    d.get_primary_btn().prop('disabled', false);
                                }
                            }
                        });
                    }
                });

                d.show();

                let duration = 5 * 60;
                let timer_display = d.get_field('timer_html').$wrapper.find('#otp-timer');
                
                let timer_interval = setInterval(() => {
                    let minutes = parseInt(duration / 60, 10);
                    let seconds = parseInt(duration % 60, 10);

                    minutes = minutes < 10 ? "0" + minutes : minutes;
                    seconds = seconds < 10 ? "0" + seconds : seconds;

                    timer_display.text(`${__('Expires in')}: ${minutes}:${seconds}`);

                    if (--duration < 0) {
                        clearInterval(timer_interval);
                        timer_display.text(__('OTP Expired. Please close and try again.'));
                        d.get_primary_btn().prop('disabled', true);
                    }
                }, 1000);

                d.on_hide = () => clearInterval(timer_interval);
            }
        });
    }

    function get_selected_names() {
        return page.main.find('.row-checker:checked').map(function() {
            return $(this).data('name');
        }).get();
    }

    function perform_bulk_update(names, values, success_msg) {
        let promises = names.map(name => {
            return new Promise((resolve) => {
                frappe.call({
                    method: 'frappe.client.set_value',
                    args: {
                        doctype: 'Requisitions',
                        name: name,
                        fieldname: values
                    },
                    callback: (r) => resolve(r),
                    error: (r) => {
                        console.error("Bulk update failed for: " + name, r);
                        resolve(null);
                    }
                });
            });
        });

        Promise.all(promises).then(() => {
            frappe.show_alert({message: success_msg, indicator: 'blue'});
            wrapper.refresh();
        });
    }

    function handle_undo(names) {
        let msg = names.length > 1 
            ? __('Undo Action for {0} selected items?', [names.length]) 
            : __('Undo Action for {0}? Record will move back to draft/pending initiation.', [names[0]]);

        frappe.confirm(msg, () => {
            perform_bulk_update(names, {
                'initiated_at': null,
                'initiated_by': null,
                'authorised_at': null,
                'authorised_by': null
            }, __('Action undone successfully'));
        });
    }

    wrapper.refresh = function() {
        let active_btn = tab_container.find('.btn-primary');
        if (active_btn.length) {
            active_btn.trigger('click');
        } else {
            tab_container.find('button:first').trigger('click');
        }
    };

    wrapper.refresh();
};

// ====================== DYNAMIC BALANCE FUNCTION ======================
function loadMpesaBalance() {
    const balanceText = $('#balance-text');
    balanceText.html('<i class="fa fa-spinner fa-spin"></i> Loading...');

    frappe.call({
        method: 'fanaka_app.api.MpesaDisbursement.get_mpesa_balance',
        callback: function(r) {
            if (r.message && !r.message.error) {
                balanceText.html(`Working: <strong>${r.message.working || 'N/A'}</strong><br>Utility: <strong>${r.message.utility || 'N/A'}</strong>`);
            } else {
                balanceText.html('<span style="color:red;">Failed to load balance</span>');
            }
        }
    });
}