// ================================================
// UNPAID REQUISITIONS – Modern Beautiful Dashboard
// Dynamic M-Pesa Balance + Bulk Authorise with OTP
// ================================================

frappe.pages['unpaid-requisitions'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Unpaid Requisitions'),
        single_column: true
    });

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
            
            .otp-timer { font-weight: bold; color: var(--red-500); font-size: 1.1em; }
            .resend-link { cursor: pointer; color: var(--primary); text-decoration: underline; font-size: 12px; }
            .resend-link.disabled { color: #8d99a6; cursor: not-allowed; text-decoration: none; }
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

    // Load initial balances
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
        { label: __('Authorise'), id: 'authorise', filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null], 'status': ['!=', 'Rejected'] } },
        { label: __('Release Funds'), id: 'release', filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] } },
        { label: __('Paid'), id: 'paid', filter: { 'status': ['=', 'Paid'] } },
        { label: __('Rejected'), id: 'rejected', filter: { 'status': ['=', 'Rejected'] } }
    ];

    let tab_container = $('<div class="btn-group btn-group-tabs" role="group" style="margin-bottom: 25px;"></div>').appendTo(page.main);
    
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

        let list_wrapper = $('<div class="list-container"></div>').appendTo(page.main);

        let table = $(`<table class="table table-hover">
            <thead>
                <tr style="color: #8d99a6; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">
                    <th style="width: 45px; text-align: center;"><input type="checkbox" class="master-checker"></th>
                    <th>${__('Requisition Details')}</th>
                    <th>${__('Amount')}</th>
                    <th>${__('Method')}</th>
                    <th>${__('Payee')}</th>
                    <th class="text-right">${__('Action')}</th>
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
                fields: ["name", "pay_to", "total_amount", "payment_method", "description"],
                filters: formatted_filters,
                order_by: "modified desc"
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    r.message.forEach(data => {
                        let row = $(`<tr>
                            <td style="text-align: center;"><input type="checkbox" class="row-checker" data-name="${data.name}"></td>
                            <td>
                                <div style="font-weight: 700; color: #1f272e;">${data.name}</div>
                                <div class="text-muted" style="font-size: 11px; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${data.description || 'No description'}</div>
                            </td>
                            <td><span style="font-weight: 700; color: #2d3436;">${frappe.format(data.total_amount, {fieldtype: 'Currency'})}</span></td>
                            <td><span class="badge" style="background-color: #f1f2f6; color: #2f3542; font-weight: 600; text-transform: capitalize;">${data.payment_method || 'N/A'}</span></td>
                            <td class="text-muted" style="font-size: 12px;">${data.pay_to || '-'}</td>
                            <td class="text-right action-area"></td>
                        </tr>`).appendTo(table.find('tbody'));

                        if (context_id === 'authorise' || context_id === 'release') {
                            $(`<button class="btn btn-default btn-xs" style="color: #ff4757; border: none;" title="${__('Undo')}"><i class="fa fa-undo"></i></button>`)
                                .appendTo(row.find('.action-area'))
                                .on('click', () => handle_undo([data.name]));
                        }
                    });
                    setup_bulk_actions(context_id);
                } else {
                    table.find('tbody').append(`<tr><td colspan="6" class="text-center text-muted" style="padding: 80px; background: #fff; border-radius: 8px;">
                        <i class="fa fa-folder-open-o" style="font-size: 24px; display: block; margin-bottom: 10px;"></i>
                        ${__('All caught up! No requisitions here.')}</td></tr>`);
                }
            }
        });

        table.find('.master-checker').on('change', function() {
            table.find('.row-checker').prop('checked', $(this).prop('checked'));
        });
    }

    // ====================== BULK ACTIONS & OTP ======================
    function setup_bulk_actions(context_id) {
        if (context_id === 'authorise') {
            page.set_primary_action(__('Bulk Authorise'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Please select requisitions to authorise'));
                
                initiate_authorisation_workflow(selected);
            });

            page.set_secondary_action(__('Reject Selected'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Select items to reject'));
                handle_reject(selected);
            }, { icon: 'fa fa-times', class: 'btn-danger' });

        } else if (context_id === 'release') {
            page.set_primary_action(__('Bulk Release'), () => {
                let selected = get_selected_names();
                if (!selected.length) return frappe.msgprint(__('Select items to release funds'));
                
                frappe.confirm(__('Release M-Pesa payments for {0} items?', [selected.length]), () => {
                    selected.forEach(name => {
                        frappe.call({
                            method: 'fanaka_app.api.MpesaDisbursement.process_disbursement',
                            args: { requisition_id: name }
                        });
                    });
                    frappe.show_alert({message: __('Disbursement sequence triggered'), indicator: 'green'});
                    setTimeout(() => wrapper.refresh(), 2000);
                });
            });
        }
    }

    // ====================== OTP WORKFLOW ======================
    function initiate_authorisation_workflow(selected_names) {
        // 1. Send OTP via backend
        frappe.call({
            method: 'fanaka_app.api.MpesaDisbursement.send_otp_notification', // Assumes this API exists to send SMS/Email
            callback: (r) => {
                if(!r.exc) {
                    show_otp_modal(selected_names);
                }
            }
        });
    }

    function show_otp_modal(selected_names) {
        let d = new frappe.ui.Dialog({
            title: __('Verify Authorisation'),
            fields: [
                {
                    html: `<div class="text-center" style="margin-bottom: 15px;">
                        <p>${__('An OTP has been sent to your registered device.')}</p>
                        <div class="otp-timer-wrapper">Time remaining: <span id="timer-val" class="otp-timer">05:00</span></div>
                    </div>`
                },
                {
                    label: __('Enter OTP Code'),
                    fieldname: 'otp_code',
                    fieldtype: 'Int',
                    reqd: 1
                },
                {
                    html: `<div class="text-center" style="margin-top: 10px;">
                        <span id="resend-otp-btn" class="resend-link disabled">${__('Resend OTP')}</span>
                    </div>`
                }
            ],
            primary_action_label: __('Confirm & Authorise'),
            primary_action(values) {
                frappe.call({
                    method: 'fanaka_app.api.MpesaDisbursement.verify_authorisation_otp',
                    args: { otp: values.otp_code },
                    callback: (r) => {
                        if (r.message === true) {
                            d.hide();
                            perform_bulk_update(selected_names, {
                                'authorised_at': frappe.datetime.now_datetime(),
                                'authorised_by': frappe.session.user
                            }, __('Bulk Authorisation Successful'));
                        } else {
                            frappe.msgprint({title: __('Invalid OTP'), message: __('The code entered is incorrect or expired.'), indicator: 'red'});
                        }
                    }
                });
            }
        });

        d.show();

        // Timer Logic
        let timeLeft = 300; // 5 Minutes
        let timerInterval = setInterval(() => {
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                $('#timer-val').text('Expired');
                $('#resend-otp-btn').removeClass('disabled').on('click', () => {
                    d.hide();
                    initiate_authorisation_workflow(selected_names);
                });
            } else {
                let mins = Math.floor(timeLeft / 60);
                let secs = timeLeft % 60;
                $('#timer-val').text(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
                timeLeft--;
            }
        }, 1000);

        d.on_hide = () => clearInterval(timerInterval);
    }

    // ====================== CORE UTILS ======================
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
                    error: () => resolve(null)
                });
            });
        });

        Promise.all(promises).then(() => {
            frappe.show_alert({message: success_msg, indicator: 'green'});
            wrapper.refresh();
        });
    }

    function handle_undo(names) {
        frappe.confirm(__('Move {0} items back to draft/initiated status?', [names.length]), () => {
            perform_bulk_update(names, {
                'authorised_at': null,
                'authorised_by': null,
                'status': 'Pending Authorisation'
            }, __('Requisitions reset successfully'));
        });
    }

    function handle_reject(names) {
        frappe.prompt([{label: 'Reason for Rejection', fieldname: 'reason', fieldtype: 'Small Text', reqd: 1}], (v) => {
            perform_bulk_update(names, {
                'status': 'Rejected',
                'rejected_at': frappe.datetime.now_datetime(),
                'rejection_reason': v.reason
            }, __('Items Rejected'));
        }, __('Reject Requisitions'), __('Submit Rejection'));
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