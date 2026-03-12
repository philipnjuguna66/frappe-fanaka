frappe.ui.form.on("Lead", {

    refresh(frm) {

        if (frm.doc.phone) {

            frm.add_custom_button("Call Customer", () => {

                frappe.call({
                    method: "fanaka_app.api.call.make_call",
                    args: {
                        phone_number: frm.doc.phone
                    },
                    callback: function(r) {

                        if (r.message.status === "success") {
                            frappe.msgprint("Call initiated successfully");
                        } else {
                            frappe.msgprint("Call failed");
                        }

                    }
                });

            });

        }

    }

});