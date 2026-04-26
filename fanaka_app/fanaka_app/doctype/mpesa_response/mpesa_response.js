// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Mpesa Response", {
    refresh: function (frm) {
        if (frm.doc.originator_conversation_id) {
            frm.add_custom_button(__("Find Requisition Payments"), function () {
                frappe.set_route("List", "Requisitions", {
                    name: frm.doc.erp_requisition,
                });
            });
        }
    },
});
