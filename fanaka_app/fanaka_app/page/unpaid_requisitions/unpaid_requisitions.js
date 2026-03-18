// [2026-03-18 12:58:45]
frappe.pages['unpaid-requisitions'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Unpaid Requisitions'),
        single_column: true
    });

    // 1. Setup Header Tabs
    let tabs = [
        { 
            label: __('Authorise'), 
            id: 'authorise',
            filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null] }
        },
        { 
            label: __('Release Funds'), 
            id: 'release',
            filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] }
        },
        { 
            label: __('Paid'), 
            id: 'paid',
            filter: { 'status': ['=', 'Paid'] }
        },
        { 
            label: __('Rejected'), 
            id: 'rejected',
            filter: { 'rejected_at': ['!=', null] }
        }
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

    // 2. Render Table View
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
                            method: 'fanaka_app.services.MpesaDisbursement.process_disbursement',
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

    // 3. OTP Verification Logic with 5-minute timer
    function request_otp_verification(on_success) {
        // First call to send OTP
        frappe.call({
            method: "fanaka_app.services.MpesaDisbursement.send_otp_notification", 
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
                            method: "fanaka_app.services.MpesaDisbursement.verify_authorisation_otp",
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

                // 5 Minute Timer Logic
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