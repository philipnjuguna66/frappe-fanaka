// ================================================
// UNPAID REQUISITIONS – Beautiful Tailwind Dashboard
// ================================================

frappe.pages['unpaid-requisitions'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Unpaid Requisitions'),
        single_column: true
    });

    // ====================== INJECT TAILWIND + CUSTOM STYLES ======================
    if (!document.getElementById('tailwind-cdn')) {
        const tw = document.createElement('script');
        tw.id = 'tailwind-cdn';
        tw.src = 'https://cdn.tailwindcss.com';
        tw.onload = () => {
            if (window.tailwind) {
                window.tailwind.config = {
                    theme: {
                        extend: {
                            colors: {
                                brand: { DEFAULT: '#16a34a', light: '#dcfce7', dark: '#15803d' },
                                surface: '#f8fafc',
                                border: '#e2e8f0'
                            }
                        }
                    },
                    corePlugins: { preflight: false }
                };
            }
        };
        document.head.appendChild(tw);
    }

    const styles = `
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@500&display=swap');

        .req-page * { font-family: 'DM Sans', sans-serif; box-sizing: border-box; }
        .req-page { background: #f1f5f9; min-height: 100vh; padding: 20px; }

        /* Hide default Frappe page title bar styling conflicts */
        .req-page .page-head { display: none !important; }

        /* Balance Cards */
        .balance-card {
            background: #fff;
            border-radius: 16px;
            padding: 20px 24px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        .balance-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        }
        .balance-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
        }
        .balance-card.working::before { background: linear-gradient(90deg, #16a34a, #4ade80); }
        .balance-card.utility::before { background: linear-gradient(90deg, #2563eb, #60a5fa); }
        .balance-card.sync::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

        .balance-label {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .balance-label .dot {
            width: 7px; height: 7px;
            border-radius: 50%;
            display: inline-block;
        }
        .balance-amount {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
            font-family: 'DM Mono', monospace;
            letter-spacing: -0.5px;
        }
        .balance-amount.utility { color: #2563eb; }
        .balance-sub {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
        }

        /* Sync Button */
        .sync-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: #fff;
            border: 1.5px solid #16a34a;
            color: #16a34a;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .sync-btn:hover { background: #f0fdf4; box-shadow: 0 4px 12px rgba(22,163,74,0.15); }
        .sync-btn.loading i { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Tab Navigation */
        .req-tabs {
            display: flex;
            gap: 4px;
            background: #fff;
            padding: 4px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            width: fit-content;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            margin-bottom: 20px;
        }
        .req-tab {
            padding: 8px 20px;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 500;
            color: #64748b;
            cursor: pointer;
            border: none;
            background: transparent;
            transition: all 0.18s ease;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 7px;
        }
        .req-tab:hover { color: #0f172a; background: #f8fafc; }
        .req-tab.active {
            background: #16a34a;
            color: #fff;
            box-shadow: 0 2px 8px rgba(22,163,74,0.3);
            font-weight: 600;
        }
        .req-tab .tab-count {
            background: rgba(255,255,255,0.25);
            border-radius: 20px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: 700;
        }
        .req-tab:not(.active) .tab-count {
            background: #f1f5f9;
            color: #64748b;
        }

        /* List Card */
        .list-card {
            background: #fff;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            overflow: hidden;
        }
        .list-card-header {
            padding: 16px 20px;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .list-card-title {
            font-size: 15px;
            font-weight: 700;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Table */
        .req-table {
            width: 100%;
            border-collapse: collapse;
        }
        .req-table thead tr {
            border-bottom: 1px solid #f1f5f9;
        }
        .req-table thead th {
            padding: 10px 16px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: #94a3b8;
            text-align: left;
            background: #f8fafc;
        }
        .req-table thead th:first-child { border-radius: 0; padding-left: 20px; }
        .req-table thead th:last-child { text-align: right; padding-right: 20px; }
        .req-table tbody tr {
            border-bottom: 1px solid #f8fafc;
            transition: background 0.15s ease;
        }
        .req-table tbody tr:last-child { border-bottom: none; }
        .req-table tbody tr:hover { background: #f8fafc; }
        .req-table tbody td {
            padding: 14px 16px;
            vertical-align: middle;
            font-size: 13px;
            color: #334155;
        }
        .req-table tbody td:first-child { padding-left: 20px; }
        .req-table tbody td:last-child { text-align: right; padding-right: 20px; }

        .req-name { font-weight: 700; color: #0f172a; font-size: 13px; }
        .req-desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .req-amount { font-family: 'DM Mono', monospace; font-weight: 600; color: #0f172a; font-size: 14px; }

        /* Method Badge */
        .method-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            background: #dbeafe;
            color: #1d4ed8;
        }
        .method-badge.mpesa { background: #dcfce7; color: #15803d; }
        .method-badge.bank { background: #ede9fe; color: #6d28d9; }
        .method-badge.cash { background: #fef9c3; color: #854d0e; }

        /* Action Buttons */
        .action-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px; height: 30px;
            border-radius: 8px;
            border: 1.5px solid #e2e8f0;
            background: #fff;
            color: #64748b;
            cursor: pointer;
            transition: all 0.15s ease;
            font-size: 12px;
        }
        .action-btn:hover { border-color: #ef4444; color: #ef4444; background: #fef2f2; }

        /* Bulk Action Bar */
        .bulk-bar {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 20px;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
        }
        .bulk-btn-primary {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 18px;
            background: #16a34a;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(22,163,74,0.25);
        }
        .bulk-btn-primary:hover { background: #15803d; box-shadow: 0 4px 14px rgba(22,163,74,0.35); transform: translateY(-1px); }
        .bulk-btn-danger {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 18px;
            background: #fff;
            color: #ef4444;
            border: 1.5px solid #fca5a5;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .bulk-btn-danger:hover { background: #fef2f2; border-color: #ef4444; }

        /* Export Button */
        .export-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            background: #f8fafc;
            border: 1.5px solid #e2e8f0;
            color: #475569;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .export-btn:hover { background: #f1f5f9; border-color: #cbd5e1; }

        /* Checkbox Styles */
        .req-check {
            width: 16px; height: 16px;
            accent-color: #16a34a;
            cursor: pointer;
            border-radius: 4px;
        }

        /* Empty State */
        .empty-state {
            padding: 64px 20px;
            text-align: center;
        }
        .empty-icon {
            width: 56px; height: 56px;
            background: #f1f5f9;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            font-size: 22px;
            color: #94a3b8;
        }
        .empty-title { font-size: 15px; font-weight: 700; color: #475569; margin-bottom: 6px; }
        .empty-sub { font-size: 13px; color: #94a3b8; }

        /* OTP Dialog Overrides */
        .modal-dialog { border-radius: 16px !important; overflow: hidden; }
        .modal-header { background: #f8fafc !important; border-bottom: 1px solid #e2e8f0 !important; }
        .modal-title { font-family: 'DM Sans', sans-serif !important; font-weight: 700 !important; }

        /* Fade-in animation */
        @keyframes fadeSlideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .req-animate { animation: fadeSlideIn 0.3s ease forwards; }

        /* Paybill Info */
        .paybill-strip {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 16px;
            background: #fff;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            font-size: 12px;
            color: #64748b;
            width: fit-content;
        }
        .paybill-strip strong { color: #0f172a; font-weight: 700; }
        .paybill-divider { width: 1px; height: 16px; background: #e2e8f0; }
    </style>`;
    $('head').append(styles);

    // ====================== REALTIME NOTIFICATIONS ======================
    function setup_realtime_listeners() {
        frappe.realtime.on('payment_success', (data) => {
            frappe.show_alert({
                message: __(`✅ ${data.requisitionId}: Payment Successful — ${data.transaction_id}`),
                indicator: 'green'
            });
            wrapper.refresh();
        });
        frappe.realtime.on('mpesa_balance_updated', (data) => {
            renderDatabaseBalances();
            frappe.show_alert({ message: __('M-Pesa balance synced from Safaricom'), indicator: 'blue' });
        });
        frappe.realtime.on('payment_error', (data) => {
            frappe.msgprint({
                title: __('M-Pesa Payment Failed'),
                message: __(`${data.requisitionId}: ${data.message}`),
                indicator: 'red'
            });
            wrapper.refresh();
        });
    }
    setup_realtime_listeners();

    // ====================== PAGE WRAPPER ======================
    const $main = page.main;
    $main.addClass('req-page');

    // ====================== HEADER ======================
    const headerHtml = `
    <div class="req-animate" style="margin-bottom: 24px;">
        <div style="display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
            <div>
                <h1 style="font-size: 22px; font-weight: 800; color: #0f172a; margin: 0 0 4px;">Unpaid Requisitions</h1>
                <div class="paybill-strip">
                    <span>Paybill <strong>4157389</strong></span>
                    <div class="paybill-divider"></div>
                    <span>Account <strong>Fanaka</strong></span>
                </div>
            </div>
            <button class="sync-btn" id="refresh-mpesa-btn">
                <i class="fa fa-refresh"></i>
                Sync Balance
            </button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
            <div class="balance-card working">
                <div class="balance-label">
                    <span class="dot" style="background: #16a34a;"></span>
                    Working Account
                </div>
                <div class="balance-amount" id="working-balance">KES —</div>
                <div class="balance-sub">M-Pesa Working</div>
            </div>
            <div class="balance-card utility">
                <div class="balance-label">
                    <span class="dot" style="background: #2563eb;"></span>
                    Utility Account
                </div>
                <div class="balance-amount utility" id="utility-balance">KES —</div>
                <div class="balance-sub">M-Pesa Utility</div>
            </div>
            <div class="balance-card sync" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="balance-label">
                    <span class="dot" style="background: #f59e0b;"></span>
                    Last Synced
                </div>
                <div id="last-updated-text" style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 4px;">Fetching...</div>
            </div>
        </div>
    </div>`;

    $main.append(headerHtml);
    renderDatabaseBalances();

    $('#refresh-mpesa-btn').on('click', function() {
        const $btn = $(this).addClass('loading');
        frappe.call({
            method: 'fanaka_app.api.MpesaDisbursement.get_mpesa_balance',
            callback: () => {
                frappe.show_alert({ message: __('Syncing with Safaricom…'), indicator: 'orange' });
                setTimeout(() => {
                    renderDatabaseBalances();
                    $btn.removeClass('loading');
                }, 4000);
            }
        });
    });

    function renderDatabaseBalances() {
        frappe.call({
            method: 'fanaka_app.api.MpesaDisbursement.get_stored_mpesa_balance',
            callback: function(r) {
                if (r.message) {
                    $('#working-balance').text(r.message.working_balance);
                    $('#utility-balance').text(r.message.utility_balance);
                    $('#last-updated-text').text(r.message.last_updated);
                }
            }
        });
    }

    // ====================== TABS ======================
    const tabs = [
        { label: 'Authorise Requisition', id: 'authorise', icon: '🔐', filter: { 'initiated_at': ['!=', null], 'authorised_at': ['=', null] } },
        { label: 'Release Requisition', id: 'release', icon: '💸', filter: { 'authorised_at': ['!=', null], 'status': ['!=', 'Paid'] } },
        { label: 'Paid Requisition', id: 'paid', icon: '✅', filter: { 'status': ['=', 'Paid'] } },
        { label: 'Rejected Requisition', id: 'rejected', icon: '❌', filter: { 'rejected_at': ['!=', null] } }
    ];

    const $tabsRow = $('<div class="req-tabs req-animate"></div>').appendTo($main);

    tabs.forEach(tab => {
        $(`<button class="req-tab" data-id="${tab.id}">
            <span>${tab.icon}</span>
            <span>${__(tab.label)}</span>
        </button>`)
            .appendTo($tabsRow)
            .on('click', function() {
                $tabsRow.find('.req-tab').removeClass('active');
                $(this).addClass('active');
                render_list(tab.filter, tab.id, tab.label);
            });
    });

    // ====================== RENDER LIST ======================
    function render_list(filters, context_id, tab_label) {
        $main.find('.list-card').remove();

        const $card = $('<div class="list-card req-animate"></div>').appendTo($main);

        $card.html(`
            <div class="list-card-header">
                <div class="list-card-title">
                    <span>${tab_label || context_id}</span>
                </div>
                <button class="export-btn">
                    <i class="fa fa-download"></i> Export
                </button>
            </div>
            <div class="table-responsive">
                <table class="req-table">
                    <thead>
                        <tr>
                            <th style="width: 40px;"><input type="checkbox" class="req-check master-checker"></th>
                            <th>${__('Requisition')}</th>
                            <th>${__('Amount')}</th>
                            <th>${__('Method')}</th>
                            <th>${__('Pay To')}</th>
                            <th>${__('Actions')}</th>
                        </tr>
                    </thead>
                    <tbody id="req-tbody">
                        <tr>
                            <td colspan="6">
                                <div class="empty-state">
                                    <div class="empty-icon"><i class="fa fa-spinner fa-spin"></i></div>
                                    <div class="empty-title">Loading…</div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="bulk-bar" id="bulk-bar" style="display: none;"></div>
        `);

        // Master checkbox
        $card.find('.master-checker').on('change', function() {
            $card.find('.row-checker').prop('checked', $(this).prop('checked'));
        });

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
                const $tbody = $card.find('#req-tbody').empty();

                // Update tab count
                const count = r.message ? r.message.length : 0;
                $tabsRow.find(`.req-tab.active .tab-count`).remove();
                if (count > 0) {
                    $tabsRow.find('.req-tab.active').append(`<span class="tab-count">${count}</span>`);
                }

                if (r.message && r.message.length > 0) {
                    r.message.forEach(data => {
                        const methodClass = (data.payment_method || '').toLowerCase().includes('mpesa') ? 'mpesa'
                            : (data.payment_method || '').toLowerCase().includes('bank') ? 'bank' : 'cash';

                        const $row = $(`<tr>
                            <td><input type="checkbox" class="req-check row-checker" data-name="${data.name}"></td>
                            <td>
                                <div class="req-name">${data.name}</div>
                                <div class="req-desc">${data.description || '—'}</div>
                            </td>
                            <td><span class="req-amount">${frappe.format(data.total_amount, { fieldtype: 'Currency' })}</span></td>
                            <td><span class="method-badge ${methodClass}">${data.payment_method || 'N/A'}</span></td>
                            <td style="color: #64748b; font-size: 13px;">${data.pay_to || '—'}</td>
                            <td class="action-area"></td>
                        </tr>`).appendTo($tbody);

                        if (context_id === 'authorise' || context_id === 'release') {
                            $(`<button class="action-btn" title="${__('Undo Action')}"><i class="fa fa-undo"></i></button>`)
                                .appendTo($row.find('.action-area'))
                                .on('click', () => handle_undo([data.name]));
                        }
                    });

                    setup_bulk_actions($card, context_id);
                } else {
                    $tbody.html(`<tr><td colspan="6">
                        <div class="empty-state">
                            <div class="empty-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                            </div>
                            <div class="empty-title">No ${tab_label || 'Records'}</div>
                            <div class="empty-sub">No requisitions pending in this category</div>
                        </div>
                    </td></tr>`);
                }
            }
        });
    }

    // ====================== BULK ACTIONS ======================
    function setup_bulk_actions($card, context_id) {
        const $bar = $card.find('#bulk-bar').show();

        if (context_id === 'authorise') {
            $bar.html(`
                <button class="bulk-btn-primary" id="bulk-auth-btn">
                    <i class="fa fa-check"></i> Bulk Authorise
                </button>
                <button class="bulk-btn-danger" id="bulk-undo-btn">
                    <i class="fa fa-undo"></i> Bulk Undo
                </button>
                <span style="font-size: 12px; color: #94a3b8; margin-left: 4px;" id="selected-count"></span>
            `);

            $card.find('.row-checker').on('change', update_count);
            $card.find('.master-checker').on('change', update_count);

            $bar.find('#bulk-auth-btn').on('click', () => {
                let selected = get_selected_names($card);
                if (!selected.length) return frappe.msgprint(__('Select at least one item'));
                request_otp_verification(() => {
                    perform_bulk_update(selected, {
                        'authorised_at': frappe.datetime.now_datetime(),
                        'authorised_by': frappe.session.user
                    }, __('Requisitions Authorised'));
                });
            });

            $bar.find('#bulk-undo-btn').on('click', () => {
                let selected = get_selected_names($card);
                if (!selected.length) return frappe.msgprint(__('Select at least one item'));
                handle_undo(selected);
            });

        } else if (context_id === 'release') {
            $bar.html(`
                <button class="bulk-btn-primary" id="bulk-release-btn">
                    <i class="fa fa-paper-plane"></i> Bulk Release
                </button>
                <button class="bulk-btn-danger" id="bulk-undo-btn">
                    <i class="fa fa-undo"></i> Bulk Undo
                </button>
                <span style="font-size: 12px; color: #94a3b8; margin-left: 4px;" id="selected-count"></span>
            `);

            $card.find('.row-checker').on('change', update_count);
            $card.find('.master-checker').on('change', update_count);

            $bar.find('#bulk-release-btn').on('click', () => {
                let selected = get_selected_names($card);
                if (!selected.length) return frappe.msgprint(__('Select at least one item'));
                frappe.confirm(__('Release payments for {0} items?', [selected.length]), () => {
                    selected.forEach(name => {
                        frappe.call({
                            method: 'fanaka_app.api.MpesaDisbursement.process_disbursement',
                            args: { requisition_id: name }
                        });
                    });
                    frappe.show_alert({ message: __('Disbursement started'), indicator: 'green' });
                    setTimeout(() => wrapper.refresh(), 2000);
                });
            });

            $bar.find('#bulk-undo-btn').on('click', () => {
                let selected = get_selected_names($card);
                if (!selected.length) return frappe.msgprint(__('Select at least one item'));
                handle_undo(selected);
            });
        } else {
            $bar.hide();
        }

        function update_count() {
            const n = get_selected_names($card).length;
            $('#selected-count').text(n > 0 ? `${n} selected` : '');
        }
    }

    // ====================== OTP VERIFICATION ======================
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
                            content: `<div style="background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 10px 14px; margin-top: 8px; display: flex; align-items: center; gap: 8px;">
                                <i class="fa fa-clock-o" style="color: #ef4444;"></i>
                                <span id="otp-timer" style="font-family: 'DM Mono', monospace; font-weight: 600; color: #ef4444; font-size: 14px;">Expires in: 05:00</span>
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
                    let m = String(Math.floor(duration / 60)).padStart(2, '0');
                    let s = String(duration % 60).padStart(2, '0');
                    timer_display.text(`Expires in: ${m}:${s}`);
                    if (--duration < 0) {
                        clearInterval(timer_interval);
                        timer_display.text('OTP Expired. Please close and try again.');
                        d.get_primary_btn().prop('disabled', true);
                    }
                }, 1000);

                d.on_hide = () => clearInterval(timer_interval);
            }
        });
    }

    // ====================== HELPERS ======================
    function get_selected_names($card) {
        return ($card || page.main).find('.row-checker:checked').map(function() {
            return $(this).data('name');
        }).get();
    }

    function perform_bulk_update(names, values, success_msg) {
        let promises = names.map(name => new Promise((resolve) => {
            frappe.call({
                method: 'frappe.client.set_value',
                args: { doctype: 'Requisitions', name, fieldname: values },
                callback: resolve,
                error: resolve
            });
        }));
        Promise.all(promises).then(() => {
            frappe.show_alert({ message: success_msg, indicator: 'blue' });
            wrapper.refresh();
        });
    }

    function handle_undo(names) {
        const msg = names.length > 1
            ? __('Undo action for {0} selected items?', [names.length])
            : __('Undo action for {0}? Record returns to draft/pending.', [names[0]]);
        frappe.confirm(msg, () => {
            perform_bulk_update(names, {
                'initiated_at': null,
                'initiated_by': null,
                'authorised_at': null,
                'authorised_by': null
            }, __('Action undone successfully'));
        });
    }

    // ====================== INIT ======================
    wrapper.refresh = function() {
        const $active = $tabsRow.find('.req-tab.active');
        if ($active.length) {
            $active.trigger('click');
        } else {
            $tabsRow.find('.req-tab:first').trigger('click');
        }
    };

    wrapper.refresh();
};